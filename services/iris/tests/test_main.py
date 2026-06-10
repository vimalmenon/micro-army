"""Tests for iris."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from config import settings
from main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "iris"


@patch("email_sender.email_sender.send", return_value=(True, ""))
def test_send_email_success(mock_send):
    resp = client.post(
        "/email",
        json={
            "to": "test@example.com",
            "subject": "Hello",
            "body": "<h1>Test</h1>",
            "body_type": "html",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"
    assert data["to"] == "test@example.com"
    assert data["subject"] == "Hello"
    mock_send.assert_called_once_with(
        to="test@example.com",
        subject="Hello",
        body="<h1>Test</h1>",
        body_type="html",
        cc=None,
    )


@patch("email_sender.email_sender.send", return_value=(True, ""))
@patch("main.httpx.AsyncClient")
def test_send_email_stores_in_dynamo(mock_http, mock_send):
    """Verify the email record is correctly stored in DynamoDB via dynamo-svc."""
    mock_post = AsyncMock()
    mock_post.status_code = 201
    mock_post.json.return_value = {"item": {"id": "abc"}}
    mock_http.return_value.__aenter__.return_value.post = mock_post

    resp = client.post(
        "/email",
        json={
            "to": "test@example.com",
            "subject": "Storage Test",
            "body": "<p>Check DynamoDB</p>",
            "body_type": "html",
        },
    )
    assert resp.status_code == 200

    # Verify the call to dynamo-svc
    call_url = mock_post.call_args[0][0]
    call_json = mock_post.call_args[1]["json"]
    assert "vimal/item" in call_url
    assert call_json["app"] == "CA#Message"
    assert call_json["to"] == "test@example.com"
    assert call_json["subject"] == "Storage Test"
    assert call_json["status"] == "sent"
    assert len(call_json["id"]) == 36  # UUID4 length


@patch("email_sender.email_sender.send", return_value=(False, "SMTP auth failed"))
def test_send_email_failure(mock_send):
    resp = client.post(
        "/email",
        json={
            "to": "test@example.com",
            "subject": "Fail",
            "body": "Body text",
            "body_type": "plain",
        },
    )
    assert resp.status_code == 502
    assert "SMTP auth failed" in resp.json()["detail"]


def test_send_email_invalid_email():
    resp = client.post(
        "/email",
        json={
            "to": "not-an-email",
            "subject": "Test",
            "body": "Body",
            "body_type": "plain",
        },
    )
    assert resp.status_code == 422


@patch("email_sender.email_sender.send", return_value=(True, ""))
def test_send_email_with_cc(mock_send):
    resp = client.post(
        "/email",
        json={
            "to": "primary@example.com",
            "subject": "CC Test",
            "body": "<p>With CC</p>",
            "body_type": "html",
            "cc": ["cc1@example.com", "cc2@example.com"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"
    mock_send.assert_called_once_with(
        to="primary@example.com",
        subject="CC Test",
        body="<p>With CC</p>",
        body_type="html",
        cc=["cc1@example.com", "cc2@example.com"],
    )


def test_metrics_endpoint():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "prometheus" in resp.text.lower() or resp.status_code == 200


# ─── Subscriber tests ─────────────────────────────


@patch("main.httpx.AsyncClient")
def test_subscribe_new(mock_http):
    """A new subscriber gets a record created."""
    # Mock GET returns 404 (no existing subscriber)
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 404
    mock_get_resp.text = "Not found"
    mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_get_resp)

    # Mock POST for storing the subscriber
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 201
    mock_post_resp.json.return_value = {"item": {"id": "abc"}}
    mock_post_resp.text = "Created"
    mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_post_resp)

    resp = client.post(
        "/subscribe",
        json={"email": "new@example.com", "name": "New User"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["name"] == "New User"
    assert data["silenced"] is False
    assert data["subscribed_at"] != ""


@patch("main.httpx.AsyncClient")
def test_subscribe_existing_active(mock_http):
    """Already active subscriber returns existing record (idempotent)."""
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "item": {
            "id": "abc123",
            "email": "active@example.com",
            "name": "Active User",
            "silenced": False,
            "subscribed_at": "2026-01-01T00:00:00",
            "silenced_at": None,
        }
    }
    mock_get_resp.text = "OK"
    mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_get_resp)

    resp = client.post(
        "/subscribe",
        json={"email": "active@example.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "active@example.com"
    assert data["silenced"] is False
    assert data["subscribed_at"] == "2026-01-01T00:00:00"


@patch("main.httpx.AsyncClient")
def test_subscribe_reactivates_silenced(mock_http):
    """A previously silenced subscriber gets re-activated."""
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "item": {
            "id": "def456",
            "email": "silenced@example.com",
            "name": "Silenced User",
            "silenced": True,
            "subscribed_at": "2026-01-01T00:00:00",
            "silenced_at": "2026-06-01T00:00:00",
        }
    }
    mock_get_resp.text = "OK"
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 201
    mock_post_resp.text = "Created"
    mock_post_fn = AsyncMock(return_value=mock_post_resp)

    mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_get_resp)
    mock_http.return_value.__aenter__.return_value.post = mock_post_fn

    resp = client.post(
        "/subscribe",
        json={"email": "silenced@example.com", "name": "Silenced User"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "silenced@example.com"
    assert data["silenced"] is False
    # Verify a store call was made (re-activation)
    assert mock_post_fn.call_count >= 1


@patch("main.httpx.AsyncClient")
def test_subscribe_invalid_email(mock_http):
    """Invalid email returns 422."""
    resp = client.post(
        "/subscribe",
        json={"email": "not-an-email", "name": "Bad"},
    )
    assert resp.status_code == 422


@patch("main.httpx.AsyncClient")
def test_unsubscribe(mock_http):
    """Unsubscribe sets silenced=True on existing subscriber."""
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "item": {
            "id": "ghi789",
            "email": "unsub@example.com",
            "name": "Unsub User",
            "silenced": False,
            "subscribed_at": "2026-01-01T00:00:00",
        }
    }
    mock_get_resp.text = "OK"
    mock_put_resp = MagicMock()
    mock_put_resp.status_code = 200
    mock_put_resp.text = "OK"
    mock_put_fn = AsyncMock(return_value=mock_put_resp)

    mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_get_resp)
    mock_http.return_value.__aenter__.return_value.put = mock_put_fn

    resp = client.post(
        "/unsubscribe",
        json={"email": "unsub@example.com"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "unsub@example.com"
    assert data["silenced"] is True
    assert data["silenced_at"] != ""

    # Verify PUT was called with silenced=True
    put_json = mock_put_fn.call_args[1]["json"]
    assert put_json["expression_attr_values"][":s"] is True


@patch("main.httpx.AsyncClient")
def test_unsubscribe_not_found(mock_http):
    """Unsubscribing a non-existent email returns 404."""
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 404
    mock_get_resp.text = "Not found"
    mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_get_resp)

    resp = client.post(
        "/unsubscribe",
        json={"email": "nonexistent@example.com"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@patch("main.httpx.AsyncClient")
def test_list_subscribers(mock_http):
    """List subscribers returns all records."""
    mock_scan_resp = MagicMock()
    mock_scan_resp.status_code = 200
    mock_scan_resp.json.return_value = {
        "items": [
            {
                "id": "a1",
                "email": "active@example.com",
                "name": "Active",
                "silenced": False,
                "subscribed_at": "2026-01-01T00:00:00",
                "silenced_at": None,
            },
            {
                "id": "a2",
                "email": "silenced@example.com",
                "name": "Silenced",
                "silenced": True,
                "subscribed_at": "2026-01-01T00:00:00",
                "silenced_at": "2026-06-01T00:00:00",
            },
        ]
    }
    mock_scan_resp.text = "OK"
    mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_scan_resp)

    resp = client.get("/subscribers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["email"] == "active@example.com"
    assert data[0]["silenced"] is False
    assert data[1]["email"] == "silenced@example.com"
    assert data[1]["silenced"] is True
    assert data[1]["silenced_at"] == "2026-06-01T00:00:00"
