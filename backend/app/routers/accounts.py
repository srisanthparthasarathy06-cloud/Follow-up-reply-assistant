from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import EmailAccount, Email
from app.schemas import ConnectAccountRequest, EmailAccountOut, SyncResponse
from app.security import get_current_user_id, create_access_token
from app.services.email_service import get_provider

router = APIRouter(prefix="/email", tags=["accounts"])


@router.get("/google/connect-url")
async def google_connect_url(user_id: str = Depends(get_current_user_id)):
    """
    Returns the URL the frontend should navigate the browser to in order to
    start the Gmail OAuth consent flow. We mint a fresh short-lived token
    here (rather than reusing the caller's bearer token) purely so it's
    obviously scoped to this one redirect round-trip.
    """
    state_token = create_access_token(user_id)
    return {"url": f"/auth/google/login?token={state_token}"}


@router.post("/connect", response_model=EmailAccountOut, status_code=201)
async def connect_account(
    payload: ConnectAccountRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    For IMAP-style providers only (no OAuth redirect needed). Gmail/Outlook
    go through GET /auth/google/login instead — see google_connect_url above.
    """
    if payload.provider in ("gmail", "outlook"):
        raise HTTPException(
            400, "Gmail/Outlook connect via OAuth — call GET /email/google/connect-url and redirect the browser there."
        )

    account = EmailAccount(user_id=user_id, provider=payload.provider, email_address="pending-imap-setup")
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/accounts", response_model=list[EmailAccountOut])
async def list_accounts(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.scalars(select(EmailAccount).where(EmailAccount.user_id == user_id))
    return result.all()


@router.delete("/accounts/{account_id}", status_code=204)
async def disconnect_account(account_id: str, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user_id:
        raise HTTPException(404, "Account not found")
    await db.delete(account)
    await db.commit()


@router.post("/accounts/{account_id}/sync", response_model=SyncResponse)
async def sync_account(
    account_id: str,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Pulls the most recent `limit` inbox messages from the real mailbox and
    inserts any we haven't seen before (deduped on the provider's message id).
    Does NOT analyze them or generate replies — that happens per-email via
    POST /emails/{id}/generate-replies, or in bulk via POST /emails/bulk-process.
    """
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user_id:
        raise HTTPException(404, "Account not found")

    provider = get_provider(account.provider)
    try:
        raw_messages = await provider.fetch_inbox(account, limit=limit, db=db)
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Failed to sync inbox: {exc}") from exc

    existing_ids = set(
        await db.scalars(
            select(Email.external_id).where(Email.account_id == account_id, Email.external_id.isnot(None))
        )
    )

    added = 0
    for m in raw_messages:
        if m["external_id"] in existing_ids:
            continue
        db.add(
            Email(
                account_id=account_id,
                external_id=m["external_id"],
                thread_id=m.get("thread_id"),
                sender=m["sender"],
                recipient=m.get("recipient", ""),
                subject=m["subject"],
                body=m["body"],
                received_at=m["received_at"],
            )
        )
        added += 1

    from datetime import datetime
    account.last_synced_at = datetime.utcnow()
    await db.commit()

    return SyncResponse(fetched=len(raw_messages), added=added, skipped_duplicates=len(raw_messages) - added)
