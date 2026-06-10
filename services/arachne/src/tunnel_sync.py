"""tunnel-sync: Reconcile k3s ingresses with Cloudflare tunnel ingress rules.

Detects k3s Ingress hostnames missing from the Cloudflare tunnel config
and adds them automatically. Designed to run as a cron job or container.

Usage:
    python src/tunnel_sync.py                  # uses env vars
    python src/tunnel_sync.py --dry-run         # preview only, no changes
    python src/tunnel_sync.py --verbose         # detailed logging
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from typing import Any

import requests

log = logging.getLogger("tunnel-sync")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """Load config from environment variables (all required)."""
    required = {
        "api_token": "CLOUDFLARE_API_TOKEN",
        "account_id": "CF_ACCOUNT_ID",
        "tunnel_id": "CF_TUNNEL_ID",
    }
    cfg = {}
    for key, env_var in required.items():
        val = os.environ.get(env_var)
        if not val:
            log.error("Missing required env var: %s", env_var)
            raise SystemExit(f"ERROR: {env_var} is required but not set")
        cfg[key] = val

    cfg["backend"] = os.environ.get("TUNNEL_BACKEND", "http://192.168.128.200")
    cfg["host_suffix"] = os.environ.get("HOST_SUFFIX", ".completeautomate.com")
    return cfg


# ---------------------------------------------------------------------------
# Cloudflare API helpers
# ---------------------------------------------------------------------------
def _cf_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_tunnel_config(cfg: dict) -> dict:
    """Fetch the current tunnel ingress config from Cloudflare."""
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{cfg['account_id']}"
        f"/cfd_tunnel/{cfg['tunnel_id']}/configurations"
    )
    resp = requests.get(url, headers=_cf_headers(cfg["api_token"]), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Cloudflare API error: {data.get('errors', 'unknown')}")
    return data["result"]


def put_tunnel_config(cfg: dict, ingress: list[dict], version: int) -> dict:
    """Push updated tunnel ingress config to Cloudflare."""
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{cfg['account_id']}"
        f"/cfd_tunnel/{cfg['tunnel_id']}/configurations"
    )
    body = {"config": {"ingress": ingress, "warp-routing": {"enabled": False}}}
    resp = requests.put(
        url,
        headers=_cf_headers(cfg["api_token"]),
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Cloudflare API error: {data.get('errors', 'unknown')}")
    return data["result"]


# ---------------------------------------------------------------------------
# k3s ingress discovery
# ---------------------------------------------------------------------------
def get_k3s_ingress_hostnames(suffix: str) -> set[str]:
    """Run kubectl and return all Ingress hostnames matching the suffix."""
    result = subprocess.run(
        ["kubectl", "get", "ingress", "-A", "-o", "json"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"kubectl failed: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    hostnames: set[str] = set()
    for item in data.get("items", []):
        for rule in item.get("spec", {}).get("rules", []):
            host = rule.get("host", "")
            if host.endswith(suffix):
                hostnames.add(host)
    return hostnames


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------
def reconcile(
    cfg: dict, *, dry_run: bool = False, verbose: bool = False
) -> dict[str, Any]:
    """Compare k3s ingresses vs tunnel config, add missing hostnames.

    Returns a summary dict with keys:
        - tunnel_hostnames: hostnames currently in the tunnel
        - k3s_hostnames: all matching hostnames from k3s
        - missing: hostnames in k3s but not in tunnel
        - added: hostnames we actually added (empty on dry-run)
        - version: new tunnel config version (or None)
    """
    # 1. Get tunnel config
    tunnel = get_tunnel_config(cfg)
    current_ingress: list[dict] = tunnel["config"]["ingress"]
    current_version: int = tunnel["version"]
    tunnel_hostnames = {
        r.get("hostname", "")
        for r in current_ingress
        if r.get("hostname")
    }

    # 2. Get k3s ingresses
    k3s_hostnames = get_k3s_ingress_hostnames(cfg["host_suffix"])

    # 3. Find missing
    missing = sorted(k3s_hostnames - tunnel_hostnames)

    result: dict[str, Any] = {
        "tunnel_hostnames": sorted(tunnel_hostnames),
        "k3s_hostnames": sorted(k3s_hostnames),
        "missing": missing,
        "added": [],
        "version": current_version,
    }

    if not missing:
        log.info("All %d tunnel hostnames are up-to-date.", len(tunnel_hostnames))
        return result

    log.info(
        "Found %d hostname(s) in k3s but missing from tunnel: %s",
        len(missing),
        ", ".join(missing),
    )

    if dry_run:
        log.info("DRY-RUN: would add %d hostname(s).", len(missing))
        return result

    # 4. Add missing hostnames before the catch-all
    new_rules = []
    for hostname in missing:
        new_rules.append({
            "service": cfg["backend"],
            "hostname": hostname,
            "originRequest": {},
        })
        if verbose:
            log.info("  Adding: %s -> %s", hostname, cfg["backend"])

    # Insert before catch-all (last entry, which has no hostname)
    updated_ingress = current_ingress[:-1] + new_rules + [current_ingress[-1]]

    # 5. Push updated config
    updated = put_tunnel_config(cfg, updated_ingress, current_version)
    new_version = updated["version"]

    result["added"] = missing
    result["version"] = new_version
    log.info(
        "Tunnel config updated to version %d — added %d hostname(s): %s",
        new_version,
        len(missing),
        ", ".join(missing),
    )
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync k3s Ingress hostnames into Cloudflare tunnel ingress config.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Detailed logging.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON (for machine parsing).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.verbose)

    try:
        cfg = load_config()
    except KeyError as exc:
        log.error("Missing required environment variable: %s", exc)
        print(f"ERROR: Missing required environment variable: {exc}", file=sys.stderr)
        return 1

    try:
        result = reconcile(cfg, dry_run=args.dry_run, verbose=args.verbose)
    except Exception as exc:
        log.error("Reconciliation failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["missing"]:
            print(f"Added {len(result['added'])} hostname(s) — tunnel config v{result['version']}")
            for h in result["added"]:
                print(f"  + {h}")
        else:
            print("All up-to-date — no changes needed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
