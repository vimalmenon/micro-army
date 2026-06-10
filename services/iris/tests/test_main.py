"""Tests for email-svc."""

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
    assert resp.json()["service"] == "email-svc"


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
