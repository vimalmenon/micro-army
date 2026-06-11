import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    dynamo_svc_url: str = field(
        default_factory=lambda: os.getenv(
            "DYNAMO_SVC_URL", "http://clio.microservices.svc.cluster.local:8000"
        )
    )
    service_port: int = field(default_factory=lambda: int(os.getenv("SERVICE_PORT", "8000")))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "deepseek/deepseek-chat"))
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    search_api_key: str = field(default_factory=lambda: os.getenv("SEARCH_API_KEY", ""))
    search_engine_id: str = field(default_factory=lambda: os.getenv("SEARCH_ENGINE_ID", ""))


settings = Settings()
