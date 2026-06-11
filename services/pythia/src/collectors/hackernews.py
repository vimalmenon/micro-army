"""Hacker News collector — fetches posts via Algolia API."""

from __future__ import annotations

import logging

import httpx

from models import RawItem
from collectors.base import BaseCollector, register_collector

logger = logging.getLogger(__name__)

ALGOLIA_BY_DATE = "https://hn.algolia.com/api/v1/search_by_date"
ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"

# Tags: Ask HN and Show HN posts, up to 50
QUERY_ASKS = {
    "tags": "ask_hn,show_hn",
    "hitsPerPage": 50,
}

# Keyword search for "automation", up to 30
QUERY_AUTOMATION = {
    "query": "automation",
    "hitsPerPage": 30,
}

MIN_POINTS = 2

TIMEOUT_SEC = 15


@register_collector
class HackerNewsCollector(BaseCollector):
    """Collect posts from Hacker News via Algolia API."""

    @property
    def source_name(self) -> str:
        return "hackernews"

    async def _fetch(self, client: httpx.AsyncClient, url: str, params: dict) -> list[dict]:
        """Fetch a page of results from Algolia."""
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("hits", [])
        except httpx.HTTPError as exc:
            logger.warning("HN Algolia fetch failed (%s %s): %s", url, params, exc)
            return []
        except Exception as exc:
            logger.warning("HN Algolia parse error (%s %s): %s", url, params, exc)
            return []

    async def collect(self) -> list[RawItem]:
        items: list[RawItem] = []
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
            # 1. Ask HN / Show HN posts
            hits_asks = await self._fetch(client, ALGOLIA_BY_DATE, QUERY_ASKS)

            # 2. Automation keyword search
            hits_auto = await self._fetch(client, ALGOLIA_SEARCH, QUERY_AUTOMATION)

        all_hits = hits_asks + hits_auto

        for hit in all_hits:
            points = hit.get("points") or 0
            if points < MIN_POINTS:
                continue

            title = hit.get("title", "")
            url = hit.get("url") or hit.get("story_url") or ""
            # Fallback to HN discussion page if no external URL
            if not url:
                object_id = hit.get("objectID", "")
                url = f"https://news.ycombinator.com/item?id={object_id}"

            body = hit.get("story_text") or hit.get("comment_text") or ""
            # Clean up basic HTML entities if present
            if body:
                body = body.replace("<p>", "\n").replace("</p>", "")

            if not title:
                continue

            items.append(
                RawItem(
                    source=self.source_name,
                    url=url,
                    title=title,
                    body=body,
                )
            )

        logger.info("HN collector returned %d items", len(items))
        return items
