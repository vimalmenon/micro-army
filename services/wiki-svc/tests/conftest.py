"""Shared fixtures for wiki-svc tests — using httpx transport mocking."""
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from main import app


class MockDynamoTransport(httpx.MockTransport):
    """Mock transport that returns configured JSON responses."""

    def __init__(self) -> None:
        self.response_data: Any = {"ok": True}
        self.response_status: int = 200
        super().__init__(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=self.response_status, json=self.response_data)


@pytest.fixture
def mock_dynamo_transport() -> Generator[MockDynamoTransport, None, None]:
    """Replace httpx.AsyncClient with one using a mock transport."""
    transport = MockDynamoTransport()
    transport.response_data = {
        "app": "wiki", "id": "test-article", "title": "Test title",
        "content": "Test body", "tags": ["test"], "files": [],
        "author": "elara", "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    transport.response_status = 200

    # Capture the REAL AsyncClient before any patch is applied
    real_async_client = httpx.AsyncClient

    def make_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    with patch("main.httpx.AsyncClient", side_effect=make_client):
        yield transport


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
