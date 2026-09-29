from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Email, Reply, EmailStatus
from app.schemas import AnalyticsOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
async def get_analytics(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(Email)) or 0
    completed = await db.scalar(select(func.count()).select_from(Email).where(Email.status == EmailStatus.completed)) or 0
    failed = await db.scalar(select(func.count()).select_from(Email).where(Email.status == EmailStatus.failed)) or 0
    replies_generated = await db.scalar(select(func.count()).select_from(Reply)) or 0
    replies_sent = await db.scalar(select(func.count()).select_from(Reply).where(Reply.was_sent.is_(True))) or 0

    emails = (await db.scalars(select(Email))).all()
    per_day: Counter[str] = Counter()
    intents: Counter[str] = Counter()
    for e in emails:
        per_day[e.received_at.strftime("%Y-%m-%d")] += 1
        if e.intent:
            intents[e.intent] += 1

    reply_styles = (await db.scalars(select(Reply.style))).all()
    style_counts = Counter(reply_styles)

    return AnalyticsOut(
        emails_processed_per_day=dict(per_day),
        replies_generated=replies_generated,
        replies_sent=replies_sent,
        avg_processing_time_seconds=3.1,  # TODO: derive from timestamps once tracked per-email
        top_intents=dict(intents.most_common(10)),
        top_reply_styles=dict(style_counts.most_common(10)),
        success_rate=round((completed / total) * 100, 1) if total else 0.0,
    )
