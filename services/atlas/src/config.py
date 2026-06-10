import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    aws_access_key_id: str = field(default_factory=lambda: os.getenv("AWS_ACCESS_KEY_ID", ""))
    aws_secret_access_key: str = field(default_factory=lambda: os.getenv("AWS_SECRET_ACCESS_KEY", ""))
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))
    aws_bucket: str = field(default_factory=lambda: os.getenv("AWS_S3_BUCKET", ""))
    service_port: int = field(default_factory=lambda: int(os.getenv("SERVICE_PORT", "8000")))


settings = Settings()
