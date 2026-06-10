"""Tests for FastAPI routes — health, submit, list, get, mark-read."""

from unittest.mock import AsyncMock

import pytest
from fastapi import status


class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"status": "ok", "service": "angelos"}


class TestSubmitMessage:
    def test_submits_successfully(self, client, mock_dynamo_svc):
        mock_post, _, _, _ = mock_dynamo_svc
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
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        call_json = mock_post.call_args[1]["json"]
        assert "vimal/item" in call_url
        assert call_json["app"] == "CA#ContactSubmission"
        assert call_json["name"] == "Alice"
        assert call_json["email"] == "alice@example.com"

    def test_dynamo_svc_error(self, client, mock_dynamo_svc):
        mock_post, _, _, _ = mock_dynamo_svc
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal Server Error"

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


class TestListMessages:
    def test_lists_messages(self, client, mock_dynamo_svc):
        _, mock_get, _, _ = mock_dynamo_svc
        items = [
            {
                "id": "msg-1",
                "app": "CA#ContactSubmission",
                "name": "Alice",
                "email": "alice@example.com",
                "subject": "Hello",
                "message": "Test",
                "read": False,
                "created_at": "2026-06-10T12:00:00",
                "updated_at": "2026-06-10T12:00:00",
            },
            {
                "id": "msg-2",
                "app": "CA#ContactSubmission",
                "name": "Bob",
                "email": "bob@example.com",
                "subject": "Hi",
                "message": "Another",
                "read": True,
                "created_at": "2026-06-09T12:00:00",
                "updated_at": "2026-06-09T12:00:00",
            },
        ]
        mock_post, _, _, _ = mock_dynamo_svc
        mock_post.set_json({"items": items})

        resp = client.get("/messages?limit=50")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["count"] == 2
        assert data["messages"][0]["name"] == "Alice"
        assert data["messages"][1]["name"] == "Bob"

    def test_list_empty(self, client, mock_dynamo_svc):
        mock_post, _, _, _ = mock_dynamo_svc
        mock_post.set_json({"items": []})

        resp = client.get("/messages")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["count"] == 0
        assert data["messages"] == []

    def test_list_dynamo_error(self, client, mock_dynamo_svc):
        mock_post, _, _, _ = mock_dynamo_svc
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Dynamo error"

        resp = client.get("/messages")
        assert resp.status_code == 502
        assert "Failed to list messages" in resp.json()["detail"]


class TestGetMessage:
    def test_gets_message(self, client, mock_dynamo_svc):
        _, mock_get, _, _ = mock_dynamo_svc
        mock_get.set_json({
            "item": {
                "id": "msg-1",
                "app": "CA#ContactSubmission",
                "name": "Alice",
                "email": "alice@example.com",
                "subject": "Hello",
                "message": "Test body",
                "read": False,
                "created_at": "2026-06-10T12:00:00",
                "updated_at": "2026-06-10T12:00:00",
            }
        })

        resp = client.get("/messages/msg-1")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["name"] == "Alice"
        assert data["subject"] == "Hello"
        assert data["read"] is False

    def test_get_not_found(self, client, mock_dynamo_svc):
        _, mock_get, _, _ = mock_dynamo_svc
        mock_get.return_value.status_code = 404

        resp = client.get("/messages/nonexistent")
        assert resp.status_code == 404
        assert "Message not found" in resp.json()["detail"]

    def test_get_dynamo_error(self, client, mock_dynamo_svc):
        _, mock_get, _, _ = mock_dynamo_svc
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "Upstream error"

        resp = client.get("/messages/msg-1")
        assert resp.status_code == 502
        assert "Failed to get message" in resp.json()["detail"]


class TestMarkRead:
    def test_marks_read(self, client, mock_dynamo_svc):
        _, _, mock_put, _ = mock_dynamo_svc
        mock_put.return_value.json.return_value = {
            "item": {
                "id": "msg-1",
                "app": "CA#ContactSubmission",
                "name": "Alice",
                "email": "alice@example.com",
                "subject": "Hello",
                "message": "Test",
                "read": True,
                "created_at": "2026-06-10T12:00:00",
                "updated_at": "2026-06-10T12:01:00",
            }
        }

        resp = client.patch("/messages/msg-1/read")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == "msg-1"
        assert data["read"] is True
        assert data["status"] == "updated"

    def test_mark_read_not_found(self, client, mock_dynamo_svc):
        _, _, mock_put, _ = mock_dynamo_svc
        mock_put.return_value.status_code = 404

        resp = client.patch("/messages/nonexistent/read")
        assert resp.status_code == 404
        assert "Message not found" in resp.json()["detail"]

    def test_mark_read_dynamo_error(self, client, mock_dynamo_svc):
        _, _, mock_put, _ = mock_dynamo_svc
        mock_put.return_value.status_code = 500
        mock_put.return_value.text = "Upstream error"

        resp = client.patch("/messages/msg-1/read")
        assert resp.status_code == 502
        assert "Failed to update message" in resp.json()["detail"]


class TestDeleteMessage:
    def test_deletes_message(self, client, mock_dynamo_svc):
        _, _, _, mock_delete = mock_dynamo_svc

        resp = client.delete("/messages/msg-1")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == "msg-1"
        assert data["deleted"] is True
        assert data["status"] == "deleted"

        # Verify the HTTP call was made to dynamo-svc
        mock_delete.assert_called_once()

    def test_delete_not_found(self, client, mock_dynamo_svc):
        _, _, _, mock_delete = mock_dynamo_svc
        mock_delete.return_value.status_code = 404

        resp = client.delete("/messages/nonexistent")
        assert resp.status_code == 404
        assert "Message not found" in resp.json()["detail"]

    def test_delete_dynamo_error(self, client, mock_dynamo_svc):
        _, _, _, mock_delete = mock_dynamo_svc
        mock_delete.return_value.status_code = 500
        mock_delete.return_value.text = "Upstream error"

        resp = client.delete("/messages/msg-1")
        assert resp.status_code == 502
        assert "Failed to delete message" in resp.json()["detail"]
