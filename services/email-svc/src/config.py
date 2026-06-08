import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    dynamo_svc_url: str = field(
        default_factory=lambda: os.getenv(
            "DYNAMO_SVC_URL", "http://dynamo-svc.microservices.svc.cluster.local:8000"
        )
    )
    service_port: int = field(default_factory=lambda: int(os.getenv("SERVICE_PORT", "8000")))

    # SMTP settings
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.zoho.com"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "465")))

    # SMTP credentials (from k8s secret)
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", "hello@completeautomate.com"))
    smtp_from_name: str = field(default_factory=lambda: os.getenv("SMTP_FROM_NAME", "Complete Automate"))

    # Use SSL (465) vs STARTTLS (587)
    smtp_use_ssl: bool = field(default_factory=lambda: os.getenv("SMTP_USE_SSL", "true").lower() == "true")


settings = Settings()
