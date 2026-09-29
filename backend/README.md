# Relay — AI Follow-Up Reply Assistant (Backend)

FastAPI backend for an AI email assistant that reads incoming emails, understands
intent/tone/urgency, and drafts 10 stylistically distinct replies per email —
at a scale of up to 1,000 emails per batch, without blocking the UI.

## Quickstart

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env — at minimum set ANTHROPIC_API_KEY

python seed.py            # optional: adds a demo user + 3 sample emails
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Architecture

```
app/
  main.py            FastAPI app, CORS, rate limiting, router wiring
  config.py          Env-driven settings (pydantic-settings)
  database.py        Async SQLAlchemy engine/session (SQLite dev / Postgres prod)
  models.py          ORM: User, EmailAccount, Email, Reply, BulkJob
  schemas.py         Pydantic request/response models incl. EmailAnalysis
  security.py        JWT + bcrypt password hashing
  routers/
    auth.py          POST /auth/register, /auth/login
    accounts.py      POST /email/connect, GET/DELETE /email/accounts
    emails.py        Inbox CRUD, analyze, generate-replies, send, bulk-process
    analytics.py     GET /analytics
  services/
    ai_service.py       Claude prompts for analysis + 10-reply generation,
                         with anti-fabrication guardrails
    bulk_processor.py   Bounded-concurrency async batch runner + progress
    email_service.py    Gmail/Outlook/IMAP provider interface (stubbed —
                         fill in OAuth token exchange + API calls to go live)
```

## Why it scales to 1,000 emails

`POST /emails/bulk-process` returns a `job_id` immediately (202 Accepted) and
runs the actual work in the background via `bulk_processor.run_job`, which
fans out over all target emails behind an `asyncio.Semaphore` capped at
`AI_MAX_CONCURRENCY` (default 10). One email failing never aborts the batch —
each failure is caught, logged onto the `Email.error_message` field, and
recorded on the `BulkJob.failed_email_ids` list so the frontend can offer a
one-click retry (`POST /emails/bulk-retry/{job_id}`).

The frontend polls `GET /emails/bulk-status/{job_id}` for live progress
(processed / succeeded / failed counts) — see the mock version of this flow
in `frontend_prototype.html`.

**To scale past a single process:** swap the `BackgroundTasks.add_task(run_job, ...)`
call in `routers/emails.py` for a Celery task backed by Redis
(`process_job.delay(job_id)`). The per-email logic in `process_one_email`
doesn't need to change.

## AI safety design

`ai_service.py` separates what an email actually says (`known_information`)
from what the sender is asking about but we can't confirm
(`missing_information`). The reply-generation prompt is instructed to hedge
on anything in the latter bucket rather than invent an answer — e.g. it will
never say "your application has been approved" unless that fact was present
in the source thread. A lightweight lexical check (`_guard_against_fabrication`)
flags any reply that asserts a risky claim without hedging language, so it
surfaces for human review instead of being silently sendable.

## Extending to real inboxes

`services/email_service.py` defines the `EmailProvider` interface
(`fetch_inbox`, `send_reply`) with `GmailProvider` / `OutlookProvider` /
`ImapSmtpProvider` stubs. Each raises `NotImplementedError` with a note on
exactly which API call to wire up — Gmail's `users.messages` API, Microsoft
Graph's `/me/messages`, or IMAP/SMTP for anything else. No email password is
ever stored; OAuth access/refresh tokens are the only credentials persisted,
and should be encrypted at rest in production (see the `_encrypted` field
names in `models.EmailAccount` as a placeholder for that layer).

## API surface

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register`, `/auth/login` | Auth, returns JWT |
| POST | `/email/connect` | Connect Gmail/Outlook/IMAP account |
| GET | `/emails` | List inbox, with search/filter/pagination |
| GET | `/emails/{id}` | Email detail |
| POST | `/emails/{id}/analyze` | Run intent/tone/priority analysis |
| POST | `/emails/{id}/generate-replies` | Produce the 10 reply drafts |
| POST | `/emails/{id}/send` | Send a chosen reply |
| POST | `/emails/bulk-process` | Kick off a batch job (up to 1,000) |
| GET | `/emails/bulk-status/{job_id}` | Poll batch progress |
| POST | `/emails/bulk-retry/{job_id}` | Retry only the failed emails |
| POST | `/replies/{id}/regenerate` | Regenerate one reply in its own style |
| POST | `/replies/{id}/modify` | "Make it shorter / friendlier / ..." |
| GET | `/analytics` | Aggregate stats for the analytics dashboard |

## Notes on what's stubbed vs. real

- **Real**: DB schema, API contracts, async bulk-processing engine, AI prompts
  and anti-fabrication guardrails, auth/JWT, request validation.
- **Stubbed (clearly marked `TODO`)**: actual Gmail/Outlook OAuth token
  exchange and message fetch/send calls, encryption-at-rest for stored
  tokens, Celery/Redis wiring for multi-process scale.
