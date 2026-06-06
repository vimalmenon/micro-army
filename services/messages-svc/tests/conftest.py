"""Shared fixtures for messages-svc tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app, dynamo


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
        instance.put_item.return_value = {"id": "new-id", "name": "test"}
        instance.update_item.return_value = {"id": "abc-123", "name": "Test", "read": True}
        instance.delete_item.return_value = True
        instance.query.return_value = []
        instance.scan.return_value = [
            {
                "id": "msg-1",
                "name": "Alice",
                "email": "alice@test.com",
                "subject": "Hello",
                "message": "Test message",
                "read": False,
                "created_at": "2026-06-06T10:00:00+00:00",
                "updated_at": "2026-06-06T10:00:00+00:00",
            },
            {
                "id": "msg-2",
                "name": "Bob",
                "email": "bob@test.com",
                "subject": "Support",
                "message": "Need help",
                "read": True,
                "created_at": "2026-06-05T09:00:00+00:00",
                "updated_at": "2026-06-05T09:00:00+00:00",
            },
        ]
        yield instance


@pytest.fixture
def client(mock_dynamo_client: MagicMock) -> TestClient:
    import main as main_module

    main_module.dynamo = mock_dynamo_client
    with TestClient(app) as c:
        yield c
