"""Tests for FastAPI routes — all DynamoDB calls are mocked."""

from unittest.mock import MagicMock

import pytest
from fastapi import status


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"status": "ok", "service": "messages-svc"}


class TestCreateMessage:
    def test_creates_message(self, client, mock_dynamo_client: MagicMock):
        body = {
            "name": "Alice",
            "email": "alice@example.com",
            "subject": "Hello",
            "message": "This is a test message",
        }
        saved = {
            "id": "abc-123",
            "name": "Alice",
            "email": "alice@example.com",
            "subject": "Hello",
            "message": "This is a test message",
            "read": False,
            "created_at": "2026-06-06T10:00:00+00:00",
            "updated_at": "2026-06-06T10:00:00+00:00",
        }
        mock_dynamo_client.put_item.return_value = saved

        resp = client.post("/messages", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["message"]["email"] == "alice@example.com"
        assert data["message"]["read"] is False
        assert "id" in data["message"]

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


class TestListMessages:
    def test_list_all(self, client, mock_dynamo_client: MagicMock):
        items = [
            {"id": "1", "name": "Alice", "email": "a@b.com", "read": False,
             "created_at": "2026-06-06T10:00:00+00:00", "updated_at": "2026-06-06T10:00:00+00:00"},
            {"id": "2", "name": "Bob", "email": "b@b.com", "read": True,
             "created_at": "2026-06-05T09:00:00+00:00", "updated_at": "2026-06-05T09:00:00+00:00"},
        ]
        mock_dynamo_client.scan.return_value = items

        resp = client.get("/messages")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["count"] == 2
        assert len(data["messages"]) == 2

    def test_filter_by_read(self, client, mock_dynamo_client: MagicMock):
        items = [
            {"id": "1", "read": True, "created_at": "2026-06-05T09:00:00+00:00"},
            {"id": "2", "read": False, "created_at": "2026-06-06T10:00:00+00:00"},
        ]
        mock_dynamo_client.scan.return_value = items

        resp = client.get("/messages?read=true")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["count"] == 1
        assert resp.json()["messages"][0]["id"] == "1"

    def test_filter_by_email(self, client, mock_dynamo_client: MagicMock):
        items = [{"id": "1", "email": "alice@test.com", "read": False,
                  "created_at": "2026-06-06T10:00:00+00:00", "updated_at": "2026-06-06T10:00:00+00:00"}]
        mock_dynamo_client.query.return_value = items

        resp = client.get("/messages?email=alice@test.com")
        assert resp.status_code == status.HTTP_200_OK
        mock_dynamo_client.query.assert_called_once()
        # Should use email-index
        assert resp.json()["count"] == 1

    def test_invalid_limit(self, client):
        resp = client.get("/messages?limit=999")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetMessage:
    def test_found(self, client, mock_dynamo_client: MagicMock):
        msg = {"id": "abc-123", "name": "Alice", "email": "a@b.com", "read": False,
               "created_at": "2026-06-06T10:00:00+00:00", "updated_at": "2026-06-06T10:00:00+00:00"}
        mock_dynamo_client.get_item.return_value = msg

        resp = client.get("/messages/abc-123")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["message"]["id"] == "abc-123"

    def test_not_found(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = None
        resp = client.get("/messages/nonexistent")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateMessage:
    def test_mark_read(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = {
            "id": "abc", "name": "Alice", "read": False,
        }
        mock_dynamo_client.update_item.return_value = {
            "id": "abc", "name": "Alice", "read": True,
            "updated_at": "2026-06-06T11:00:00+00:00",
        }

        resp = client.put("/messages/abc", json={"read": True})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["message"]["read"] is True

    def test_not_found(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = None
        resp = client.put("/messages/nonexistent", json={"read": True})
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteMessage:
    def test_deletes(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = {"id": "abc"}
        resp = client.delete("/messages/abc")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"deleted": True}

    def test_not_found(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = None
        resp = client.delete("/messages/nonexistent")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
