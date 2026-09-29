"""
Pydantic v2 schemas for request validation and response shaping. Keeping
these separate from the ORM models lets the API surface evolve independently
of storage.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Email accounts ----------
class ConnectAccountRequest(BaseModel):
    provider: str = Field(pattern="^(gmail|outlook|imap)$")
    oauth_code: str | None = None  # authorization code from OAuth redirect
    imap_host: str | None = None   # only for provider == "imap"


class EmailAccountOut(BaseModel):
    id: str
    provider: str
    email_address: str
    connected_at: datetime

    class Config:
        from_attributes = True


class SyncResponse(BaseModel):
    fetched: int
    added: int
    skipped_duplicates: int


# ---------- Emails ----------
class EmailOut(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    status: str
    priority: str | None = None
    intent: str | None = None
    tone: str | None = None
    summary: str | None = None
    received_at: datetime
    reply_count: int = 0

    class Config:
        from_attributes = True


class EmailAnalysis(BaseModel):
    """Structured output the AI must return for the 'understand' step."""
    intent: str
    priority: str  # low | medium | high
    tone: str
    urgency: str
    sentiment: str
    required_action: str
    questions_asked: list[str] = []
    key_entities: list[str] = []
    relevant_dates: list[str] = []
    known_information: list[str] = Field(
        default_factory=list,
        description="Facts explicitly present in the email/thread — safe to reference.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Things the sender asked about that we do NOT have confirmed data for — replies must not fabricate these.",
    )
    summary: str


class ReplyOut(BaseModel):
    id: str
    style: str
    body: str
    is_selected: bool
    was_edited: bool
    was_sent: bool

    class Config:
        from_attributes = True


class GenerateRepliesResponse(BaseModel):
    email_id: str
    analysis: EmailAnalysis
    replies: list[ReplyOut]


class ModifyReplyRequest(BaseModel):
    instruction: str = Field(
        ..., examples=["Make it shorter", "Make it more professional", "Make it friendlier"]
    )


class SendReplyRequest(BaseModel):
    reply_id: str
    account_id: str | None = Field(
        default=None, description="Send from this connected account instead of the email's original inbox account."
    )


# ---------- Bulk processing ----------
class BulkProcessRequest(BaseModel):
    email_ids: list[str] | None = None  # None => process all pending, up to 1000
    limit: int = Field(default=1000, le=1000)


class BulkJobOut(BaseModel):
    id: str
    total: int
    processed: int
    succeeded: int
    failed: int
    status: str
    failed_email_ids: list[str]

    class Config:
        from_attributes = True


# ---------- Analytics ----------
class AnalyticsOut(BaseModel):
    emails_processed_per_day: dict[str, int]
    replies_generated: int
    replies_sent: int
    avg_processing_time_seconds: float
    top_intents: dict[str, int]
    top_reply_styles: dict[str, int]
    success_rate: float
