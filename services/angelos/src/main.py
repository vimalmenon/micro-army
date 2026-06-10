"""
Messages microservice — simple contact form submission for the website.

Posts messages to dynamo-svc's REST API instead of calling DynamoDB directly.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import quote as url_quote

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from config import settings
from models import CreateMessageRequest, HealthResponse, MessageDetail, MessageListResponse, MessageResponse, MessageUpdateResponse
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

setup_logging("angelos")
logger = logging.getLogger(__name__)

# DynamoDB partition key following CA# convention for single-table design
APP_PARTITION = "CA#ContactSubmission"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting angelos...")
    yield
    logger.info("Shutting down angelos...")


app = FastAPI(
    title="angelos",
    description="Website contact form submission microservice",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS (public contact form + admin read access) ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://completeautomate.com",
        "https://www.completeautomate.com",
    ],
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)

# ─── Prometheus metrics ─────────────────────────
app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, include_in_schema=False)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Root redirect ──────────────────────────────


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


# ─── Health ─────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse()


# ─── Submit Message ──────────────────────────────


@app.post("/messages", response_model=MessageResponse, status_code=201, tags=["messages"])
async def submit_message(body: CreateMessageRequest):
    """Submit a contact form message via dynamo-svc API."""
    now = _now()
    item = {
        "app": APP_PARTITION,
        "id": str(uuid.uuid4()),
        "name": body.name.strip(),
        "email": body.email.strip().lower(),
        "subject": body.subject.strip(),
        "message": body.message.strip(),
        "read": False,
        "created_at": now,
        "updated_at": now,
    }

    dynamo_svc_url = settings.dynamo_svc_url.rstrip("/")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{dynamo_svc_url}/vimal/item", json=item)

    if resp.status_code != 200:
        logger.error(
            "dynamo-svc returned %s: %s", resp.status_code, resp.text[:200]
        )
        raise HTTPException(
            status_code=502,
            detail=f"Failed to store message: upstream returned {resp.status_code}",
        )

    logger.info(
        "Message submitted: id=%s from=%s subject=%s",
        item["id"], item["email"], item["subject"],
    )
    return MessageResponse(id=item["id"])


# ─── List Messages ──────────────────────────────


@app.get("/messages", response_model=MessageListResponse, tags=["messages"])
async def list_messages(limit: int = 50):
    """List all contact form messages, newest first."""
    dynamo_svc_url = settings.dynamo_svc_url.rstrip("/")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{dynamo_svc_url}/vimal/scan",
            json={
                "filter_expression": "#app = :app_val",
                "expression_attr_values": {":app_val": APP_PARTITION},
                "expression_attr_names": {"#app": "app"},
                "limit": limit,
            },
        )

    if resp.status_code != 200:
        logger.error("dynamo-svc scan returned %s: %s", resp.status_code, resp.text[:200])
        raise HTTPException(
            status_code=502,
            detail=f"Failed to list messages: upstream returned {resp.status_code}",
        )

    data = resp.json()
    items = data.get("items", [])

    # Sort newest first by created_at
    items.sort(key=lambda m: m.get("created_at", ""), reverse=True)

    messages = [MessageDetail(**item) for item in items]
    return MessageListResponse(messages=messages, count=len(messages))


# ─── Get Message ────────────────────────────────


@app.get("/messages/{message_id}", response_model=MessageDetail, tags=["messages"])
async def get_message(message_id: str):
    """Get a single message by ID."""
    dynamo_svc_url = settings.dynamo_svc_url.rstrip("/")
    encoded_app = url_quote(APP_PARTITION, safe="")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{dynamo_svc_url}/vimal/item/{encoded_app}",
            params={"id": message_id},
        )

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Message not found")
    if resp.status_code != 200:
        logger.error("dynamo-svc get returned %s: %s", resp.status_code, resp.text[:200])
        raise HTTPException(
            status_code=502,
            detail=f"Failed to get message: upstream returned {resp.status_code}",
        )

    data = resp.json()
    return MessageDetail(**data["item"])


# ─── Mark Message as Read ────────────────────────


@app.patch("/messages/{message_id}/read", response_model=MessageUpdateResponse, tags=["messages"])
async def mark_read(message_id: str):
    """Mark a message as read."""
    dynamo_svc_url = settings.dynamo_svc_url.rstrip("/")
    now = _now()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.put(
            f"{dynamo_svc_url}/vimal/item",
            json={
                "key": {"app": APP_PARTITION, "id": message_id},
                "update_expression": "SET #read = :read, updated_at = :now",
                "expression_attr_values": {":read": True, ":now": now},
                "expression_attr_names": {"#read": "read"},
            },
        )

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Message not found")
    if resp.status_code != 200:
        logger.error("dynamo-svc update returned %s: %s", resp.status_code, resp.text[:200])
        raise HTTPException(
            status_code=502,
            detail=f"Failed to update message: upstream returned {resp.status_code}",
        )

    return MessageUpdateResponse(id=message_id, read=True)
