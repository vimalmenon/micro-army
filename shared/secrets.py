from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class SecretsManager:
    """Fetch secrets from AWS Secrets Manager with in-memory caching.

    Each service still needs base AWS credentials (env vars or IAM role)
    to authenticate with Secrets Manager. Use this to fetch additional
    secrets at startup instead of baking them into config files or
    Kubernetes Secrets.

    Credentials are read from environment variables (AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY, AWS_REGION) — the same ones injected from
    the aws-dynamo-creds k8s secret.
    """

    _client: Any = None

    @classmethod
    def _build_client_kwargs(cls) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if key := os.environ.get("AWS_ACCESS_KEY_ID"):
            kwargs["aws_access_key_id"] = key
        if secret := os.environ.get("AWS_SECRET_ACCESS_KEY"):
            kwargs["aws_secret_access_key"] = secret
        if region := os.environ.get("AWS_REGION") or "ap-southeast-1":
            kwargs["region_name"] = region
        return kwargs

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            kwargs = cls._build_client_kwargs()
            cls._client = boto3.client("secretsmanager", **kwargs)
            logger.info(
                "AWS Secrets Manager client initialized (region=%s)",
                kwargs.get("region_name", "unknown"),
            )
        return cls._client

    @classmethod
    @lru_cache(maxsize=32)
    def get_secret(cls, secret_id: str) -> dict[str, Any]:
        """Fetch a secret from AWS Secrets Manager.

        Args:
            secret_id: The name or ARN of the secret (e.g. 'prod/db-password')

        Returns:
            Parsed JSON dict of the secret value.

        Raises:
            ClientError: If the secret doesn't exist or access is denied.
        """
        client = cls._get_client()
        try:
            resp = client.get_secret_value(SecretId=secret_id)
            secret_string = resp.get("SecretString", "{}")
            return json.loads(secret_string)
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to fetch secret '%s': %s", secret_id, e)
            raise

    @classmethod
    def clear_cache(cls):
        """Clear the LRU cache (useful during testing)."""
        cls.get_secret.cache_clear()

    @classmethod
    def reset(cls):
        """Reset the client (useful during testing)."""
        cls._client = None
        cls.clear_cache()
