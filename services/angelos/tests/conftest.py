"""Shared fixtures for angelos tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def mock_dynamo_svc() -> Generator[AsyncMock, None, None]:
    """Mock httpx.AsyncClient.post so no real HTTP calls are made."""
    mock_post = AsyncMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"item": {}}

    with patch("main.httpx.AsyncClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.post = mock_post
        yield mock_post


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
