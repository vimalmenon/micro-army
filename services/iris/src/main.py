"""Email microservice — sends emails via SMTP and records them in DynamoDB."""

from __future__ import annotations

import logging
import urllib.parse
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException

from config import settings
from email_sender import email_sender
from models import (
    EmailRecord,
    EmailResponse,
    HealthResponse,
    SendEmailRequest,
    SubscribeRequest,
    SubscriberRecord,
    SubscriberResponse,
    UnsubscribeRequest,
    subscriber_id,
)
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

setup_logging("iris")
logger = logging.getLogger(__name__)

dynamo_svc_url = settings.dynamo_svc_url

# DynamoDB partition key following CA# convention for single-table design
APP_PARTITION = "CA#Message"
SUBSCRIBER_PARTITION = "CA#Subscriber"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting iris...")
    yield
    logger.info("Shutting down iris...")


app = FastAPI(
    title="iris",
    description="Send emails via SMTP and record in DynamoDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, methods=["GET"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(service="iris")


@app.post("/email", response_model=EmailResponse)
async def send_email(req: SendEmailRequest):
    """Send an email and record it in DynamoDB."""
    email_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Send the email
    success, error = email_sender.send(
        to=str(req.to),
        subject=req.subject,
        body=req.body,
        body_type=req.body_type,
        cc=[str(c) for c in req.cc] if req.cc else None,
    )

    if not success:
        logger.error("Failed to send email %s to %s: %s", email_id, req.to, error)
        # Still record the failure
        record = EmailRecord(
            id=email_id,
            to=str(req.to),
            subject=req.subject,
            body_preview=req.body[:100],
            status="failed",
            sent_at=now,
            error=error,
        )
        await _store_record(record)
        raise HTTPException(status_code=502, detail=error)

    # Record success
    record = EmailRecord(
        id=email_id,
        to=str(req.to),
        subject=req.subject,
        body_preview=req.body[:100],
        status="sent",
        sent_at=now,
        error="",
    )
    db_result = await _store_record(record)

    return EmailResponse(
        id=email_id,
        to=str(req.to),
        subject=req.subject,
        status="sent",
        sent_at=now,
    )


async def _store_record(record: EmailRecord) -> dict:
    """Store email record in DynamoDB via dynamo-svc."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            item = record.model_dump()
            item["app"] = APP_PARTITION
            resp = await client.post(
                f"{dynamo_svc_url}/vimal/item",
                json=item,
            )
            if resp.status_code not in (200, 201):
                logger.warning("Failed to store email record: %s", resp.text)
            return resp.json() if resp.status_code in (200, 201) else {}
    except httpx.RequestError as e:
        logger.warning("Failed to reach dynamo-svc for email record: %s", e)
        return {}


@app.get("/email/{email_id}", response_model=EmailRecord)
async def get_email(email_id: str):
    """Retrieve an email record from DynamoDB."""
    app_encoded = urllib.parse.quote(APP_PARTITION, safe="")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{dynamo_svc_url}/vimal/item/{app_encoded}",
                params={"id": email_id},
            )
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Email not found")
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch email record")
            data = resp.json()
            return EmailRecord(**data.get("item", data))
    except httpx.RequestError as e:
        logger.error("Failed to reach dynamo-svc: %s", e)
        raise HTTPException(status_code=502, detail="Backend unavailable")


# ─── Subscribe / Unsubscribe ─────────────────────


async def _store_subscriber(record: SubscriberRecord) -> dict:
    """Store subscriber record in DynamoDB via dynamo-svc."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            item = record.model_dump()
            item["app"] = SUBSCRIBER_PARTITION
            resp = await client.post(
                f"{dynamo_svc_url}/vimal/item",
                json=item,
            )
            if resp.status_code not in (200, 201):
                logger.warning("Failed to store subscriber: %s", resp.text)
            return resp.json() if resp.status_code in (200, 201) else {}
    except httpx.RequestError as e:
        logger.warning("Failed to reach dynamo-svc for subscriber: %s", e)
        return {}


async def _get_subscriber(email: str) -> dict | None:
    """Fetch a subscriber record from DynamoDB by email."""
    sub_id = subscriber_id(email)
    app_encoded = urllib.parse.quote(SUBSCRIBER_PARTITION, safe="")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{dynamo_svc_url}/vimal/item/{app_encoded}",
                params={"id": sub_id},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("item", data)
            return None
    except httpx.RequestError:
        return None


async def _query_subscribers() -> list[dict]:
    """Query all subscriber records from DynamoDB."""
    app_encoded = urllib.parse.quote(SUBSCRIBER_PARTITION, safe="")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Use scan to get all subscribers for this partition
            resp = await client.post(
                f"{dynamo_svc_url}/vimal/scan",
                json={
                    "filter_expression": "begins_with(#app, :app)",
                    "expression_attr_names": {"#app": "app"},
                    "expression_attr_values": {":app": SUBSCRIBER_PARTITION},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("items", [])
            return []
    except httpx.RequestError:
        return []


@app.post("/subscribe", response_model=SubscriberResponse, status_code=201)
async def subscribe(req: SubscribeRequest):
    """Subscribe an email address — idempotent. Re-activates if previously silenced."""
    now = datetime.now(timezone.utc).isoformat()
    existing = await _get_subscriber(str(req.email))

    if existing and not existing.get("silenced", False):
        # Already active — return existing
        return SubscriberResponse(
            email=existing["email"],
            name=existing.get("name", req.name),
            silenced=False,
            subscribed_at=existing["subscribed_at"],
        )

    sub_id = subscriber_id(str(req.email))
    record = SubscriberRecord(
        id=sub_id,
        email=str(req.email),
        name=req.name or (existing.get("name", "") if existing else ""),
        silenced=False,
        subscribed_at=existing["subscribed_at"] if existing else now,
        silenced_at=None,
    )

    await _store_subscriber(record)
    logger.info("Subscriber %s (%s) — %s", str(req.email), req.name or "no name",
                "re-activated" if existing else "new")

    return SubscriberResponse(
        email=record.email,
        name=record.name,
        silenced=False,
        subscribed_at=record.subscribed_at,
    )


@app.post("/unsubscribe", response_model=SubscriberResponse)
async def unsubscribe(req: UnsubscribeRequest):
    """Unsubscribe an email — sets silenced flag. Does NOT delete the record."""
    existing = await _get_subscriber(str(req.email))
    if not existing:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    now = datetime.now(timezone.utc).isoformat()
    sub_id = subscriber_id(str(req.email))
    app_encoded = urllib.parse.quote(SUBSCRIBER_PARTITION, safe="")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Update the existing subscriber to set silenced + silenced_at
            resp = await client.put(
                f"{dynamo_svc_url}/vimal/item",
                json={
                    "key": {"app": SUBSCRIBER_PARTITION, "id": sub_id},
                    "update_expression": "SET silenced = :s, silenced_at = :at",
                    "expression_attr_values": {":s": True, ":at": now},
                },
            )
            if resp.status_code not in (200, 201):
                logger.warning("Failed to update subscriber %s: %s", str(req.email), resp.text)
                raise HTTPException(status_code=502, detail="Failed to unsubscribe")
    except httpx.RequestError as e:
        logger.error("Failed to reach dynamo-svc: %s", e)
        raise HTTPException(status_code=502, detail="Backend unavailable")

    logger.info("Subscriber %s silenced", str(req.email))
    return SubscriberResponse(
        email=str(req.email),
        name=existing.get("name", ""),
        silenced=True,
        subscribed_at=existing.get("subscribed_at", ""),
        silenced_at=now,
    )


@app.get("/subscribers", response_model=list[SubscriberResponse])
async def list_subscribers():
    """List all subscribers with their status (active/silenced)."""
    items = await _query_subscribers()
    return [
        SubscriberResponse(
            email=item["email"],
            name=item.get("name", ""),
            silenced=item.get("silenced", False),
            subscribed_at=item.get("subscribed_at", ""),
            silenced_at=item.get("silenced_at"),
        )
        for item in items
    ]
