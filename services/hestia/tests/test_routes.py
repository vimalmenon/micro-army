"""Tests for Hestia routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .conftest import SAMPLE_MESSAGE


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "hestia"

    def test_health_no_auth(self, client):
        """Health endpoint should work without API key."""
        resp = client.get("/health")
        assert resp.status_code == 200


class TestAuth:
    def test_missing_api_key_returns_401(self, client):
        resp = client.get("/messages")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid or missing API key"

    def test_invalid_api_key_returns_401(self, client):
        resp = client.get("/messages", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid or missing API key"


class TestMessages:
    def test_list_messages_empty(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"items": [], "count": 0}
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

            resp = client.get("/messages", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] == 0
            assert data["messages"] == []

    def test_list_messages_with_items(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            items = [SAMPLE_MESSAGE]
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"items": items, "count": 1}
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

            resp = client.get("/messages", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] == 1
            assert data["messages"][0]["id"] == "msg-123"
            assert data["messages"][0]["name"] == "John Doe"

    def test_list_messages_upstream_error(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 502
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

            resp = client.get("/messages", headers=headers)
            assert resp.status_code == 502

    def test_get_message_found(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"item": SAMPLE_MESSAGE}
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

            resp = client.get("/messages/msg-123", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "msg-123"
            assert data["email"] == "john@example.com"

    def test_get_message_not_found(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.json.return_value = {}
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

            resp = client.get("/messages/nonexistent", headers=headers)
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Message not found"

    def test_mark_read(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_http.return_value.__aenter__.return_value.put = AsyncMock(return_value=mock_resp)

            resp = client.patch("/messages/msg-123/read", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "msg-123"
            assert data["read"] is True

    def test_delete_message(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_http.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_resp)

            resp = client.delete("/messages/msg-123", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "msg-123"

    def test_delete_message_not_found(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_http.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_resp)

            resp = client.delete("/messages/nonexistent", headers=headers)
            assert resp.status_code == 404


class TestLeads:
    def test_list_leads(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"leads": [], "count": 0}
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

            resp = client.get("/leads", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] == 0

    def test_get_lead(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"id": "lead-1", "name": "Test Lead"}
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

            resp = client.get("/leads/lead-1", headers=headers)
            assert resp.status_code == 200
            assert resp.json()["id"] == "lead-1"

    def test_update_lead_state(self, client, headers):
        with patch("src.main.httpx.AsyncClient") as mock_http:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"success": True, "lead_id": "lead-1", "state": "contacted"}
            mock_http.return_value.__aenter__.return_value.patch = AsyncMock(return_value=mock_resp)

            resp = client.patch("/leads/lead-1", json={"state": "contacted"}, headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["state"] == "contacted"
