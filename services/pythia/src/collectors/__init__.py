"""Collectors package — auto-imports all collector modules to trigger registration."""

from __future__ import annotations

# Import all collector modules to trigger @register_collector decorators
from collectors import (
    reddit,
    hackernews,
    google_news,
    indeed,
    crunchbase,
    producthunt,
)

# Re-export base registry helpers for convenience
from collectors.base import BaseCollector, register_collector, get_collector, get_all_collectors

__all__ = [
    "BaseCollector",
    "register_collector",
    "get_collector",
    "get_all_collectors",
    "reddit",
    "hackernews",
    "google_news",
    "indeed",
    "crunchbase",
    "producthunt",
]
