"""DynamoDB store for leads — CRUD via Clio."""
from __future__ import annotations

import logging

import httpx

from config import settings
from models import ScoredLead, ScoredLeadResponse

logger = logging.getLogger(__name__)

LEAD_PARTITION = "CA#Lead"


async def store_lead(lead: ScoredLead) -> bool:
    """Store a scored lead in DynamoDB via Clio. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            item = lead.model_dump()
            item["app"] = LEAD_PARTITION
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
    import urllib.parse
    app_encoded = urllib.parse.quote(LEAD_PARTITION, safe="")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.dynamo_svc_url}/vimal/item/{app_encoded}",
                params={"id": lead_id},
            )
            if resp.status_code == 200:
                data = resp.json().get("item", resp.json())
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
                return [ScoredLeadResponse(**item) for item in items]
            return []
    except httpx.RequestError:
        return []


async def update_lead_status(lead_id: str, status: str) -> bool:
    """Update the status of a lead."""
    import urllib.parse
    app_encoded = urllib.parse.quote(LEAD_PARTITION, safe="")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.put(
                f"{settings.dynamo_svc_url}/vimal/item",
                json={
                    "key": {"app": LEAD_PARTITION, "id": lead_id},
                    "update_expression": "SET #st = :s",
                    "expression_attr_values": {":s": status},
                    "expression_attr_names": {"#st": "status"},
                },
            )
            return resp.status_code in (200, 201)
    except httpx.RequestError:
        return False


async def lead_exists(url: str, source: str) -> bool:
    """Check if a lead with this URL already exists (dedup)."""
    import hashlib
    import urllib.parse
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
