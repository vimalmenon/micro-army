"""Tests for FastAPI routes — only health + submit endpoints."""

from unittest.mock import MagicMock

import pytest
from fastapi import status


class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"status": "ok", "service": "messages-svc"}


class TestSubmitMessage:
    def test_submits_successfully(self, client, mock_dynamo_client: MagicMock):
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
