"""Async service health checker — pings each microservice concurrently."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from logging import getLogger
from typing import cast

import httpx

logger = getLogger(__name__)

# ─── Target definitions ──────────────────────────────


@dataclass
class ServiceTarget:
    """A single service to health-check."""

    name: str
    host: str
    port: int
    path: str = "/"
    scheme: str = "http"


# Internal microservices in k8s microservices namespace (port 8000)
_INTERNAL_SERVICES: list[ServiceTarget] = [
    ServiceTarget(name, f"{name}.microservices.svc.cluster.local", 8000, "/health")
    for name in ["atlas", "athena", "clio", "iris", "orpheus", "pythia", "hestia"]
]

# Helios frontend (port 80)
_INTERNAL_SERVICES.append(
    ServiceTarget("helios", "helios.microservices.svc.cluster.local", 80, "/")
)

# Angelos (port 8000)
_INTERNAL_SERVICES.append(
    ServiceTarget("angelos", "angelos.microservices.svc.cluster.local", 8000, "/")
)

ALL_SERVICES: list[ServiceTarget] = _INTERNAL_SERVICES


# ─── Result type ─────────────────────────────────────


@dataclass
class ServiceStatus:
    """Health check result for a single service."""

    name: str
    status: str  # "up" | "down" | "error"
    latency_ms: float | None = None
    error: str | None = None
    url: str = ""
    response_status: int | None = None
    checked_at: str = ""


# ─── Checker ──────────────────────────────────────────


async def _check_one(
    client: httpx.AsyncClient, target: ServiceTarget
) -> ServiceStatus:
    """Ping a single service and return its status."""
    url = f"{target.scheme}://{target.host}:{target.port}{target.path}"
    start = asyncio.get_event_loop().time()
    try:
        resp = await client.get(url, timeout=5.0)
        elapsed = (asyncio.get_event_loop().time() - start) * 1000
        return ServiceStatus(
            name=target.name,
            status="up" if resp.is_success else "down",
            latency_ms=round(elapsed, 1),
            url=url,
            response_status=resp.status_code,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
    except httpx.TimeoutException:
        elapsed = (asyncio.get_event_loop().time() - start) * 1000
        return ServiceStatus(
            name=target.name,
            status="down",
            latency_ms=round(elapsed, 1),
            error="Connection timed out",
            url=url,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        elapsed = (asyncio.get_event_loop().time() - start) * 1000
        return ServiceStatus(
            name=target.name,
            status="error",
            latency_ms=round(elapsed, 1),
            error=str(exc),
            url=url,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )


async def check_all_services() -> list[ServiceStatus]:
    """Check all services concurrently and return results."""
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=5)
    async with httpx.AsyncClient(limits=limits, timeout=10.0) as client:
        results = await asyncio.gather(
            *(_check_one(client, t) for t in ALL_SERVICES), return_exceptions=True
        )

    statuses: list[ServiceStatus] = []
    for i, result_exc in enumerate(results):
        if isinstance(result_exc, Exception):
            statuses.append(
                ServiceStatus(
                    name=ALL_SERVICES[i].name,
                    status="error",
                    error=str(result_exc),
                    checked_at=datetime.now(timezone.utc).isoformat(),
                )
            )
        else:
            statuses.append(cast(ServiceStatus, result_exc))

    return statuses
