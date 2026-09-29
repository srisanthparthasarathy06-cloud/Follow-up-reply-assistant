"""
Populate the dev database with a demo user, one connected account, and a
handful of sample emails so the API/UI have something to show immediately.

Usage: python seed.py
"""
import asyncio

from app.database import init_db, SessionLocal
from app.models import User, EmailAccount, Email
from app.security import hash_password

SAMPLE_EMAILS = [
    dict(
        sender="John Smith <john.smith@outerlinecorp.com>",
        subject="Application Status",
        body="Hi,\n\nI wanted to check whether my application has been reviewed. "
             "I submitted it last week but haven't received an update yet.\n\nThanks,\nJohn",
    ),
    dict(
        sender="Sarah Lee <sarah.lee@finch.io>",
        subject="Meeting Reschedule",
        body="Hi, I won't be able to attend tomorrow's 10 AM meeting due to a personal "
             "commitment. Could we move it to Friday afternoon?",
    ),
    dict(
        sender="Alex Omondi <alex@brightpay.com>",
        subject="Payment Question — Invoice #2291",
        body="Hello, I noticed invoice #2291 hasn't been marked as paid yet even though "
             "we sent payment last Tuesday. Can you confirm receipt?",
    ),
]


async def main():
    await init_db()
    async with SessionLocal() as db:
        user = User(email="demo@relay.ai", hashed_password=hash_password("demo1234"))
        db.add(user)
        await db.commit()
        await db.refresh(user)

        account = EmailAccount(user_id=user.id, provider="gmail", email_address="demo@relay.ai")
        db.add(account)
        await db.commit()
        await db.refresh(account)

        for item in SAMPLE_EMAILS:
            db.add(Email(account_id=account.id, recipient=user.email, **item))
        await db.commit()

    print("Seeded demo user: demo@relay.ai / demo1234")
    print(f"Added {len(SAMPLE_EMAILS)} sample emails.")


if __name__ == "__main__":
    asyncio.run(main())
