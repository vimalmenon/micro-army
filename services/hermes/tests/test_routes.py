"""Tests for the Hermes API routes."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "hermes"


def test_send_returns_ok():
    with patch("main.telegram_sender.send", return_value=(True, 42, "")):
        resp = client.post("/send", json={"text": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "sent"
    assert body["message_id"] == 42


def test_send_html_forces_parse_mode():
    with patch("main.telegram_sender.send", return_value=(True, 1, "")) as mock_send:
        resp = client.post("/send-html", json={"text": "<b>hi</b>"})
    assert resp.status_code == 200
    # parse_mode should have been forced to HTML
    assert mock_send.call_args.kwargs["parse_mode"] == "HTML"


def test_send_returns_502_on_failure():
    with patch("main.telegram_sender.send", return_value=(False, None, "token missing")):
        resp = client.post("/send", json={"text": "hello"})
    assert resp.status_code == 502
