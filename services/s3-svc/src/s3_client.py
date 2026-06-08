"""S3 client wrapping boto3 for upload/download/delete/list operations.

Credentials come from the Settings singleton (injected via env vars by ESO).
Singleton pattern matches dynamo-svc's DynamoClient.
"""

import logging

import boto3
from botocore.exceptions import ClientError

from config import settings
from models import detect_content_type, s3_key_for, s3_data_from_path

logger = logging.getLogger(__name__)


class S3Client:
    """S3 client singleton wrapping boto3 operations.

    Usage:
        client = S3Client()
        client.upload_bytes(b"data", "file.txt")
    """

    _instance: "S3Client | None" = None

    def __new__(cls) -> "S3Client":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.bucket = settings.aws_bucket
        self.s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        logger.info(
            "S3Client initialized",
            extra={"bucket": self.bucket, "region": settings.aws_region},
        )

    # ─── Upload ───────────────────────────────────────

    def upload_bytes(
        self, data: bytes, name: str, key: str | None = None
    ) -> bool:
        """Upload bytes to S3, organized by content type.

        Returns True on success, False on error.
        """
        s3_key = s3_key_for(name, key=key)
        content_type = detect_content_type(name)
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=data,
                ContentType=content_type.value,
            )
            logger.info("Uploaded", extra={"s3_key": s3_key, "size": len(data)})
            return True
        except ClientError as e:
            logger.error("Upload failed", extra={"s3_key": s3_key, "error": str(e)})
            return False

    # ─── Download ─────────────────────────────────────

    def get_bytes(self, name: str, key: str | None = None) -> bytes:
        """Retrieve raw bytes from S3.

        Raises RuntimeError on failure.
        """
        s3_key = s3_key_for(name, key=key)
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
            data = response["Body"].read()
            logger.info("Retrieved bytes", extra={"s3_key": s3_key, "size": len(data)})
            return data
        except ClientError as e:
            logger.error("Get bytes failed", extra={"s3_key": s3_key, "error": str(e)})
            raise RuntimeError(f"S3 error getting {s3_key}: {e}")

    # ─── Delete ────────────────────────────────────────

    def delete(self, name: str, key: str | None = None, silent: bool = False) -> bool:
        """Delete a file from S3.

        When silent=True, 404 (Not Found) errors are swallowed.
        Returns True on success (or silent 404).
        Raises RuntimeError on other errors.
        """
        s3_key = s3_key_for(name, key=key)
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info("Deleted", extra={"s3_key": s3_key})
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if silent and error_code == "404":
                return True
            logger.error("Delete failed", extra={"s3_key": s3_key, "error": str(e)})
            raise RuntimeError(f"S3 error deleting {s3_key}: {e}")

    # ─── List ──────────────────────────────────────────

    def list_items(self, prefix: str = "", max_keys: int = 1000) -> list[dict]:
        """List objects in the bucket, optionally filtered by prefix.

        Returns a list of dicts with key/name/content_type.
        """
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket, Prefix=prefix, MaxKeys=max_keys
            )
            if "Contents" not in response:
                return []
            items = []
            for obj in response["Contents"]:
                items.append(s3_data_from_path(obj["Key"]))
            return items
        except ClientError as e:
            logger.error("List failed", extra={"prefix": prefix, "error": str(e)})
            raise RuntimeError(f"S3 error listing objects: {e}")
