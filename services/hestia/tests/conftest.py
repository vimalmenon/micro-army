"""Conftest — fixtures for Hestia tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Import the app fresh for each test."""
    from src.main import app
    return app


@pytest.fixture
def client(app):
    """FastAPI TestClient."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_dynamo_scan():
    """Mock dynamo-svc scan endpoint. Returns configured items list."""
    def _make(items: list[dict] | None = None, status: int = 200):
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.json.return_value = {"items": items or [], "count": len(items or [])}

        patcher = patch("src.main.httpx.AsyncClient")
        mock_client = patcher.start()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        yield mock_client
        patcher.stop()

    return _make


@pytest.fixture
def mock_dynamo_get():
    """Mock dynamo-svc get endpoint."""
    def _make(item: dict | None = None, status: int = 200):
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.json.return_value = {"item": item} if item else {}

        patcher = patch("src.main.httpx.AsyncClient")
        mock_client = patcher.start()
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        yield mock_client
        patcher.stop()

    return _make


@pytest.fixture
def mock_dynamo_put():
    """Mock dynamo-svc put/update endpoint."""
    def _make(status: int = 200):
        mock_resp = MagicMock()
        mock_resp.status_code = status

        patcher = patch("src.main.httpx.AsyncClient")
        mock_client = patcher.start()
        mock_client.return_value.__aenter__.return_value.put = AsyncMock(return_value=mock_resp)
        yield mock_client
        patcher.stop()

    return _make


@pytest.fixture
def mock_dynamo_delete():
    """Mock dynamo-svc delete endpoint."""
    def _make(status: int = 200):
        mock_resp = MagicMock()
        mock_resp.status_code = status

        patcher = patch("src.main.httpx.AsyncClient")
        mock_client = patcher.start()
        mock_client.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_resp)
        yield mock_client
        patcher.stop()

    return _make


@pytest.fixture
def mock_pythia():
    """Mock Pythia leads endpoints."""
    def _make(data: dict | None = None, status: int = 200):
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.json.return_value = data or {}

        patcher = patch("src.main.httpx.AsyncClient")
        mock_client = patcher.start()
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        mock_client.return_value.__aenter__.return_value.patch = AsyncMock(return_value=mock_resp)
        yield mock_client, mock_resp
        patcher.stop()

    return _make


SAMPLE_MESSAGE = {
    "id": "msg-123",
    "app": "CA#ContactSubmission",
    "name": "John Doe",
    "email": "john@example.com",
    "subject": "Hello",
    "message": "Test message",
    "read": False,
    "created_at": "2026-06-12T10:00:00Z",
    "updated_at": "2026-06-12T10:00:00Z",
}
