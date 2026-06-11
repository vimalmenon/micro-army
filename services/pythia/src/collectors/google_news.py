"""Google News collector — fetches news articles via Google News RSS."""

from __future__ import annotations

import logging

import feedparser
import httpx

from models import RawItem
from collectors.base import BaseCollector, register_collector

logger = logging.getLogger(__name__)

QUERIES = [
    "automation services",
    "workflow automation",
    "need automation help",
    "AI integration consulting",
]

RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US"

TIMEOUT_SEC = 15


@register_collector
class GoogleNewsCollector(BaseCollector):
    """Collect news articles from Google News RSS related to automation queries."""

    @property
    def source_name(self) -> str:
        return "google_news"

    async def collect(self) -> list[RawItem]:
        items: list[RawItem] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(timeout=TIMEOUT_SEC, follow_redirects=True) as client:
            for query in QUERIES:
                url = RSS_TEMPLATE.format(query=query)
                try:
                    resp = await client.get(url, headers={"User-Agent": "Pythia/1.0"})
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.warning("Google News RSS fetch failed for '%s': %s", query, exc)
                    continue

                try:
                    feed = feedparser.parse(resp.text)
                except Exception as exc:
                    logger.warning("Failed to parse Google News RSS for '%s': %s", query, exc)
                    continue

                for entry in feed.entries:
                    link = entry.get("link", "")
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))

                    # Deduplicate across queries
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)

                    if not title and not link:
                        continue

                    items.append(
                        RawItem(
                            source=self.source_name,
                            url=link,
                            title=title,
                            body=summary,
                        )
                    )

        logger.info("Google News collector returned %d items", len(items))
        return items
