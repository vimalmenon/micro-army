"""Tests for shared.secrets module."""

import json
import os
from unittest.mock import MagicMock, patch

import botocore
import pytest

from secrets import SecretsManager


@pytest.fixture(autouse=True)
def reset():
    SecretsManager.reset()
    yield
    SecretsManager.reset()


@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_REGION": "ap-southeast-1",
        },
        clear=True,
    ):
        yield


@pytest.fixture
def mock_boto3():
    with patch("secrets.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps({"username": "admin", "password": "secret123"}),
        }
        mock_boto3.client.return_value = mock_client
        yield {"boto3": mock_boto3, "client": mock_client}


class TestSecretsManagerInit:
    def test_creates_client_once(self, mock_boto3):
        SecretsManager._get_client()
        mock_boto3["boto3"].client.assert_called_once_with(
            "secretsmanager",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            region_name="ap-southeast-1",
        )

    def test_reuses_cached_client(self, mock_boto3):
        c1 = SecretsManager._get_client()
        c2 = SecretsManager._get_client()
        assert c1 is c2
        mock_boto3["boto3"].client.assert_called_once()

    def test_initializes_lazily_on_get(self, mock_boto3):
        mock_boto3["boto3"].client.assert_not_called()
        SecretsManager.get_secret("test/secret")
        mock_boto3["boto3"].client.assert_called_once()


class TestGetSecret:
    def test_returns_parsed_json(self, mock_boto3):
        result = SecretsManager.get_secret("prod/db-creds")
        assert result == {"username": "admin", "password": "secret123"}

    def test_caches_result(self, mock_boto3):
        SecretsManager.get_secret("prod/db-creds")
        SecretsManager.get_secret("prod/db-creds")
        mock_boto3["client"].get_secret_value.assert_called_once()

    def test_separate_secrets_not_cached_together(self, mock_boto3):
        SecretsManager.get_secret("secret-a")
        SecretsManager.get_secret("secret-b")
        assert mock_boto3["client"].get_secret_value.call_count == 2

    def test_raises_on_missing_secret(self, mock_boto3):
        mock_boto3["client"].get_secret_value.side_effect = (
            botocore.exceptions.ClientError(
                {"Error": {"Code": "ResourceNotFoundException"}},
                "GetSecretValue",
            )
        )
        with pytest.raises(botocore.exceptions.ClientError):
            SecretsManager.get_secret("nonexistent/secret")

    def test_network_error(self, mock_boto3):
        mock_boto3["client"].get_secret_value.side_effect = (
            botocore.exceptions.BotoCoreError()
        )
        with pytest.raises(botocore.exceptions.BotoCoreError):
            SecretsManager.get_secret("network-error")


class TestEnvFallback:
    def test_defaults_region(self, mock_boto3):
        with patch.dict(os.environ, {"AWS_REGION": ""}, clear=True):
            kwargs = SecretsManager._build_client_kwargs()
            assert kwargs["region_name"] == "ap-southeast-1"

    def test_handles_missing_keys(self, mock_boto3):
        with patch.dict(os.environ, {}, clear=True):
            kwargs = SecretsManager._build_client_kwargs()
            assert kwargs == {"region_name": "ap-southeast-1"}


class TestCache:
    def test_clear_cache_forces_new_fetch(self, mock_boto3):
        SecretsManager.get_secret("test/secret")
        SecretsManager.clear_cache()
        SecretsManager.get_secret("test/secret")
        assert mock_boto3["client"].get_secret_value.call_count == 2

    def test_reset_clears_both_client_and_cache(self, mock_boto3):
        SecretsManager.get_secret("test/secret")
        SecretsManager.reset()
        SecretsManager.get_secret("test/secret")
        assert mock_boto3["boto3"].client.call_count == 2
