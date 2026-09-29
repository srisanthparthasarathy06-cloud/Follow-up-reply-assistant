"""
AI service — the intelligence core of the app.

Two responsibilities:
  1. analyze_email()   -> structured understanding (intent, tone, priority, etc.)
  2. generate_replies() -> exactly 10 stylistically distinct, non-fabricating drafts

Design choices:
- We ask Claude for strict JSON so responses map directly onto our Pydantic
  schemas (see schemas.py) instead of parsing free text.
- The prompt explicitly separates "known_information" (safe to state) from
  "missing_information" (must be hedged, never invented) — this is enforced
  again in a second pass over the generated replies (see _guard_against_fabrication).
- Retries with exponential backoff handle rate limits / transient failures
  without crashing a 1000-email batch.
"""
import json
import logging
from typing import Any

from anthropic import AsyncAnthropic, APIStatusError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.schemas import EmailAnalysis

logger = logging.getLogger("relay.ai")

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

REPLY_STYLES = [
    "Professional", "Formal", "Friendly", "Short & Direct", "Detailed",
    "Polite", "Reassuring", "Casual", "Highly Professional", "Custom AI Suggested",
]

_RETRYABLE = (APIStatusError, APIConnectionError)


def _retry_policy():
    return retry(
        reraise=True,
        stop=stop_after_attempt(settings.ai_max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(_RETRYABLE),
    )


def _extract_json(text: str) -> dict[str, Any]:
    """Claude is instructed to return raw JSON only; strip accidental fences defensively."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
    return json.loads(cleaned)


ANALYSIS_SYSTEM_PROMPT = """You are an email-understanding engine for an inbox assistant.
Read the email (and thread context, if provided) and extract a structured analysis.

Rules:
- Only put a fact in "known_information" if it is explicitly stated in the email or thread.
- Anything the sender is asking about that you cannot confirm from the given text
  (approval status, prices, dates, decisions, policies) goes in "missing_information".
- Never guess at information that isn't present.
- Respond with ONLY a single JSON object matching this schema, no prose, no markdown fences:

{
  "intent": string,
  "priority": "low" | "medium" | "high",
  "tone": string,
  "urgency": string,
  "sentiment": string,
  "required_action": string,
  "questions_asked": [string],
  "key_entities": [string],
  "relevant_dates": [string],
  "known_information": [string],
  "missing_information": [string],
  "summary": string (2-3 sentences)
}
"""

REPLIES_SYSTEM_PROMPT = """You are drafting reply options for a human to review and send.

You will receive: the original email, the structured analysis of it, and a list of
exactly 10 required styles. For EACH style, write one reply.

Hard safety rules (violating these is a critical failure):
- NEVER state or imply an outcome, approval, price, date, or promise that is not
  present in "known_information". If the sender asked about something listed in
  "missing_information", every reply must acknowledge the question and say it will
  be followed up on / is being looked into — without inventing the answer.
- Do not fabricate names, meeting details, or company policy.
- Each of the 10 replies must be genuinely different in wording and approach, not
  a copy-paste with a synonym swapped — vary sentence structure, length, and warmth
  to actually match the named style.
- Keep each reply to a realistic length for its style (Short & Direct: 1-2 sentences;
  Detailed: a full paragraph or two; others: a short paragraph).

Respond with ONLY a JSON array of exactly 10 objects, no prose, no markdown fences:
[{"style": string, "body": string}, ...]
"""


@_retry_policy()
async def analyze_email(subject: str, body: str, thread_context: str | None = None) -> EmailAnalysis:
    user_content = f"Subject: {subject}\n\nBody:\n{body}"
    if thread_context:
        user_content += f"\n\nPrevious thread context:\n{thread_context}"

    response = await _client.messages.create(
        model=settings.ai_model,
        max_tokens=1000,
        system=ANALYSIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    data = _extract_json(text)
    return EmailAnalysis(**data)


@_retry_policy()
async def generate_replies(
    subject: str, body: str, analysis: EmailAnalysis, thread_context: str | None = None
) -> list[dict[str, str]]:
    user_content = (
        f"Original email:\nSubject: {subject}\n\n{body}\n\n"
        f"Structured analysis:\n{analysis.model_dump_json(indent=2)}\n\n"
        f"Required styles (produce exactly these 10, in this order): {REPLY_STYLES}"
    )
    if thread_context:
        user_content += f"\n\nPrevious thread context:\n{thread_context}"

    response = await _client.messages.create(
        model=settings.ai_model,
        max_tokens=2500,
        system=REPLIES_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    replies = _extract_json(text)

    replies = _guard_against_fabrication(replies, analysis)
    return replies


def _guard_against_fabrication(replies: list[dict], analysis: EmailAnalysis) -> list[dict]:
    """
    Cheap lexical safety net on top of prompt instructions: if the analysis
    flagged missing information (e.g. "approval status") and a reply asserts
    a confident outcome verb without hedging language, flag it for human
    review rather than silently sending. This never blocks the UI — it just
    annotates so the frontend can visually warn the reviewer.
    """
    risky_terms = ["approved", "confirmed", "guaranteed", "definitely will", "has been accepted"]
    hedge_terms = ["review", "looking into", "will confirm", "currently", "update you", "pending"]

    if not analysis.missing_information:
        return replies

    for r in replies:
        body_lower = r["body"].lower()
        contains_risky = any(t in body_lower for t in risky_terms)
        contains_hedge = any(t in body_lower for t in hedge_terms)
        r["needs_review"] = bool(contains_risky and not contains_hedge)

    return replies


async def modify_reply(original_body: str, instruction: str, analysis: EmailAnalysis) -> str:
    """Used for 'make it shorter / friendlier / more professional' actions."""
    prompt = (
        f"Current reply draft:\n{original_body}\n\n"
        f"Context (do not contradict this): {analysis.summary}\n\n"
        f"Instruction: {instruction}\n\n"
        "Rewrite the reply following the instruction. Preserve all factual content "
        "and do not introduce any new facts, dates, or promises. "
        "Respond with ONLY the rewritten reply text, nothing else."
    )
    response = await _client.messages.create(
        model=settings.ai_model,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()
