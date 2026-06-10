"""Shared fixtures for angelos tests."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def mock_dynamo_svc() -> Generator[tuple[AsyncMock, AsyncMock, AsyncMock, AsyncMock], Any, None]:
    """Mock httpx.AsyncClient so no real HTTP calls are made."""

    def _make_mock(initial_json=None):
        m = AsyncMock()
        m.return_value.status_code = 200
        m.return_value.text = ""
        # Use a mutable container so tests can override json return value
        json_container = {"json_data": initial_json or {"item": {}}}
        m.return_value.json = lambda: json_container["json_data"]
        # Allow tests to update the json return value
        m.set_json = lambda data: json_container.update({"json_data": data})
        return m

    mock_post = _make_mock()
    mock_get = _make_mock()
    mock_put = _make_mock()
    mock_delete = _make_mock()

    with patch("main.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.post = mock_post
        mock_client.get = mock_get
        mock_client.put = mock_put
        mock_client.delete = mock_delete
        yield mock_post, mock_get, mock_put, mock_delete


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
