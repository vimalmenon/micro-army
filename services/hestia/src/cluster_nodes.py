"""Kubernetes node info queried via in-cluster API."""

import json
import logging
import os
import ssl
import urllib.request

logger = logging.getLogger(__name__)

# In-cluster k8s API paths
TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
API_URL = "https://kubernetes.default.svc/api/v1/nodes"


def _build_headers() -> dict[str, str] | None:
    """Read the service account token if it exists."""
    if not os.path.isfile(TOKEN_PATH):
        return None
    token = open(TOKEN_PATH).read().strip()
    return {"Authorization": f"Bearer {token}"}


def _build_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if os.path.isfile(CA_PATH):
        ctx.load_verify_cafile(CA_PATH)
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _format_bytes(kib_str: str) -> str:
    """Convert Ki suffix to human-readable GiB."""
    try:
        if kib_str.endswith("Ki"):
            kib = int(kib_str[:-2])
        else:
            kib = int(kib_str) // 1024
        gib = kib / 1024 / 1024
        return f"{gib:.1f} GiB" if gib < 10 else f"{round(gib)} GiB"
    except (ValueError, TypeError):
        return kib_str


def _format_cpu(cpu_str: str) -> str:
    """Normalise CPU — '4' → '4 cores'."""
    try:
        c = int(cpu_str)
        return f"{c} cores"
    except (ValueError, TypeError):
        return cpu_str


def _format_storage(kib_str: str) -> str:
    """Format ephemeral-storage to human-readable."""
    try:
        if kib_str.endswith("Ki"):
            kib = int(kib_str[:-2])
        else:
            kib = int(kib_str) // 1024
        gib = kib / 1024 / 1024
        return f"{gib:.1f} GiB" if gib < 10 else f"{round(gib)} GiB"
    except (ValueError, TypeError):
        return kib_str


async def get_cluster_nodes() -> list[dict]:
    """Fetch and return a simplified list of cluster nodes.

    Returns a list of dicts with name, cpu, memory, storage, status.
    Falls back gracefully if k8s API is unreachable or forbidden.
    """
    headers = _build_headers()
    if not headers:
        logger.warning("No service account token found — not running in-cluster")
        return _fallback()

    ctx = _build_ssl_context()
    req = urllib.request.Request(API_URL, headers=headers)

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        logger.error("k8s API returned %s: %s", e.code, e.reason)
        return _fallback()
    except urllib.error.URLError as e:
        logger.error("k8s API unreachable: %s", e.reason)
        return _fallback()
    except Exception:
        logger.exception("Unexpected error fetching nodes")
        return _fallback()

    nodes = []
    for n in data.get("items", []):
        status = n.get("status", {})
        caps = status.get("capacity", {})
        conds = status.get("conditions", [])
        ready = any(
            c.get("type") == "Ready" and c.get("status") == "True"
            for c in conds
        )

        nodes.append({
            "name": n["metadata"]["name"],
            "cpu": _format_cpu(caps.get("cpu", "?")),
            "memory": _format_bytes(caps.get("memory", "?")),
            "storage": _format_storage(caps.get("ephemeral-storage", "?")),
            "pods": caps.get("pods", "?"),
            "ready": ready,
        })

    return nodes


def _fallback() -> list[dict]:
    """Return a minimal fallback when k8s API is unavailable."""
    return [
        {
            "name": "homelab01",
            "cpu": "4 cores",
            "memory": "~16 GiB",
            "storage": "~60 GiB",
            "pods": "110",
            "ready": True,
        },
        {
            "name": "homelab02",
            "cpu": "4 cores",
            "memory": "~8 GiB",
            "storage": "~60 GiB",
            "pods": "110",
            "ready": True,
        },
        {
            "name": "homelab03",
            "cpu": "4 cores",
            "memory": "~16 GiB",
            "storage": "~120 GiB",
            "pods": "110",
            "ready": True,
        },
    ]
