"""Tests for Settings configuration."""

import os
from unittest.mock import patch

from config import Settings


class TestSettings:
    def test_default_region(self):
        assert Settings().aws_region == "ap-southeast-1"

    def test_defaults_are_empty(self):
        s = Settings()
        assert s.aws_access_key_id == ""
        assert s.aws_secret_access_key == ""

    def test_port_default(self):
        assert Settings().service_port == 8000

    def test_env_override(self):
        with patch.dict(
            os.environ,
            {
                "AWS_ACCESS_KEY_ID": "AKIA123",
                "AWS_SECRET_ACCESS_KEY": "secret456",
                "AWS_REGION": "us-west-2",
                "SERVICE_PORT": "9000",
            },
            clear=True,
        ):
            s = Settings()
            assert s.aws_access_key_id == "AKIA123"
            assert s.aws_secret_access_key == "secret456"
            assert s.aws_region == "us-west-2"
            assert s.service_port == 9000

    def test_dynamo_endpoint_url_default_none(self):
        assert Settings().dynamo_endpoint_url is None

    def test_dynamo_endpoint_url_from_env(self):
        with patch.dict(os.environ, {"DYNAMO_ENDPOINT_URL": "http://localhost:8000"}, clear=True):
            assert Settings().dynamo_endpoint_url == "http://localhost:8000"
