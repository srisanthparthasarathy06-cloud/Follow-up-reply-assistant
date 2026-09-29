"""
Bulk-processing engine.

For a demo/dev deployment this runs as an asyncio background task with a
semaphore bounding concurrency (AI_MAX_CONCURRENCY) so we never blast 1000
simultaneous requests at the AI provider or block the event loop.

To scale beyond a single process, swap `asyncio.create_task(run_job(...))`
for a Celery task (`process_job.delay(job_id)`) backed by Redis — the
`run_job` body barely changes since it already isolates "do one email" from
"orchestrate the batch".
"""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models import Email, Reply, BulkJob, EmailStatus
from app.services import ai_service

logger = logging.getLogger("relay.bulk")


async def process_one_email(db: AsyncSession, email: Email) -> bool:
    """Analyze + generate 10 replies for a single email. Returns success flag."""
    try:
        email.status = EmailStatus.analyzing
        await db.commit()

        analysis = await ai_service.analyze_email(email.subject, email.body, email.thread_context)

        email.intent = analysis.intent
        email.priority = analysis.priority
        email.tone = analysis.tone
        email.summary = analysis.summary
        email.analysis_json = analysis.model_dump()
        email.status = EmailStatus.generating_replies
        await db.commit()

        replies = await ai_service.generate_replies(email.subject, email.body, analysis, email.thread_context)
        for r in replies:
            db.add(Reply(email_id=email.id, style=r["style"], body=r["body"]))

        email.status = EmailStatus.completed
        await db.commit()
        return True

    except Exception as exc:  # noqa: BLE001 — one bad email must never kill the batch
        logger.warning("Email %s failed: %s", email.id, exc)
        email.status = EmailStatus.failed
        email.error_message = str(exc)
        await db.commit()
        return False


async def run_job(job_id: str, email_ids: list[str], max_concurrency: int = 10) -> None:
    """Orchestrates a bulk job: bounded-concurrency fan-out over email_ids."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def worker(eid: str):
        async with semaphore:
            async with SessionLocal() as db:
                email = await db.get(Email, eid)
                if email is None:
                    return
                success = await process_one_email(db, email)

                job = await db.get(BulkJob, job_id)
                job.processed += 1
                if success:
                    job.succeeded += 1
                else:
                    job.failed += 1
                    job.failed_email_ids = [*job.failed_email_ids, eid]
                await db.commit()

    await asyncio.gather(*(worker(eid) for eid in email_ids))

    async with SessionLocal() as db:
        job = await db.get(BulkJob, job_id)
        job.status = "completed"
        from datetime import datetime
        job.finished_at = datetime.utcnow()
        await db.commit()


async def retry_failed(job_id: str) -> None:
    """Re-run only the emails that failed in a given job."""
    async with SessionLocal() as db:
        job = await db.get(BulkJob, job_id)
        failed_ids = list(job.failed_email_ids)
        job.failed_email_ids = []
        job.failed = 0
        job.status = "running"
        await db.commit()

    await run_job(job_id, failed_ids)
