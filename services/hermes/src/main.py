"""Hermes — sends messages to Telegram via the Bot API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from config import settings
from models import HealthResponse, SendMessageRequest, SendMessageResponse
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler
from telegram_sender import telegram_sender

setup_logging("hermes")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting hermes...")
    yield
    logger.info("Shutting down hermes...")


app = FastAPI(
    title="hermes",
    description="Send messages to Telegram via the Bot API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, methods=["GET"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(service="hermes")


def _dispatch(req: SendMessageRequest, parse_mode: str | None) -> SendMessageResponse:
    success, message_id, error = telegram_sender.send(
        text=req.text,
        chat_id=req.chat_id,
        parse_mode=parse_mode,
    )
    if not success:
        logger.error("Failed to send Telegram message: %s", error)
        raise HTTPException(status_code=502, detail=f"Telegram send failed: {error}")

    chat_id = req.chat_id or settings.telegram_chat_id
    return SendMessageResponse(
        message_id=message_id or 0,
        chat_id=chat_id,
        sent_at=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/send", response_model=SendMessageResponse)
async def send_message(req: SendMessageRequest):
    """Send a plain-text (or parsed) message to Telegram."""
    return _dispatch(req, req.parse_mode)


@app.post("/send-html", response_model=SendMessageResponse)
async def send_html(req: SendMessageRequest):
    """Send an HTML-formatted message to Telegram."""
    return _dispatch(req, "HTML")
