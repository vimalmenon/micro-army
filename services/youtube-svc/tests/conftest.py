"""Shared fixtures for youtube-svc tests — using httpx transport mocking."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from main import app


DEFAULT_VIDEO_ITEM = {
    "app": "youtube", "id": "test-video", "title": "Test Video",
    "description": "Test description", "tags": ["test"], "category_id": "22",
    "privacy_status": "private", "status": "draft", "youtube_id": "",
    "s3_key": "", "thumbnail_s3_key": "", "scheduled_at": "",
    "error_message": "", "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


class MockDynamoTransport(httpx.MockTransport):
    """Mock transport that returns path-aware responses for dynamo-svc."""

    def __init__(self) -> None:
        self.response_status: int = 200
        self.item_response: dict[str, Any] = {"item": DEFAULT_VIDEO_ITEM}
        self.scan_response: dict[str, Any] = {"items": [DEFAULT_VIDEO_ITEM], "count": 1}
        self.put_response: dict[str, Any] = {"ok": True}
        self.delete_response: dict[str, Any] = {"ok": True}

        # For test control — override these to simulate errors
        self.item_missing: bool = False
        self.scan_items: list[dict] | None = None
        self.fail_delete: bool = False
        super().__init__(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)

        if "/scan" in url:
            if self.scan_items is not None:
                return httpx.Response(status_code=self.response_status, json={"items": self.scan_items, "count": len(self.scan_items)})
            return httpx.Response(status_code=self.response_status, json=self.scan_response)

        if "/item/" in url and request.method == "GET":
            if self.item_missing:
                return httpx.Response(status_code=200, json={"item": None})
            return httpx.Response(status_code=self.response_status, json=self.item_response)

        if "/item/" in url and request.method == "DELETE":
            if self.fail_delete:
                return httpx.Response(status_code=500, json={"ok": False})
            return httpx.Response(status_code=self.response_status, json=self.delete_response)

        # POST /vimal/item — create/update
        if "/item" in url and request.method == "POST":
            return httpx.Response(status_code=self.response_status, json=self.put_response)

        return httpx.Response(status_code=200, json={"ok": True})


@pytest.fixture
def mock_dynamo_transport() -> Generator[MockDynamoTransport, None, None]:
    transport = MockDynamoTransport()
    transport.response_status = 200

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
