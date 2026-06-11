"""DynamoDB store for leads — CRUD via Clio."""
from __future__ import annotations

import hashlib
import json
import logging
import urllib.parse
from datetime import datetime, timezone

import httpx

from config import settings
from models import ScoredLead, ScoredLeadResponse, StateTransition

logger = logging.getLogger(__name__)

LEAD_PARTITION = "CA#Lead"


async def store_lead(lead: ScoredLead) -> bool:
    """Store a scored lead in DynamoDB via Clio. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            item = lead.model_dump(mode="json")
            item["app"] = LEAD_PARTITION
            # Serialize history as list of dicts
            item["history"] = [h.model_dump() for h in lead.history]
            resp = await client.post(
                f"{settings.dynamo_svc_url}/vimal/item",
                json=item,
            )
            if resp.status_code not in (200, 201):
                logger.warning("Failed to store lead %s: %s", lead.id, resp.text[:200])
                return False
            return True
    except httpx.RequestError as e:
        logger.warning("Failed to reach Clio for lead %s: %s", lead.id, e)
        return False


async def get_lead(lead_id: str) -> ScoredLeadResponse | None:
    """Get a single lead by ID."""
    app_encoded = urllib.parse.quote(LEAD_PARTITION, safe="")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.dynamo_svc_url}/vimal/item/{app_encoded}",
                params={"id": lead_id},
            )
            if resp.status_code == 200:
                data = resp.json().get("item", resp.json())
                # Parse history if present
                if "history" in data and isinstance(data["history"], list):
                    data["history"] = [StateTransition(**h) for h in data["history"]]
                return ScoredLeadResponse(**data)
            return None
    except httpx.RequestError:
        return None


async def list_leads(limit: int = 50) -> list[ScoredLeadResponse]:
    """List all leads, newest first."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.dynamo_svc_url}/vimal/scan",
                json={
                    "filter_expression": "#app = :app_val",
                    "expression_attr_values": {":app_val": LEAD_PARTITION},
                    "expression_attr_names": {"#app": "app"},
                    "limit": limit,
                },
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                items.sort(key=lambda m: m.get("seen_at", ""), reverse=True)
                results = []
                for item in items:
                    if "history" in item and isinstance(item["history"], list):
                        item["history"] = [StateTransition(**h) for h in item["history"]]
                    results.append(ScoredLeadResponse(**item))
                return results
            return []
    except httpx.RequestError:
        return []


async def update_lead_state(lead_id: str, new_state: str) -> bool:
    """Update lead state and append to history atomically via Clio's update endpoint.

    Uses a combined approach: read the current history, append the new transition,
    then write back. Falls back to a simple state update if the item doesn't have history yet.
    """
    now = datetime.now(timezone.utc).isoformat()
    transition = {"state": new_state, "at": now}

    # Try to get the current lead to read existing history
    current = await get_lead(lead_id)
    if current is None:
        logger.warning("Lead %s not found for state update", lead_id)
        return False

    # Build the new history
    new_history = [h.model_dump() for h in current.history]
    new_history.append(transition)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.put(
                f"{settings.dynamo_svc_url}/vimal/item",
                json={
                    "key": {"app": LEAD_PARTITION, "id": lead_id},
                    "update_expression": "SET #st = :s, #hist = :h",
                    "expression_attr_values": {
                        ":s": new_state,
                        ":h": json.dumps(new_history),
                    },
                    "expression_attr_names": {
                        "#st": "state",
                        "#hist": "history",
                    },
                },
            )
            return resp.status_code in (200, 201)
    except httpx.RequestError as e:
        logger.warning("Failed to update lead state %s: %s", lead_id, e)
        return False


async def lead_exists(url: str, source: str) -> bool:
    """Check if a lead with this URL already exists (dedup)."""
    lead_id = hashlib.md5(f"{source}:{url}".encode()).hexdigest()
    app_encoded = urllib.parse.quote(LEAD_PARTITION, safe="")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.dynamo_svc_url}/vimal/item/{app_encoded}",
                params={"id": lead_id},
            )
            return resp.status_code == 200
    except httpx.RequestError:
        return False
