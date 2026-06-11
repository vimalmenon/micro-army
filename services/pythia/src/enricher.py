"""Enricher — 4-round gap-driven web research for leads.

Each round: identify gaps → web search → LLM extract → fill fields.
Stops early if all fields are filled. Hard stop at 4 rounds.
Gracefully skips if no search API key is configured.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from config import settings
from models import ScoredLead

logger = logging.getLogger(__name__)

MAX_EVALS = 4

ENRICH_PROMPT = """You are a business research AI. Given web search results about a company, extract structured enrichment data.

Return ONLY valid JSON (no markdown, no code fences) with these fields:
{{
  "website": "<company website URL or null>",
  "linkedin": "<LinkedIn URL or null>",
  "contact_name": "<person found or null>",
  "contact_email": "<email or null>",
  "recent_news": ["<headline 1>", "<headline 2>"],
  "tech_stack": ["<tool 1>", "<tool 2>"],
  "funding": "<funding round details or null>",
  "budget_min": <minimum budget estimate or null>,
  "budget_max": <maximum budget estimate or null>,
  "budget_confidence": "<high|medium|low|null>"
}}

Budget confidence:
- high = explicitly stated
- medium = implied (funding, hiring, tool subscriptions)
- low = guessed from size cues

Company: {company}
Source context: {context}
Search results: {results}
"""


def _get_gaps(lead: ScoredLead) -> list[str]:
    """Identify what enrichment fields are still missing."""
    gaps = []
    if not lead.website:
        gaps.append("website")
    if not lead.linkedin:
        gaps.append("linkedin")
    if not lead.contact_name:
        gaps.append("contact_name")
    if not lead.contact_email:
        gaps.append("contact_email")
    if not lead.recent_news:
        gaps.append("recent_news")
    if not lead.tech_stack:
        gaps.append("tech_stack")
    if not lead.funding:
        gaps.append("funding")
    if lead.budget_min is None:
        gaps.append("budget")
    return gaps


def _build_search_query(lead: ScoredLead, gaps: list[str], round_num: int) -> str:
    """Build a search query focused on the current gaps."""
    company = lead.company or lead.title[:60]
    if round_num == 1:
        return f"{company} company"
    elif round_num == 2:
        return f"{company} {' '.join(gaps[:2])} contact"
    elif round_num == 3:
        return f"{company} funding news technology"
    else:
        return f"{company} {' '.join(gaps[:3])}"


def _build_enrichment_context(lead: ScoredLead) -> str:
    """Build a short context line describing the lead's situation."""
    parts = []
    if lead.pain_point:
        parts.append(f"Pain: {lead.pain_point}")
    if lead.fit_reason:
        parts.append(f"Fit: {lead.fit_reason}")
    if lead.source:
        parts.append(f"Source: {lead.source}")
    return " | ".join(parts) if parts else "No additional context"


async def _web_search(query: str) -> list[str]:
    """Run a web search via Google Custom Search API. Returns snippets."""
    if not settings.search_api_key or not settings.search_engine_id:
        logger.debug("No SEARCH_API_KEY configured — skipping web search")
        return []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": settings.search_api_key,
                    "cx": settings.search_engine_id,
                    "q": query,
                    "num": 5,
                },
            )
            if resp.status_code != 200:
                logger.warning("Search API returned %s: %s", resp.status_code, resp.text[:200])
                return []

            data = resp.json()
            items = data.get("items", [])
            return [
                f"{item.get('title', '')} — {item.get('snippet', '')}"
                for item in items
            ]
    except Exception as e:
        logger.warning("Search request failed: %s", e)
        return []


async def _extract_from_results(
    company: str, context: str, results: list[str], lead: ScoredLead,
) -> dict:
    """Send search results to LLM and extract structured enrichment data."""
    if not results:
        return {}

    prompt = ENRICH_PROMPT.format(
        company=company,
        context=context,
        results="\n".join(results),
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
                logger.warning("LLM enrichment returned %s: %s", resp.status_code, resp.text[:200])
                return {}

            result = resp.json()
            content = result["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            return json.loads(content)
    except Exception as e:
        logger.warning("Enrichment extraction failed for %s: %s", company, e)
        return {}


def _apply_enrichment(lead: ScoredLead, data: dict):
    """Apply extracted enrichment data to the lead, only filling null/empty fields."""
    if data.get("website") and not lead.website:
        lead.website = data["website"]
    if data.get("linkedin") and not lead.linkedin:
        lead.linkedin = data["linkedin"]
    if data.get("contact_name") and not lead.contact_name:
        lead.contact_name = data["contact_name"]
    if data.get("contact_email") and not lead.contact_email:
        lead.contact_email = data["contact_email"]
    if data.get("recent_news") and not lead.recent_news:
        lead.recent_news = data["recent_news"]
    if data.get("tech_stack") and not lead.tech_stack:
        lead.tech_stack = data["tech_stack"]
    if data.get("funding") and not lead.funding:
        lead.funding = data["funding"]
    if data.get("budget_min") is not None and lead.budget_min is None:
        lead.budget_min = data["budget_min"]
    if data.get("budget_max") is not None and lead.budget_max is None:
        lead.budget_max = data["budget_max"]
    if data.get("budget_confidence") and not lead.budget_confidence:
        lead.budget_confidence = data["budget_confidence"]


async def enrich_lead(lead: ScoredLead) -> ScoredLead:
    """Run the 4-round evaluation loop to enrich a lead.

    Returns the lead with enrichment fields populated (or unchanged if search is unavailable).
    """
    if not settings.search_api_key or not settings.search_engine_id:
        logger.info("No SEARCH_API_KEY configured — skipping enrichment")
        return lead

    company = lead.company or lead.title[:60]
    context = _build_enrichment_context(lead)
    enriched_something = False

    for round_num in range(1, MAX_EVALS + 1):
        gaps = _get_gaps(lead)
        if not gaps:
            logger.info("All enrichment fields filled for %s — stopping early", company)
            break

        query = _build_search_query(lead, gaps, round_num)
        logger.info("Enrich eval %d/%d for %s: query=%s, gaps=%s", round_num, MAX_EVALS, company, query, gaps)

        results = await _web_search(query)
        if not results:
            logger.info("No search results for eval %d — continuing", round_num)
            continue

        data = await _extract_from_results(company, context, results, lead)
        if data:
            _apply_enrichment(lead, data)
            enriched_something = True

    if enriched_something:
        lead.enriched_at = datetime.now(timezone.utc).isoformat()
        logger.info("Enrichment complete for %s — website=%s, linkedin=%s, contact=%s",
                     company, lead.website, lead.linkedin, lead.contact_name or lead.contact_email)

    return lead


async def enrich_leads(leads: list[ScoredLead]) -> list[ScoredLead]:
    """Enrich a batch of leads. Filters to hot (8+) only."""
    enriched: list[ScoredLead] = []
    for lead in leads:
        if lead.score >= 8:
            enriched.append(await enrich_lead(lead))
        else:
            enriched.append(lead)
    return enriched
