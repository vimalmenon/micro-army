"""youtube-svc configuration — YouTube Data API + cluster service URLs."""

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

    # YouTube OAuth 2.0
    google_client_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", ""))
    google_refresh_token: str = field(default_factory=lambda: os.getenv("GOOGLE_REFRESH_TOKEN", ""))

    # YouTube channel to upload to
    youtube_channel_id: str = field(default_factory=lambda: os.getenv("YOUTUBE_CHANNEL_ID", ""))

    # Category ID defaults to "22" (Science & Technology)
    default_category_id: str = field(default_factory=lambda: os.getenv("DEFAULT_CATEGORY_ID", "22"))

    # Max video file size: 100 GB (YouTube limit for verified)
    max_video_size: int = field(default_factory=lambda: int(os.getenv("MAX_VIDEO_SIZE", "107_374_182_400")))


settings = Settings()
