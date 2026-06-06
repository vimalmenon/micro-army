"""Tests for Settings configuration."""

import os
from unittest.mock import patch

from config import Settings, settings as global_settings


class TestSettings:
    def test_default_region(self):
        """Default region should be ap-southeast-1."""
        s = Settings()
        assert s.aws_region == "ap-southeast-1"

    def test_defaults_are_empty(self):
        """Sensitive keys default to empty string."""
        s = Settings()
        assert s.aws_access_key_id == ""
        assert s.aws_secret_access_key == ""

    def test_port_default(self):
        assert Settings().service_port == 8000

    def test_env_override(self):
        """Env vars should override defaults."""
        with patch.dict(
            os.environ,
            {
                "AWS_ACCESS_KEY_ID": "AKIA123",
                "AWS_SECRET_ACCESS_KEY": "secret123",
                "AWS_REGION": "us-east-1",
                "SERVICE_PORT": "9000",
            },
            clear=True,
        ):
            s = Settings()
            assert s.aws_access_key_id == "AKIA123"
            assert s.aws_secret_access_key == "secret123"
            assert s.aws_region == "us-east-1"
            assert s.service_port == 9000

    def test_dynamo_endpoint_url_none_by_default(self):
        s = Settings()
        assert s.dynamo_endpoint_url is None

    def test_dynamo_endpoint_url_from_env(self):
        with patch.dict(os.environ, {"DYNAMO_ENDPOINT_URL": "http://localhost:4566"}, clear=True):
            s = Settings()
            assert s.dynamo_endpoint_url == "http://localhost:4566"

    def test_global_settings_is_instance(self):
        """The module-level 'settings' should be a Settings instance."""
        assert isinstance(global_settings, Settings)
