"""
Hestia — admin backend microservice.

Goddess of the hearth, home, and central order.
Provides admin read/update endpoints for messages (from Clio) and leads (from Pythia),
decoupling the Helios admin dashboard from Angelos and Pythia.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import quote as url_quote

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from models import (
    HealthResponse,
    MessageDeleteResponse,
    MessageDetail,
    MessageListResponse,
    MessageUpdateResponse,
    PortfolioResponse,
)
from service_health import check_all_services, ServiceStatus
from cluster_nodes import get_cluster_nodes
from portfolio import get_portfolio
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

setup_logging("hestia")
logger = logging.getLogger(__name__)

# DynamoDB partition key for contact submissions (same as Angelos)
APP_PARTITION = "CA#ContactSubmission"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting hestia...")
    yield
    logger.info("Shutting down hestia...")


app = FastAPI(
    title="hestia",
    description="Admin backend — messages and leads management",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS (Helios admin dashboard only) ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://admin.completeautomate.com",
    ],
    allow_methods=["GET", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    max_age=600,
)

# ─── Prometheus metrics ─────────────────────────
app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, include_in_schema=False)


# ─── API Key Auth ────────────────────────────────


async def require_api_key(x_api_key: Annotated[str | None, Header()] = None):
    """Require a valid API key from the X-API-Key header."""
    if not settings.api_key:
        logger.warning("API_KEY not configured — auth disabled")
        return
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Health ─────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse()


# ─── Service Health (public, no auth required) ────


@app.get("/api/v1/services/status", tags=["system"])
async def services_status():
    """Check health of all internal microservices concurrently."""
    results = await check_all_services()
    return {"services": [s.__dict__ for s in results]}


# ─── Cluster Nodes (public, no auth required) ──────
# ─── Cluster Nodes (public, no auth required) ──────

@app.get("/api/v1/cluster/nodes", tags=["system"])
async def cluster_nodes():
    """List cluster nodes with CPU, memory, storage, and status."""
    nodes = await get_cluster_nodes()
    return {"nodes": nodes}


# ─── Portfolio (public, no auth required) ────────

@app.get("/portfolio", response_model=PortfolioResponse, tags=["portfolio"])
async def portfolio():
    """Live stock portfolio with current prices from yfinance."""
    return await get_portfolio()


# ─── Messages ────────────────────────────────────


@app.get("/messages", response_model=MessageListResponse, tags=["messages"], dependencies=[Depends(require_api_key)])
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


@app.get("/messages/{message_id}", response_model=MessageDetail, tags=["messages"], dependencies=[Depends(require_api_key)])
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


@app.patch("/messages/{message_id}/read", response_model=MessageUpdateResponse, tags=["messages"], dependencies=[Depends(require_api_key)])
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


@app.delete("/messages/{message_id}", response_model=MessageDeleteResponse, tags=["messages"], dependencies=[Depends(require_api_key)])
async def delete_message(message_id: str):
    """Delete a contact form message by ID."""
    dynamo_svc_url = settings.dynamo_svc_url.rstrip("/")
    encoded_app = url_quote(APP_PARTITION, safe="")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{dynamo_svc_url}/vimal/item/{encoded_app}",
            params={"id": message_id},
        )

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Message not found")
    if resp.status_code != 200:
        logger.error("dynamo-svc delete returned %s: %s", resp.status_code, resp.text[:200])
        raise HTTPException(
            status_code=502,
            detail=f"Failed to delete message: upstream returned {resp.status_code}",
        )

    logger.info("Message deleted: id=%s", message_id)
    return MessageDeleteResponse(id=message_id)


# ─── Leads (proxy to Pythia) ──────────────────────


@app.get("/leads", tags=["leads"], dependencies=[Depends(require_api_key)])
async def list_leads(limit: int = 100):
    """List all leads — proxies to Pythia."""
    pythia_url = settings.pythia_svc_url.rstrip("/")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{pythia_url}/leads", params={"limit": limit})
    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/leads/{lead_id}", tags=["leads"], dependencies=[Depends(require_api_key)])
async def get_lead(lead_id: str):
    """Get a single lead by ID — proxies to Pythia."""
    pythia_url = settings.pythia_svc_url.rstrip("/")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{pythia_url}/leads/{lead_id}")
    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.patch("/leads/{lead_id}", tags=["leads"], dependencies=[Depends(require_api_key)])
async def update_lead_state(lead_id: str, body: dict):
    """Update a lead's state — proxies to Pythia."""
    pythia_url = settings.pythia_svc_url.rstrip("/")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.patch(f"{pythia_url}/leads/{lead_id}", json=body)
    return JSONResponse(content=resp.json(), status_code=resp.status_code)
