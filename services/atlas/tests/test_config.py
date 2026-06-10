"""Tests for atlas configuration."""

import os
from unittest.mock import patch

from config import Settings, settings


def test_settings_defaults():
    """Settings should use default values when env vars are not set."""
    with patch.dict(os.environ, {}, clear=True):
        s = Settings()
        assert s.aws_region == "us-east-1"
        assert s.aws_bucket == ""
        assert s.service_port == 8000


def test_settings_from_env():
    """Settings should read values from environment variables."""
    with patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_REGION": "ap-southeast-1",
            "AWS_S3_BUCKET": "my-bucket",
            "SERVICE_PORT": "9000",
        },
        clear=True,
    ):
        s = Settings()
        assert s.aws_access_key_id == "test-key"
        assert s.aws_secret_access_key == "test-secret"
        assert s.aws_region == "ap-southeast-1"
        assert s.aws_bucket == "my-bucket"
        assert s.service_port == 9000


def test_settings_singleton():
    """settings module-level singleton should be a Settings instance."""
    assert isinstance(settings, Settings)
