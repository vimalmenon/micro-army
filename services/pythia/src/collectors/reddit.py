"""Reddit collector — fetches posts from target subreddits via RSS."""

from __future__ import annotations

import logging

import feedparser
import httpx

from models import RawItem
from collectors.base import BaseCollector, register_collector

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "automation",
    "smallbusiness",
    "entrepreneur",
    "webdev",
    "SaaS",
    "startups",
]

RSS_TEMPLATE = "https://www.reddit.com/r/{subreddit}/.rss"

TIMEOUT_SEC = 15


@register_collector
class RedditCollector(BaseCollector):
    """Collect Reddit posts from target subreddits via Atom RSS feeds."""

    @property
    def source_name(self) -> str:
        return "reddit"

    async def collect(self) -> list[RawItem]:
        items: list[RawItem] = []
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
            for subreddit in SUBREDDITS:
                url = RSS_TEMPLATE.format(subreddit=subreddit)
                try:
                    resp = await client.get(url, headers={"User-Agent": "Pythia/1.0"})
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.warning("Reddit RSS fetch failed for '%s': %s", subreddit, exc)
                    continue

                try:
                    feed = feedparser.parse(resp.text)
                except Exception as exc:
                    logger.warning("Failed to parse Reddit RSS for '%s': %s", subreddit, exc)
                    continue

                for entry in feed.entries:
                    link = entry.get("link", "")
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))

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

        logger.info("Reddit collector returned %d items", len(items))
        return items
