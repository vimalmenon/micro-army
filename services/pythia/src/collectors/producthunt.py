"""Product Hunt collector — fetches products via Product Hunt RSS feed."""

from __future__ import annotations

import logging

import feedparser
import httpx

from models import RawItem
from collectors.base import BaseCollector, register_collector

logger = logging.getLogger(__name__)

PH_FEED_URL = "https://www.producthunt.com/feed"

# Keywords to filter for tech/automation relevance
RELEVANT_KEYWORDS = [
    "automation",
    "AI",
    "workflow",
    "integrat",
    "bot",
    "developer tool",
    "SaaS",
    "API",
    "productivity",
    "no-code",
    "low-code",
    "DevOps",
    "pipeline",
    "deploy",
]

TIMEOUT_SEC = 15


def _is_relevant(title: str, body: str) -> bool:
    """Check if a PH post is related to tech/automation."""
    text = (title + " " + body).lower()
    for kw in RELEVANT_KEYWORDS:
        if kw.lower() in text:
            return True
    return False


@register_collector
class ProductHuntCollector(BaseCollector):
    """Collect products from Product Hunt RSS, filtering for tech/automation relevance."""

    @property
    def source_name(self) -> str:
        return "producthunt"

    async def collect(self) -> list[RawItem]:
        items: list[RawItem] = []
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC, follow_redirects=True) as client:
            try:
                resp = await client.get(PH_FEED_URL, headers={"User-Agent": "Pythia/1.0"})
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("Product Hunt RSS fetch failed: %s", exc)
                return []

            try:
                feed = feedparser.parse(resp.text)
            except Exception as exc:
                logger.warning("Failed to parse Product Hunt RSS: %s", exc)
                return []

            for entry in feed.entries:
                link = entry.get("link", "")
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))

                if not title and not link:
                    continue

                # Filter for relevance to tech/automation
                if not _is_relevant(title, summary):
                    continue

                items.append(
                    RawItem(
                        source=self.source_name,
                        url=link,
                        title=title,
                        body=summary,
                    )
                )

        logger.info("Product Hunt collector returned %d items", len(items))
        return items
