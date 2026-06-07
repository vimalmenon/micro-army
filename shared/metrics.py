"""Prometheus metrics middleware for FastAPI microservices.

Provides:
- Standard HTTP request metrics (count, duration, in-progress)
- /metrics endpoint for Prometheus scraping
- Middleware that auto-instruments every request
"""

import time

from prometheus_client import Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

REQUESTS_IN_PROGRESS = Histogram(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method"],
)

EXCEPTIONS_TOTAL = Counter(
    "http_exceptions_total",
    "Total unhandled HTTP exceptions",
    ["method", "endpoint"],
)


def _route_path(request: Request) -> str:
    """Return the route template path (e.g. '/{table}/item/{app}') for
    cardinality-safe metrics, falling back to the real path."""
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return route.path
    return request.url.path


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that records Prometheus metrics for every request."""

    async def dispatch(
        self,
        request: Request,
        call_next: ...,
    ) -> Response:
        method = request.method
        endpoint = _route_path(request)
        start = time.monotonic()

        REQUESTS_IN_PROGRESS.labels(method=method).observe(1)

        try:
            response = await call_next(request)
            duration = time.monotonic() - start

            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint, status=response.status_code
            ).inc()
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

            return response
        except Exception:
            EXCEPTIONS_TOTAL.labels(method=method, endpoint=endpoint).inc()
            raise


async def metrics_handler(request: Request) -> Response:
    """FastAPI route handler for /metrics."""
    return Response(
        content=generate_latest(), media_type="text/plain; charset=utf-8"
    )
