"""
Email provider integration layer.

GmailProvider is fully implemented (list/read/send via the Gmail API).
OutlookProvider and ImapSmtpProvider are still stubs — same interface,
fill in when you need them.

Security: only OAuth access/refresh tokens are ever persisted, and always
encrypted at rest (see services/crypto.py). No email password is stored.
"""
import asyncio
import base64
import re
from datetime import datetime
from email.mime.text import MIMEText
from abc import ABC, abstractmethod

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import EmailAccount
from app.services import crypto
from app.services.google_oauth import SCOPES


class EmailProvider(ABC):
    @abstractmethod
    async def fetch_inbox(self, account: EmailAccount, limit: int, db: AsyncSession | None = None) -> list[dict]:
        """Return raw email dicts: external_id, thread_id, sender, recipient, subject, body, received_at."""

    @abstractmethod
    async def send_reply(
        self, account: EmailAccount, to: str, subject: str, body: str, thread_id: str | None, db: AsyncSession | None = None
    ) -> None: ...


def _build_credentials(account: EmailAccount) -> Credentials:
    if not account.oauth_access_token_encrypted:
        raise RuntimeError("This account has no stored access token — reconnect it via /email/google/connect-url.")
    access_token = crypto.decrypt(account.oauth_access_token_encrypted)
    refresh_token = (
        crypto.decrypt(account.oauth_refresh_token_encrypted) if account.oauth_refresh_token_encrypted else None
    )
    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )


async def _refresh_if_needed(creds: Credentials, account: EmailAccount, db: AsyncSession | None) -> None:
    if creds.valid or not creds.refresh_token:
        return
    await asyncio.to_thread(creds.refresh, GoogleRequest())
    account.oauth_access_token_encrypted = crypto.encrypt(creds.token)
    account.token_expiry = creds.expiry
    if db is not None:
        await db.commit()


def _extract_body(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        found = _extract_body(part)
        if found:
            return found
    return ""


def _parse_message(msg: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    received_at = datetime.utcnow()
    try:
        # Gmail internalDate is ms since epoch — more reliable than parsing the Date header
        received_at = datetime.utcfromtimestamp(int(msg["internalDate"]) / 1000)
    except (KeyError, ValueError):
        pass

    return {
        "external_id": msg["id"],
        "thread_id": msg.get("threadId"),
        "sender": headers.get("from", "Unknown sender"),
        "recipient": headers.get("to", ""),
        "subject": headers.get("subject", "(no subject)"),
        "body": _extract_body(msg.get("payload", {})) or msg.get("snippet", ""),
        "received_at": received_at,
    }


class GmailProvider(EmailProvider):
    async def fetch_inbox(self, account: EmailAccount, limit: int = 100, db: AsyncSession | None = None) -> list[dict]:
        creds = _build_credentials(account)
        await _refresh_if_needed(creds, account, db)
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)

        def _list_and_fetch():
            results = (
                service.users()
                .messages()
                .list(userId="me", labelIds=["INBOX"], maxResults=min(limit, 500))
                .execute()
            )
            message_refs = results.get("messages", [])
            parsed = []
            for ref in message_refs:
                msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
                parsed.append(_parse_message(msg))
            return parsed

        # Gmail's client library is synchronous — run it off the event loop
        # so it doesn't block other requests (including other emails' AI calls).
        return await asyncio.to_thread(_list_and_fetch)

    async def send_reply(
        self, account: EmailAccount, to: str, subject: str, body: str, thread_id: str | None = None, db: AsyncSession | None = None
    ) -> None:
        creds = _build_credentials(account)
        await _refresh_if_needed(creds, account, db)
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject if re.match(r"(?i)^re:", subject) else f"Re: {subject}"
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        payload = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id

        await asyncio.to_thread(service.users().messages().send(userId="me", body=payload).execute)


class OutlookProvider(EmailProvider):
    """Wraps Microsoft Graph (/me/messages). Not yet implemented."""

    async def fetch_inbox(self, account, limit=100, db=None) -> list[dict]:
        raise NotImplementedError("Wire up Microsoft Graph credentials to enable live sync.")

    async def send_reply(self, account, to, subject, body, thread_id=None, db=None) -> None:
        raise NotImplementedError("Wire up Microsoft Graph credentials to enable sending.")


class ImapSmtpProvider(EmailProvider):
    """Generic fallback for any IMAP/SMTP-compatible provider. Not yet implemented."""

    async def fetch_inbox(self, account, limit=100, db=None) -> list[dict]:
        raise NotImplementedError("Configure IMAP host/credentials to enable live sync.")

    async def send_reply(self, account, to, subject, body, thread_id=None, db=None) -> None:
        raise NotImplementedError("Configure SMTP host/credentials to enable sending.")


def get_provider(provider_name: str) -> EmailProvider:
    return {"gmail": GmailProvider(), "outlook": OutlookProvider(), "imap": ImapSmtpProvider()}[provider_name]
