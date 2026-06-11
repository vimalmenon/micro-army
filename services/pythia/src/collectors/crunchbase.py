"""Crunchbase-style collector — fetches recent funding/startup news via Google News RSS."""

from __future__ import annotations

import logging

import feedparser
import httpx

from models import RawItem
from collectors.base import BaseCollector, register_collector

logger = logging.getLogger(__name__)

QUERIES = [
    "raised funding automation",
    "series A funding startup",
    "seed funding automation",
    "raised capital workflow",
]

RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US"

TIMEOUT_SEC = 15


@register_collector
class CrunchbaseCollector(BaseCollector):
    """Collect startup/news about funding rounds from Google News RSS.

    Crunchbase's native RSS feed requires an API key, so we use Google News
    with targeted funding/startup queries as a proxy.
    """

    @property
    def source_name(self) -> str:
        return "crunchbase"

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
                    logger.warning("Crunchbase Google News fetch failed for '%s': %s", query, exc)
                    continue

                try:
                    feed = feedparser.parse(resp.text)
                except Exception as exc:
                    logger.warning("Failed to parse Crunchbase RSS for '%s': %s", query, exc)
                    continue

                for entry in feed.entries:
                    link = entry.get("link", "")
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))

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

        logger.info("Crunchbase collector returned %d items", len(items))
        return items
