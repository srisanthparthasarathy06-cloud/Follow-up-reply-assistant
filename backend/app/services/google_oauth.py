"""
Google OAuth 2.0 authorization-code flow for Gmail access.

Requires GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REDIRECT_URI in
.env, created via Google Cloud Console (OAuth consent screen + credentials).
See backend/README.md for the exact steps.
"""
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=settings.google_redirect_uri)


def get_authorization_url(state: str) -> str:
    """`state` carries the caller's JWT so the callback knows which user to attach the account to."""
    flow = _flow()
    url, _ = flow.authorization_url(
        access_type="offline",       # required to get a refresh_token
        include_granted_scopes="true",
        prompt="consent",            # forces refresh_token on every connect, not just the first
        state=state,
    )
    return url


def exchange_code(code: str) -> dict:
    """Exchanges an authorization code for tokens + the connected account's email address."""
    flow = _flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    oauth2_service = build("oauth2", "v2", credentials=creds)
    info = oauth2_service.userinfo().get().execute()

    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry,
        "email_address": info.get("email"),
    }
