"""Indeed / Jobs collector — fetches job-related news via Google News RSS.

Indeed's native RSS feed (rss.indeed.com) returns HTTP 403 Forbidden,
so we use Google News RSS with targeted job search queries instead.
"""

from __future__ import annotations

import logging

import feedparser
import httpx

from models import RawItem
from collectors.base import BaseCollector, register_collector

logger = logging.getLogger(__name__)

# Job-related queries for the collector
QUERIES = [
    "automation engineer hiring",
    "workflow automation jobs",
    "AI integration consultant job",
    "automation specialist hiring",
    "remote automation engineer",
]

RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US"

TIMEOUT_SEC = 15


@register_collector
class IndeedCollector(BaseCollector):
    """Collect job-related news from Google News RSS for automation roles.

    Note: Indeed's own RSS (https://rss.indeed.com/rss) no longer
    allows programmatic access (returns 403). Google News RSS is
    used as a reliable proxy to surface hiring and job-market news.
    """

    @property
    def source_name(self) -> str:
        return "indeed"

    async def _fetch_rss(
        self, client: httpx.AsyncClient, url: str
    ) -> list[dict]:
        """Fetch and parse an RSS feed, returning the entries list."""
        try:
            resp = await client.get(url, headers={"User-Agent": "Pythia/1.0"})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Indeed RSS fetch failed: %s", exc)
            return []
        try:
            feed = feedparser.parse(resp.text)
            return feed.entries
        except Exception as exc:
            logger.warning("Failed to parse Indeed RSS: %s", exc)
            return []

    async def collect(self) -> list[RawItem]:
        items: list[RawItem] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(timeout=TIMEOUT_SEC, follow_redirects=True) as client:
            for query in QUERIES:
                url = RSS_TEMPLATE.format(query=query)
                entries = await self._fetch_rss(client, url)

                for entry in entries:
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

        logger.info("Indeed collector returned %d items", len(items))
        return items
