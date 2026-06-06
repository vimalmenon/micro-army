"""Messages microservice — contact form / messaging for the website.

Table schema (DynamoDB):
  Table: messages
  PK: id (string, UUID v4)
  Attributes: id, name, email, subject, message, read, created_at, updated_at
  GSI: email-index (email → message)
"""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query

from config import settings
from dynamo_client import DynamoClient
from models import (
    CreateMessageRequest,
    DeleteResponse,
    HealthResponse,
    MessageListResponse,
    MessageResponse,
    UpdateMessageRequest,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TABLE_NAME = "messages"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting messages-svc...")
    DynamoClient()
    yield
    logger.info("Shutting down messages-svc...")


app = FastAPI(
    title="messages-svc",
    description="Website contact form / messages microservice",
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


# ─── Create Message ──────────────────────────────


@app.post("/messages", response_model=MessageResponse, status_code=201, tags=["messages"])
async def create_message(body: CreateMessageRequest):
    now = _now()
    item = {
        "id": str(uuid.uuid4()),
        "name": body.name.strip(),
        "email": body.email.strip().lower(),
        "subject": body.subject.strip(),
        "message": body.message.strip(),
        "read": False,
        "created_at": now,
        "updated_at": now,
    }
    dynamo.put_item(TABLE_NAME, item)
    logger.info("Message created: id=%s from=%s", item["id"], item["email"])
    return MessageResponse(message=item)


# ─── List Messages ──────────────────────────────


@app.get("/messages", response_model=MessageListResponse, tags=["messages"])
async def list_messages(
    limit: int = Query(50, ge=1, le=200),
    read: bool | None = None,
    email: str | None = None,
):
    """List messages with optional filtering by read status or email."""
    if email:
        # Query by GSI
        items = dynamo.query(
            TABLE_NAME,
            key_condition_expression="email = :email",
            expression_attr_values={":email": email},
            index_name="email-index",
            limit=limit,
        )
    else:
        items = dynamo.scan(TABLE_NAME, limit=limit)

    if read is not None:
        items = [i for i in items if i.get("read") is read]

    # Sort newest first
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return MessageListResponse(messages=items, count=len(items))


# ─── Get Single Message ─────────────────────────


@app.get("/messages/{message_id}", response_model=MessageResponse, tags=["messages"])
async def get_message(message_id: str):
    item = dynamo.get_item(TABLE_NAME, {"id": message_id})
    if item is None:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
    return MessageResponse(message=item)


# ─── Update Message (mark read / edit) ──────────


@app.put("/messages/{message_id}", response_model=MessageResponse, tags=["messages"])
async def update_message(message_id: str, body: UpdateMessageRequest):
    """Mark a message as read or update its fields."""
    # Check it exists first
    existing = dynamo.get_item(TABLE_NAME, {"id": message_id})
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found")

    # Build update expression
    updates: list[str] = []
    expr_attr_values: dict = {}
    expr_attr_names: dict = {}

    if body.read is not None:
        updates.append("#read = :read")
        expr_attr_values[":read"] = body.read
        expr_attr_names["#read"] = "read"

    if body.subject is not None:
        updates.append("#subject = :subject")
        expr_attr_values[":subject"] = body.subject
        expr_attr_names["#subject"] = "subject"

    updates.append("#updated_at = :updated_at")
    expr_attr_values[":updated_at"] = _now()
    expr_attr_names["#updated_at"] = "updated_at"

    update_expr = "SET " + ", ".join(updates)

    result = dynamo.update_item(
        TABLE_NAME,
        key={"id": message_id},
        update_expression=update_expr,
        expression_attr_values=expr_attr_values,
        expression_attr_names=expr_attr_names,
    )
    return MessageResponse(message=result)


# ─── Delete Message ──────────────────────────────


@app.delete("/messages/{message_id}", response_model=DeleteResponse, tags=["messages"])
async def delete_message(message_id: str):
    existing = dynamo.get_item(TABLE_NAME, {"id": message_id})
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
    dynamo.delete_item(TABLE_NAME, {"id": message_id})
    logger.info("Message deleted: id=%s", message_id)
    return DeleteResponse(deleted=True)
