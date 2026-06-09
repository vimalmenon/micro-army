import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    dynamo_svc_url: str = field(
        default_factory=lambda: os.getenv(
            "DYNAMO_SVC_URL", "http://dynamo-svc.microservices.svc.cluster.local:8000"
        )
    )
    s3_svc_url: str = field(
        default_factory=lambda: os.getenv(
            "S3_SVC_URL", "http://s3-svc.microservices.svc.cluster.local:8000"
        )
    )
    service_port: int = field(default_factory=lambda: int(os.getenv("SERVICE_PORT", "8000")))
    max_file_size: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE", "10_485_760")))  # 10MB
    allowed_extensions: list[str] = field(
        default_factory=lambda: os.getenv("ALLOWED_EXTENSIONS", "png,jpg,jpeg,gif,pdf,txt,md,svg,csv,json").split(",")
    )


settings = Settings()
