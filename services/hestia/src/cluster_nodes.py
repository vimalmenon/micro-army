"""Kubernetes node info queried via in-cluster API — capacity + usage from metrics-server."""

import json
import logging
import os
import ssl
import urllib.request

logger = logging.getLogger(__name__)

# In-cluster k8s API paths
TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
NODE_API = "https://kubernetes.default.svc/api/v1/nodes"
METRICS_API = "https://kubernetes.default.svc/apis/metrics.k8s.io/v1beta1/nodes"


# ─── k8s quantity parsing helpers ────────────────────────

def parse_cpu_millicores(raw: str) -> int:
    """Parse k8s CPU quantity to millicores. '2' → 2000, '250m' → 250."""
    raw = raw.strip()
    if raw.endswith("m"):
        return int(raw[:-1])
    return int(raw) * 1000


def parse_memory_bytes(raw: str) -> int:
    """Parse k8s memory quantity to bytes. '16Gi', '5319Mi', '16000000Ki'."""
    raw = raw.strip()
    suffixes = {
        "Ei": 1024 ** 6,
        "Pi": 1024 ** 5,
        "Ti": 1024 ** 4,
        "Gi": 1024 ** 3,
        "Mi": 1024 ** 2,
        "Ki": 1024,
    }
    for suffix, multiplier in suffixes.items():
        if raw.endswith(suffix):
            return int(float(raw[: -len(suffix)]) * multiplier)
    # Assume plain bytes
    return int(raw)


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable GiB."""
    gib = bytes_val / (1024 ** 3)
    return f"{gib:.1f} GiB" if gib < 10 else f"{round(gib)} GiB"


def format_millicores(millicores: int) -> str:
    """Format millicores to human (e.g. 270 → '270m', 4000 → '4 cores')."""
    if millicores >= 1000:
        return f"{millicores // 1000} cores"
    return f"{millicores}m"


# ─── API plumbing ────────────────────────────────────────


def _build_headers() -> dict[str, str] | None:
    """Read the service account token if it exists."""
    if not os.path.isfile(TOKEN_PATH):
        return None
    token = open(TOKEN_PATH).read().strip()
    return {"Authorization": f"Bearer {token}"}


def _build_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if os.path.isfile(CA_PATH):
        # Python 3.13 API uses load_verify_locations
        ctx.load_verify_locations(CA_PATH)
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _fetch_json(url: str, headers: dict) -> dict | None:
    """Fetch a JSON response from the k8s API. Returns None on failure."""
    ctx = _build_ssl_context()
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        logger.warning("k8s API %s returned %s: %s", url, e.code, e.reason)
        return None
    except urllib.error.URLError as e:
        logger.warning("k8s API %s unreachable: %s", url, e.reason)
        return None
    except Exception:
        logger.exception("Unexpected error fetching %s", url)
        return None


# ─── Main ────────────────────────────────────────────────


async def get_cluster_nodes() -> list[dict]:
    """Fetch cluster nodes with capacity + usage data.

    Returns a list of dicts with:
      - name, ready
      - cpu (human readable total), cpu_used_m (millicores), cpu_total_m (millicores)
      - memory (human total), memory_used (human), memory_total_bytes, memory_used_bytes
      - cpu_percent, memory_percent
      - storage (human total)
    Falls back gracefully if k8s API is unreachable.
    """
    headers = _build_headers()
    if not headers:
        logger.warning("No service account token found — not running in-cluster")
        return _fallback()

    # Fetch both endpoints in parallel
    import asyncio
    loop = asyncio.get_event_loop()

    def _fetch_all():
        nodes_data = _fetch_json(NODE_API, headers)
        metrics_data = _fetch_json(METRICS_API, headers)
        return nodes_data, metrics_data

    nodes_data, metrics_data = await loop.run_in_executor(None, _fetch_all)

    if not nodes_data:
        logger.error("Failed to fetch node capacity data")
        return _fallback()

    # Index metrics by node name
    metrics_by_name: dict[str, dict] = {}
    if metrics_data:
        for m in metrics_data.get("items", []):
            metrics_by_name[m["metadata"]["name"]] = m.get("usage", {})

    nodes = []
    for n in nodes_data.get("items", []):
        name = n["metadata"]["name"]
        status = n.get("status", {})
        caps = status.get("capacity", {})
        conds = status.get("conditions", [])
        ready = any(
            c.get("type") == "Ready" and c.get("status") == "True"
            for c in conds
        )

        cpu_raw = caps.get("cpu", "0")
        mem_raw = caps.get("memory", "0")
        storage_raw = caps.get("ephemeral-storage", "0")

        cpu_total_m = parse_cpu_millicores(cpu_raw)
        mem_total_bytes = parse_memory_bytes(mem_raw)

        usage = metrics_by_name.get(name, {})
        cpu_used_m = parse_cpu_millicores(usage.get("cpu", "0m")) if usage else 0
        mem_used_bytes = parse_memory_bytes(usage.get("memory", "0")) if usage else 0

        cpu_pct = round(cpu_used_m / cpu_total_m * 100) if cpu_total_m > 0 else 0
        mem_pct = round(mem_used_bytes / mem_total_bytes * 100) if mem_total_bytes > 0 else 0

        nodes.append({
            "name": name,
            "ready": ready,
            # Total capacity (human + raw)
            "cpu": format_millicores(cpu_total_m),
            "cpu_total_m": cpu_total_m,
            "cpu_used_m": cpu_used_m,
            "cpu_percent": cpu_pct,
            "memory": format_bytes(mem_total_bytes),
            "memory_total_bytes": mem_total_bytes,
            "memory_used_bytes": mem_used_bytes,
            "memory_used": format_bytes(mem_used_bytes),
            "memory_percent": mem_pct,
            "storage": format_bytes(parse_memory_bytes(storage_raw)),
        })

    return nodes


# ─── Fallback ────────────────────────────────────────────


def _fallback() -> list[dict]:
    """Return static fallback when k8s API is unavailable."""
    return [
        {
            "name": "homelab01",
            "ready": True,
            "cpu": "4 cores",
            "cpu_total_m": 4000,
            "cpu_used_m": 270,
            "cpu_percent": 7,
            "memory": "16 GiB",
            "memory_total_bytes": 17179869184,
            "memory_used_bytes": 5577375744,
            "memory_used": "5.2 GiB",
            "memory_percent": 32,
            "storage": "58 GiB",
        },
        {
            "name": "homelab02",
            "ready": True,
            "cpu": "4 cores",
            "cpu_total_m": 4000,
            "cpu_used_m": 92,
            "cpu_percent": 2,
            "memory": "8 GiB",
            "memory_total_bytes": 8589934592,
            "memory_used_bytes": 2411728896,
            "memory_used": "2.2 GiB",
            "memory_percent": 28,
            "storage": "58 GiB",
        },
        {
            "name": "homelab03",
            "ready": True,
            "cpu": "4 cores",
            "cpu_total_m": 4000,
            "cpu_used_m": 402,
            "cpu_percent": 10,
            "memory": "16 GiB",
            "memory_total_bytes": 17179869184,
            "memory_used_bytes": 5343551488,
            "memory_used": "5.0 GiB",
            "memory_percent": 31,
            "storage": "117 GiB",
        },
    ]
