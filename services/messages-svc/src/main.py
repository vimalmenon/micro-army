"""Messages microservice — simple contact form submission for the website.

Table schema (DynamoDB, single table "vimal"):
  Table: vimal (configurable via DYNAMO_TABLE env var)
  PK: app (string) = "message" for messages (configurable via APP_PREFIX)
  SK: id (string, UUID v4)
  Attributes: app, id, name, email, subject, message, read, created_at, updated_at
"""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from config import settings
from dynamo_client import DynamoClient
from models import CreateMessageRequest, HealthResponse, MessageResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting messages-svc...")
    DynamoClient()
    yield
    logger.info("Shutting down messages-svc...")


app = FastAPI(
    title="messages-svc",
    description="Website contact form submission microservice",
    version="1.0.0",
    lifespan=lifespan,
)

dynamo = DynamoClient()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Health ─────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse()


# ─── Submit Message ──────────────────────────────


@app.post("/messages", response_model=MessageResponse, status_code=201, tags=["messages"])
async def submit_message(body: CreateMessageRequest):
    """Submit a contact form message from the website."""
    now = _now()
    item = {
        "app": settings.app_prefix,
        "id": str(uuid.uuid4()),
        "name": body.name.strip(),
        "email": body.email.strip().lower(),
        "subject": body.subject.strip(),
        "message": body.message.strip(),
        "read": False,
        "created_at": now,
        "updated_at": now,
    }
    dynamo.put_item(settings.dynamo_table_name, item)
    logger.info("Message submitted: id=%s from=%s subject=%s", item["id"], item["email"], item["subject"])
    return MessageResponse(id=item["id"])
