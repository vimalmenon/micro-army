"""Shared fixtures for clio tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings
from main import app, dynamo


@pytest.fixture(autouse=True)
def reset_dynamo_singleton():
    """Reset the DynamoClient singleton between tests."""
    from dynamo_client import DynamoClient

    DynamoClient._instance = None
    yield


@pytest.fixture
def mock_settings():
    """Provide test settings that don't require real AWS credentials."""
    return Settings(
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        aws_region="us-east-1",
        dynamo_endpoint_url="http://localhost:8000",
        dynamo_table_name="vimal",
    )


@pytest.fixture
def mock_dynamo_client() -> Generator[MagicMock, None, None]:
    """Mock the DynamoClient singleton so no real AWS calls are made."""
    with patch("main.DynamoClient") as mock_cls:
        instance = mock_cls.return_value
        instance.get_item.return_value = None
        instance.put_item.return_value = {"app": "message", "id": "test", "data": "value"}
        instance.update_item.return_value = {"app": "message", "data": "updated"}
        instance.delete_item.return_value = True
        instance.query.return_value = [{"app": "message", "id": "a"}, {"app": "message", "id": "b"}]
        instance.scan.return_value = [{"app": "x"}, {"app": "y"}, {"app": "z"}]
        instance.list_tables.return_value = ["vimal"]
        yield instance


@pytest.fixture
def client(mock_dynamo_client: MagicMock) -> TestClient:
    """FastAPI TestClient with a mocked DynamoClient singleton."""
    # Re-create the singleton so main.dynamo points to our mock
    import main as main_module

    main_module.dynamo = mock_dynamo_client

    with TestClient(app) as c:
        yield c
