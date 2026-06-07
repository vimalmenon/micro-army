"""Structured JSON logging for micro-army services.

Replaces basic Python logging with JSON-formatted output suitable for
Loki / Promtail ingestion. Each log line is a single JSON object.

Usage:
    from shared.logging import setup_logging
    setup_logging("dynamo-svc")
    logger = logging.getLogger(__name__)
    logger.info("Server started", extra={"port": 8000})
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        # Basic fields
        fields: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Exception info
        if record.exc_info and record.exc_info[0]:
            fields["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        # Extra fields from the caller (e.g. extra={"request_id": "abc"})
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "levelname", "levelno", "lineno",
                "message", "module", "msecs", "msg", "name", "pathname",
                "process", "processName", "relativeCreated", "stack_info",
                "thread", "threadName", "service_name",
            ):
                fields[key] = value

        return json.dumps(fields, default=str)


def setup_logging(service_name: str, level: int = logging.INFO) -> None:
    """Configure the root logger with JSON output to stdout.

    Args:
        service_name: Name of the service (appears in every log line).
        level: Logging level (default: INFO).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(service_name))

    root = logging.getLogger()
    # Remove default handlers to avoid duplicate output
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy third-party loggers
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
