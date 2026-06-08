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
from models import EmailRecord, EmailResponse, HealthResponse, SendEmailRequest
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

setup_logging("email-svc")
logger = logging.getLogger(__name__)

dynamo_svc_url = settings.dynamo_svc_url

# DynamoDB partition key following CA# convention for single-table design
APP_PARTITION = "CA#Message"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting email-svc...")
    yield
    logger.info("Shutting down email-svc...")


app = FastAPI(
    title="email-svc",
    description="Send emails via SMTP and record in DynamoDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, methods=["GET"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(service="email-svc")


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
