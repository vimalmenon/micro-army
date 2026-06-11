"""LLM lead scorer — evaluates raw items and extracts structured lead data."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from config import settings
from models import RawItem, ScoredLead, StateTransition

logger = logging.getLogger(__name__)

SCORING_PROMPT = """You are a lead qualification AI for Complete Automate, a business 
automation consultancy that helps companies automate workflows, integrate AI,
and optimize operations. Given a post/comment from the web, evaluate it as a 
potential sales lead.

Score 1-10 where:
- 10 = Actively seeking automation help, has budget, clear pain point, easy to reach
- 7-9 = Exploring options, likely need, some positive signals
- 4-6 = Vague mention, might be worth monitoring
- 1-3 = Not relevant / no action needed

Return ONLY valid JSON (no markdown, no code fences) with these fields:
{{
  "score": <int 1-10>,
  "company": "<company or person name, or null>",
  "pain_point": "<what they need automated, be specific>",
  "fit_reason": "<why Complete Automate could help>",
  "angle": "<suggested outreach message angle>",
  "urgency": "<high|medium|low>"
}}

Post title: {title}
Post body: {body}
Source: {source}
"""


def _compute_id(url: str, source: str) -> str:
    """Deterministic ID from URL for dedup."""
    import hashlib
    raw = f"{source}:{url}"
    return hashlib.md5(raw.encode()).hexdigest()


async def score_item(item: RawItem) -> Optional[ScoredLead]:
    """Score a single raw item via LLM. Returns ScoredLead or None on failure."""
    if not settings.llm_api_key:
        logger.warning("No LLM_API_KEY configured — skipping scoring")
        return None

    prompt = SCORING_PROMPT.format(
        title=item.title[:500],
        body=item.body[:2000],
        source=item.source,
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
            )
            if resp.status_code != 200:
                logger.warning("LLM API returned %s: %s", resp.status_code, resp.text[:200])
                return None

            result = resp.json()
            content = result["choices"][0]["message"]["content"].strip()

            # Parse JSON from response (handle markdown code fences)
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            data = json.loads(content)
    except Exception as e:
        logger.warning("Failed to score item %s: %s", item.url[:80], e)
        return None

    import hashlib
    raw = f"{item.source}:{item.url}"
    item_id = hashlib.md5(raw.encode()).hexdigest()

    return ScoredLead(
        id=item_id,
        source=item.source,
        url=item.url,
        title=item.title,
        body=item.body[:500],
        company=data.get("company") or None,
        score=data.get("score") or 0,
        pain_point=data.get("pain_point") or "",
        fit_reason=data.get("fit_reason") or "",
        angle=data.get("angle") or "",
        urgency=data.get("urgency") or "low",
        state=data.get("status", "discovery"),
        seen_at=item.collected_at,
        history=[StateTransition(state=data.get("status", "discovery"), at=item.collected_at or datetime.now(timezone.utc).isoformat())],
    )


async def score_items(items: list[RawItem]) -> list[ScoredLead]:
    """Score multiple items in parallel (10 at a time via semaphore)."""
    sem = asyncio.Semaphore(10)

    async def _scored(item: RawItem) -> Optional[ScoredLead]:
        async with sem:
            return await score_item(item)

    results = await asyncio.gather(*[_scored(item) for item in items])
    return [lead for lead in results if lead and lead.score >= 5]
