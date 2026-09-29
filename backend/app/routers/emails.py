import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Email, Reply, BulkJob, EmailStatus, EmailAccount
from app.schemas import (
    EmailOut, GenerateRepliesResponse, EmailAnalysis, ReplyOut,
    BulkProcessRequest, BulkJobOut, SendReplyRequest,
)
from app.security import get_current_user_id
from app.services import ai_service
from app.services.bulk_processor import run_job, retry_failed
from app.services.email_service import get_provider

router = APIRouter(prefix="/emails", tags=["emails"])
replies_router = APIRouter(prefix="/replies", tags=["replies"])


@router.get("", response_model=list[EmailOut])
async def list_emails(
    status_filter: str | None = None,
    intent: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    db: AsyncSession = Depends(get_db),
):
    query = select(Email)
    if status_filter:
        query = query.where(Email.status == status_filter)
    if intent:
        query = query.where(Email.intent == intent)
    if priority:
        query = query.where(Email.priority == priority)
    if search:
        like = f"%{search}%"
        query = query.where((Email.subject.ilike(like)) | (Email.sender.ilike(like)))

    query = query.order_by(Email.received_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.scalars(query)
    emails = result.all()

    out = []
    for e in emails:
        count = await db.scalar(select(func.count()).select_from(Reply).where(Reply.email_id == e.id))
        item = EmailOut.model_validate(e)
        item.reply_count = count or 0
        out.append(item)
    return out


@router.get("/{email_id}", response_model=EmailOut)
async def get_email(email_id: str, db: AsyncSession = Depends(get_db)):
    email = await db.get(Email, email_id)
    if not email:
        raise HTTPException(404, "Email not found")
    count = await db.scalar(select(func.count()).select_from(Reply).where(Reply.email_id == email_id))
    out = EmailOut.model_validate(email)
    out.reply_count = count or 0
    return out


@router.post("/{email_id}/analyze", response_model=EmailAnalysis)
async def analyze_email_endpoint(email_id: str, db: AsyncSession = Depends(get_db)):
    email = await db.get(Email, email_id)
    if not email:
        raise HTTPException(404, "Email not found")

    email.status = EmailStatus.analyzing
    await db.commit()

    try:
        analysis = await ai_service.analyze_email(email.subject, email.body, email.thread_context)
    except Exception as exc:
        email.status = EmailStatus.failed
        email.error_message = str(exc)
        await db.commit()
        raise HTTPException(502, f"AI analysis failed: {exc}") from exc

    email.intent = analysis.intent
    email.priority = analysis.priority
    email.tone = analysis.tone
    email.summary = analysis.summary
    email.analysis_json = analysis.model_dump()
    email.status = EmailStatus.analyzed
    await db.commit()
    return analysis


@router.post("/{email_id}/generate-replies", response_model=GenerateRepliesResponse)
async def generate_replies_endpoint(email_id: str, db: AsyncSession = Depends(get_db)):
    email = await db.get(Email, email_id)
    if not email:
        raise HTTPException(404, "Email not found")

    if not email.analysis_json:
        analysis = await ai_service.analyze_email(email.subject, email.body, email.thread_context)
        email.intent, email.priority, email.tone = analysis.intent, analysis.priority, analysis.tone
        email.summary, email.analysis_json = analysis.summary, analysis.model_dump()
    else:
        analysis = EmailAnalysis(**email.analysis_json)

    email.status = EmailStatus.generating_replies
    await db.commit()

    try:
        drafts = await ai_service.generate_replies(email.subject, email.body, analysis, email.thread_context)
    except Exception as exc:
        email.status = EmailStatus.failed
        email.error_message = str(exc)
        await db.commit()
        raise HTTPException(502, f"Reply generation failed: {exc}") from exc

    # Replace any previous drafts for this email
    old = await db.scalars(select(Reply).where(Reply.email_id == email_id))
    for r in old.all():
        await db.delete(r)

    reply_rows = [Reply(email_id=email_id, style=d["style"], body=d["body"]) for d in drafts]
    db.add_all(reply_rows)
    email.status = EmailStatus.completed
    await db.commit()
    for r in reply_rows:
        await db.refresh(r)

    return GenerateRepliesResponse(
        email_id=email_id,
        analysis=analysis,
        replies=[ReplyOut.model_validate(r) for r in reply_rows],
    )


@router.post("/{email_id}/send")
async def send_reply(email_id: str, payload: SendReplyRequest, db: AsyncSession = Depends(get_db)):
    reply = await db.get(Reply, payload.reply_id)
    if not reply or reply.email_id != email_id:
        raise HTTPException(404, "Reply not found")

    email = await db.get(Email, email_id)
    account = await db.get(EmailAccount, payload.account_id) if payload.account_id else (
        await db.get(EmailAccount, email.account_id) if email else None
    )

    # Only actually calls the provider's API if this account has real OAuth
    # tokens (i.e. was connected via Gmail OAuth, not seeded demo data).
    if account and account.oauth_access_token_encrypted:
        provider = get_provider(account.provider)
        sender_email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", email.sender)
        try:
            await provider.send_reply(
                account,
                to=sender_email.group(0) if sender_email else email.sender,
                subject=email.subject,
                body=reply.body,
                thread_id=email.thread_id,
                db=db,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"Sending via {account.provider} failed: {exc}") from exc

    reply.was_sent = True
    reply.is_selected = True
    await db.commit()
    return {"status": "sent", "reply_id": reply.id}


@router.post("/bulk-process", response_model=BulkJobOut, status_code=202)
async def bulk_process(
    payload: BulkProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Kicks off an async bulk job and returns immediately with a job id.
    The frontend polls GET /emails/bulk-status/{job_id} for live progress —
    this endpoint never blocks on the actual AI calls.
    """
    if payload.email_ids:
        ids = payload.email_ids[: payload.limit]
    else:
        result = await db.scalars(
            select(Email.id).where(Email.status == EmailStatus.pending).limit(payload.limit)
        )
        ids = result.all()

    if not ids:
        raise HTTPException(400, "No matching emails to process")

    job = BulkJob(total=len(ids), status="running")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(run_job, job.id, list(ids))
    return job


@router.get("/bulk-status/{job_id}", response_model=BulkJobOut)
async def bulk_status(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(BulkJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/bulk-retry/{job_id}", response_model=BulkJobOut, status_code=202)
async def bulk_retry(job_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    job = await db.get(BulkJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    background_tasks.add_task(retry_failed, job_id)
    return job


# ---------- Reply-level actions ----------

@replies_router.post("/{reply_id}/regenerate", response_model=ReplyOut)
async def regenerate_reply(reply_id: str, db: AsyncSession = Depends(get_db)):
    reply = await db.get(Reply, reply_id)
    if not reply:
        raise HTTPException(404, "Reply not found")
    email = await db.get(Email, reply.email_id)
    analysis = EmailAnalysis(**email.analysis_json)

    drafts = await ai_service.generate_replies(email.subject, email.body, analysis, email.thread_context)
    match = next((d for d in drafts if d["style"] == reply.style), drafts[0])

    reply.body = match["body"]
    reply.was_edited = False
    await db.commit()
    await db.refresh(reply)
    return reply


@replies_router.post("/{reply_id}/modify", response_model=ReplyOut)
async def modify_reply_endpoint(reply_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """payload: {"instruction": "Make it shorter"} — see schemas.ModifyReplyRequest"""
    reply = await db.get(Reply, reply_id)
    if not reply:
        raise HTTPException(404, "Reply not found")
    email = await db.get(Email, reply.email_id)
    analysis = EmailAnalysis(**email.analysis_json)

    new_body = await ai_service.modify_reply(reply.body, payload["instruction"], analysis)
    reply.body = new_body
    reply.was_edited = True
    await db.commit()
    await db.refresh(reply)
    return reply
