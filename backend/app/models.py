"""
ORM models. Kept intentionally normalized: an Email has many Replies (up to
10 per analysis pass) and one latest Analysis snapshot. BulkJob tracks a
batch-processing run so progress can be polled or streamed.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_id() -> str:
    return uuid.uuid4().hex


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class EmailStatus(str, enum.Enum):
    pending = "pending"
    analyzing = "analyzing"
    analyzed = "analyzed"
    generating_replies = "generating_replies"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    accounts: Mapped[list["EmailAccount"]] = relationship(back_populates="user")


class EmailAccount(Base):
    """
    A connected mailbox. OAuth tokens are stored encrypted at rest (see
    services/crypto.py in a real deployment) — never a raw password.
    """
    __tablename__ = "email_accounts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String)  # "gmail" | "outlook" | "imap"
    email_address: Mapped[str] = mapped_column(String)
    oauth_access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="accounts")


class Email(Base):
    __tablename__ = "emails"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("email_accounts.id"))
    external_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # provider's message id — dedup key on sync
    thread_id: Mapped[str | None] = mapped_column(String, nullable=True)  # provider's thread id — used when sending a threaded reply
    sender: Mapped[str] = mapped_column(String)
    recipient: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    thread_context: Mapped[str | None] = mapped_column(Text, nullable=True)  # prior messages, if any
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    status: Mapped[EmailStatus] = mapped_column(Enum(EmailStatus), default=EmailStatus.pending)
    priority: Mapped[Priority | None] = mapped_column(Enum(Priority), nullable=True)
    intent: Mapped[str | None] = mapped_column(String, nullable=True)
    tone: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # full structured analysis
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    replies: Mapped[list["Reply"]] = relationship(back_populates="email", cascade="all, delete-orphan")


class Reply(Base):
    __tablename__ = "replies"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    email_id: Mapped[str] = mapped_column(ForeignKey("emails.id"))
    style: Mapped[str] = mapped_column(String)   # e.g. "Professional", "Casual"
    body: Mapped[str] = mapped_column(Text)
    is_selected: Mapped[bool] = mapped_column(default=False)
    was_edited: Mapped[bool] = mapped_column(default=False)
    was_sent: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    email: Mapped["Email"] = relationship(back_populates="replies")


class BulkJob(Base):
    """
    Tracks one bulk-processing run. Progress fields are updated in place by
    the background worker so the frontend can poll GET /emails/bulk-status/{id}.
    """
    __tablename__ = "bulk_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    total: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="running")  # running|completed|failed
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_email_ids: Mapped[list] = mapped_column(JSON, default=list)
