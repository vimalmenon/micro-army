"""Tests for FastAPI routes — only health + submit endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi import status


class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"status": "ok", "service": "messages-svc"}


class TestSubmitMessage:
    def test_submits_successfully(self, client, mock_dynamo_svc: AsyncMock):
        body = {
            "name": "Alice",
            "email": "alice@example.com",
            "subject": "Hello",
            "message": "This is a test message",
        }
        resp = client.post("/messages", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["status"] == "submitted"
        assert len(data["id"]) == 36  # UUID4 length

        # Verify the HTTP call was made to dynamo-svc
        mock_dynamo_svc.assert_called_once()
        call_url = mock_dynamo_svc.call_args[0][0]
        call_json = mock_dynamo_svc.call_args[1]["json"]
        assert "vimal/item" in call_url
        assert call_json["app"] == "message"
        assert call_json["name"] == "Alice"
        assert call_json["email"] == "alice@example.com"

    def test_dynamo_svc_error(self, client, mock_dynamo_svc: AsyncMock):
        mock_dynamo_svc.return_value.status_code = 500
        mock_dynamo_svc.return_value.text = "Internal Server Error"

        resp = client.post(
            "/messages",
            json={
                "name": "Bob",
                "email": "bob@test.com",
                "subject": "Fail",
                "message": "Should 502",
            },
        )
        assert resp.status_code == 502
        assert "Failed to store message" in resp.json()["detail"]

    def test_invalid_email(self, client):
        resp = client.post(
            "/messages",
            json={
                "name": "Bad",
                "email": "not-an-email",
                "subject": "Test",
                "message": "Body",
            },
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_fields(self, client):
        resp = client.post("/messages", json={"name": "Incomplete"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_empty_body(self, client):
        resp = client.post("/messages", json={})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
