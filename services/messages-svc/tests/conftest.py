"""Shared fixtures for messages-svc tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(autouse=True)
def reset_dynamo_singleton():
    from dynamo_client import DynamoClient

    DynamoClient._instance = None
    yield


@pytest.fixture
def mock_dynamo_client() -> Generator[MagicMock, None, None]:
    with patch("main.DynamoClient") as mock_cls:
        instance = mock_cls.return_value
        instance.get_item.return_value = None
        instance.put_item.return_value = {
            "app": "message", "id": "abc-123", "name": "Alice", "read": False,
        }
        instance.delete_item.return_value = True
        instance.scan.return_value = []
        instance.query.return_value = []
        yield instance


@pytest.fixture
def client(mock_dynamo_client: MagicMock) -> Generator[TestClient, None, None]:
    import main as main_module

    main_module.dynamo = mock_dynamo_client
    with TestClient(app) as c:
        yield c
