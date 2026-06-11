"""Runner — orchestrates collect → score → enrich → store."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from collectors import get_all_collectors
from config import settings
from digest import categorize_leads
from enricher import enrich_leads
from scorer import score_items
from store import lead_exists, list_leads, store_lead

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def run_pipeline() -> dict:
    """Execute the full lead pipeline. Returns stats dict."""
    stats = {
        "scanned": 0,
        "scored": 0,
        "enriched": 0,
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

    # Step 3: Enrich (hot leads only, 4-round eval loop)
    leads = await enrich_leads(leads)
    stats["enriched"] = sum(1 for l in leads if l.enriched_at is not None)

    # Step 4: Store (max 1000 leads per run)
    MAX_LEADS = 1000
    if len(leads) > MAX_LEADS:
        logger.warning("Capping leads from %d to %d (safety limit)", len(leads), MAX_LEADS)
        leads = leads[:MAX_LEADS]
    for lead in leads:
        success = await store_lead(lead)
        if success:
            stats["new_leads"] += 1
        else:
            stats["errors"] += 1

    # Step 5: Categorize (only active discovery leads)
    active_leads = [l for l in leads if l.state == "discovery"]
    hot, warm = categorize_leads(active_leads)
    stats["hot"] = len(hot)
    stats["warm"] = len(warm)
    stats["cold"] = stats["scanned"] - stats["scored"]

    return stats
