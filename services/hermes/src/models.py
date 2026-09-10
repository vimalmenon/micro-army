from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "hermes"


class SendMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4096)
    chat_id: Optional[str] = None  # defaults to configured chat
    parse_mode: Optional[str] = None  # "HTML", "MarkdownV2", or None for plain text


class SendMessageResponse(BaseModel):
    message_id: int
    chat_id: str
    status: str = "sent"
    sent_at: str = ""
