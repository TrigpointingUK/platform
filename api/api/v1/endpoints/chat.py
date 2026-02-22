"""
Chat endpoint — SSE streaming responses from the RAG chat agent.
"""

import json
import logging
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.core.config import settings
from api.db.database import get_db
from api.services.chat.agent import stream_response

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _rate_limit_key(request: Request) -> str:
    """Extract an identifier for basic rate limiting."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Simple in-memory rate limiter: max requests per IP per minute
_rate_limits: dict[str, list[float]] = {}
MAX_REQUESTS_PER_MINUTE = 10


def _check_rate_limit(key: str) -> bool:
    now = time.time()
    window = _rate_limits.setdefault(key, [])
    # Remove entries older than 60 seconds
    _rate_limits[key] = [t for t in window if now - t < 60]
    if len(_rate_limits[key]) >= MAX_REQUESTS_PER_MINUTE:
        return False
    _rate_limits[key].append(now)
    return True


@router.post("")
async def chat(
    body: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Stream a chat response as Server-Sent Events."""
    if not settings.OPENAI_API_KEY:
        return StreamingResponse(
            iter(
                [
                    'data: {"type":"error","message":"Chat is not configured (missing OPENAI_API_KEY)."}\n\n'
                ]
            ),
            media_type="text/event-stream",
            status_code=503,
        )

    ip = _rate_limit_key(request)
    if not _check_rate_limit(ip):
        return StreamingResponse(
            iter(
                [
                    'data: {"type":"error","message":"Rate limit exceeded. Please wait a moment."}\n\n'
                ]
            ),
            media_type="text/event-stream",
            status_code=429,
        )

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    def event_stream():
        try:
            for event in stream_response(messages, db):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            logger.exception("SSE stream error")
            yield f'data: {json.dumps({"type": "error", "message": str(exc)})}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
