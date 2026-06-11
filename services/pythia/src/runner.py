"""Runner — orchestrates collect → score → store → deliver."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx

from collectors import get_all_collectors
from config import settings
from digest import categorize_leads, format_telegram_digest
from scorer import score_items
from store import lead_exists, list_leads, store_lead

logger = logging.getLogger(__name__)


async def run_pipeline() -> dict:
    """Execute the full lead pipeline. Returns stats dict."""
    stats = {
        "scanned": 0,
        "scored": 0,
        "new_leads": 0,
        "hot": 0,
        "warm": 0,
        "cold": 0,
        "errors": 0,
    }

    # Step 1: Collect
    all_items = []
    collectors = get_all_collectors()
    for collector in collectors:
        try:
            items = await collector.collect()
            # Filter out already-seen items
            new_items = []
            for item in items:
                if await lead_exists(item.url, item.source):
                    continue
                item.collected_at = datetime.now(timezone.utc).isoformat()
                new_items.append(item)
            all_items.extend(new_items)
            logger.info("Collector %s: %d new items (of %d total)", collector.source_name, len(new_items), len(items))
        except Exception as e:
            logger.error("Collector %s failed: %s", collector.source_name, e)
            stats["errors"] += 1

    stats["scanned"] = len(all_items)

    if not all_items:
        logger.info("No new items found")
        return stats

    # Step 2: Score
    leads = await score_items(all_items)
    stats["scored"] = len(leads)

    if not leads:
        logger.info("No leads scored 5+")
        return stats

    # Step 3: Store
    for lead in leads:
        success = await store_lead(lead)
        if success:
            stats["new_leads"] += 1
        else:
            stats["errors"] += 1

    # Step 4: Categorize (only active new leads)
    active_leads = [l for l in leads if l.status == "new"]
    hot, warm = categorize_leads(active_leads)
    stats["hot"] = len(hot)
    stats["warm"] = len(warm)
    stats["cold"] = stats["scanned"] - stats["scored"]

    # Step 5: Send digest
    if hot or warm:
        await send_digest(hot, warm, stats)

    return stats


async def send_digest(hot: list, warm: list, stats: dict) -> bool:
    """Send Telegram digest via Hermes cron delivery or direct API."""
    text = format_telegram_digest(
        hot=hot,
        warm=warm,
        total_scanned=stats["scanned"],
        cold_count=stats["cold"],
    )

    # Try direct Telegram API first
    if settings.telegram_bot_token and settings.telegram_chat_id:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": settings.telegram_chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                )
                if resp.status_code == 200:
                    logger.info("Digest sent via Telegram API")
                    return True
                else:
                    logger.warning("Telegram API returned %s: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning("Failed to send Telegram: %s", e)

    # Fallback: print the digest (for Hermes cron delivery)
    print("=== LEAD DIGEST ===")
    print(text)
    return True
