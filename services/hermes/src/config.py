import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    service_port: int = field(default_factory=lambda: int(os.getenv("SERVICE_PORT", "8000")))

    # Telegram Bot API base URL
    telegram_api_base: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")
    )

    # Credentials (from k8s secret, managed by Infisical)
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))


settings = Settings()
