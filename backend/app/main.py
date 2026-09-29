"""
Relay — AI Follow-Up Reply Assistant, backend entrypoint.

Run locally:
    pip install -r requirements.txt
    cp .env.example .env   # then fill in ANTHROPIC_API_KEY at minimum
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, accounts, emails, analytics, google_oauth


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Relay — AI Follow-Up Reply Assistant",
    description="Reads incoming emails, understands intent, and drafts 10 reply options per email.",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate limiting (protects the AI endpoints from runaway/bulk misuse) ---
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: exc)
app.add_middleware(SlowAPIMiddleware)

# --- Routers ---
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(google_oauth.router)
app.include_router(emails.router)
app.include_router(emails.replies_router)
app.include_router(analytics.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
