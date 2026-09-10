"""Tests for the TelegramSender."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from telegram_sender import TelegramSender


def test_send_returns_message_id_on_success():
    sender = TelegramSender()
    sender.bot_token = "test-token"
    sender.default_chat_id = "123"

    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    fake_resp.json.return_value = {
        "ok": True,
        "result": {"message_id": 42, "chat": {"id": 123}},
    }

    with patch("telegram_sender.httpx.post", return_value=fake_resp) as mock_post:
        success, message_id, error = sender.send("hello")

    assert success is True
    assert message_id == 42
    assert error == ""
    mock_post.assert_called_once()


def test_send_uses_explicit_chat_id():
    sender = TelegramSender()
    sender.bot_token = "test-token"
    sender.default_chat_id = "123"

    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    fake_resp.json.return_value = {"ok": True, "result": {"message_id": 7, "chat": {"id": 999}}}

    with patch("telegram_sender.httpx.post", return_value=fake_resp) as mock_post:
        success, _, _ = sender.send("hello", chat_id="999")

    assert success is True
    payload = mock_post.call_args.kwargs["json"]
    assert payload["chat_id"] == "999"


def test_send_fails_without_token():
    sender = TelegramSender()
    sender.bot_token = ""
    sender.default_chat_id = "123"

    success, message_id, error = sender.send("hello")
    assert success is False
    assert message_id is None
    assert "TELEGRAM_BOT_TOKEN" in error


def test_send_fails_when_api_returns_error():
    sender = TelegramSender()
    sender.bot_token = "test-token"
    sender.default_chat_id = "123"

    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    fake_resp.json.return_value = {"ok": False, "description": "Bad Request: chat not found"}

    with patch("telegram_sender.httpx.post", return_value=fake_resp):
        success, message_id, error = sender.send("hello")

    assert success is False
    assert message_id is None
    assert "Bad Request" in error
