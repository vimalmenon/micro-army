"""Messages microservice — simple contact form submission for the website.

Posts messages to dynamo-svc's REST API instead of calling DynamoDB directly.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException

from config import settings
from models import CreateMessageRequest, HealthResponse, MessageResponse
from shared.logging import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

setup_logging("messages-svc")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting messages-svc...")
    yield
    logger.info("Shutting down messages-svc...")


app = FastAPI(
    title="messages-svc",
    description="Website contact form submission microservice",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Prometheus metrics ─────────────────────────
app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, include_in_schema=False)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        "app": "message",
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
