"""
Google OAuth 2.0 endpoints. Flow:

  1. Frontend sends the user's browser to GET /auth/google/login?token=<jwt>
     (the JWT is the user's own Relay session token, carried as `state`)
  2. Google shows its consent screen, then redirects to GET /auth/google/callback
  3. We exchange the code for tokens, look up the user from `state`, and
     upsert their EmailAccount row with encrypted tokens
  4. Redirect back to the frontend's accounts page
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import EmailAccount
from app.security import decode_token
from app.services import crypto, google_oauth

router = APIRouter(prefix="/auth/google", tags=["google-oauth"])


@router.get("/login")
async def google_login(token: str = Query(..., description="The signed-in user's Relay JWT")):
    # Validate up front so a bad/expired token fails fast with a clear error,
    # rather than after the user has already gone through Google's consent screen.
    decode_token(token)
    url = google_oauth.get_authorization_url(state=token)
    return RedirectResponse(url)


@router.get("/callback")
async def google_callback(code: str = Query(...), state: str = Query(...)):
    try:
        user_id = decode_token(state)
    except HTTPException:
        raise HTTPException(400, "Session expired before Google redirected back — please try connecting again.")

    try:
        result = google_oauth.exchange_code(code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Google token exchange failed: {exc}") from exc

    async with SessionLocal() as db:
        existing = await db.scalar(
            select(EmailAccount).where(
                EmailAccount.user_id == user_id,
                EmailAccount.provider == "gmail",
                EmailAccount.email_address == result["email_address"],
            )
        )
        account = existing or EmailAccount(user_id=user_id, provider="gmail", email_address=result["email_address"])

        account.oauth_access_token_encrypted = crypto.encrypt(result["access_token"])
        if result["refresh_token"]:
            account.oauth_refresh_token_encrypted = crypto.encrypt(result["refresh_token"])
        account.token_expiry = result["expiry"]

        if not existing:
            db.add(account)
        await db.commit()

    return RedirectResponse(f"{settings.frontend_url}/accounts?connected=1")
