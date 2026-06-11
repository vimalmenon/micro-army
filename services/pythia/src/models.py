"""Pythia models — lead data with enrichment and state workflow."""
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


class StateTransition(BaseModel):
    """A single state transition in the lead's history."""
    state: str
    at: str


class ScoredLead(BaseModel):
    """A lead after LLM scoring and optional enrichment, ready for storage."""
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
    state: str = "discovery"
    seen_at: str = ""

    # Enrichment fields (populated by enricher)
    website: Optional[str] = None
    linkedin: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    recent_news: list[str] = []
    tech_stack: list[str] = []
    funding: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    budget_confidence: Optional[str] = None
    enriched_at: Optional[str] = None

    # State workflow
    history: list[StateTransition] = []


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
    state: str
    seen_at: str
    website: Optional[str] = None
    linkedin: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    recent_news: list[str] = []
    tech_stack: list[str] = []
    funding: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    budget_confidence: Optional[str] = None
    enriched_at: Optional[str] = None
    history: list[StateTransition] = []


class LeadStateUpdate(BaseModel):
    """Request body for updating a lead's state."""
    state: str


class DigestMessage(BaseModel):
    """Formatted Telegram digest."""
    text: str
    stats: dict = {}
