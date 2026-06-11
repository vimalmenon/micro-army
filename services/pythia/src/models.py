from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "pythia"


class RawItem(BaseModel):
    """A raw item collected from a source, before scoring."""
    source: str
    url: str
    title: str
    body: str
    collected_at: str = ""


class ScoredLead(BaseModel):
    """A lead after LLM scoring, ready for storage."""
    id: str
    source: str
    url: str
    title: str
    body: str
    company: Optional[str] = None
    score: int = 0
    pain_point: str = ""
    fit_reason: str = ""
    angle: str = ""
    urgency: str = "low"
    status: str = "new"
    seen_at: str = ""


class ScoredLeadResponse(BaseModel):
    """Public response shape for a stored lead."""
    id: str
    source: str
    url: str
    title: str
    company: Optional[str] = None
    score: int
    pain_point: str
    fit_reason: str
    angle: str
    urgency: str
    status: str
    seen_at: str


class LeadStatusUpdate(BaseModel):
    """Request body for updating a lead's status."""
    status: str


class DigestMessage(BaseModel):
    """Formatted Telegram digest."""
    text: str
    stats: dict = {}
