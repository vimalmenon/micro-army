"""Telegram sender — sends messages via the Telegram Bot API."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class TelegramSender:
    """Sends text messages to a Telegram chat via the Bot API."""

    def __init__(self):
        self.api_base = settings.telegram_api_base.rstrip("/")
        self.bot_token = settings.telegram_bot_token
        self.default_chat_id = settings.telegram_chat_id

    @property
    def _send_url(self) -> str:
        return f"{self.api_base}/bot{self.bot_token}/sendMessage"

    def send(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
    ) -> tuple[bool, Optional[int], str]:
        """Send a text message. Returns (success, message_id, error)."""
        target = chat_id or self.default_chat_id
        if not self.bot_token:
            return False, None, "TELEGRAM_BOT_TOKEN not configured"
        if not target:
            return False, None, "no chat_id provided and no default configured"

        payload: dict = {"chat_id": target, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            resp = httpx.post(self._send_url, json=payload, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Telegram API request failed: %s", exc)
            return False, None, str(exc)

        if not data.get("ok"):
            err = data.get("description", "unknown error")
            logger.error("Telegram API returned error: %s", err)
            return False, None, err

        result = data.get("result", {})
        message_id = result.get("message_id")
        chat = result.get("chat", {})
        logger.info("Sent message_id=%s to chat=%s", message_id, chat.get("id", target))
        return True, message_id, ""


telegram_sender = TelegramSender()
