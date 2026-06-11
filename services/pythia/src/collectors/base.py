"""Base collector interface and registry."""
from __future__ import annotations

from abc import ABC, abstractmethod

from models import RawItem


class BaseCollector(ABC):
    """Interface for a data source collector."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source name (e.g. 'reddit', 'hackernews')."""
        ...

    @abstractmethod
    async def collect(self) -> list[RawItem]:
        """Fetch new items from the source. Returns list of RawItems."""
        ...


_collectors: dict[str, type[BaseCollector]] = {}


def register_collector(cls: type[BaseCollector]) -> type[BaseCollector]:
    """Register a collector class by its source_name."""
    instance = cls()
    _collectors[instance.source_name] = cls
    return cls


def get_collector(name: str) -> BaseCollector:
    """Get a collector instance by source name."""
    cls = _collectors.get(name)
    if not cls:
        raise ValueError(f"Unknown collector: {name}. Available: {list(_collectors.keys())}")
    return cls()


def get_all_collectors() -> list[BaseCollector]:
    """Get instances of all registered collectors."""
    return [cls() for cls in _collectors.values()]
