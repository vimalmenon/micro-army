"""Tests for tunnel_sync — mock kubectl + Cloudflare API to test reconciliation."""

import json
import subprocess
from unittest.mock import ANY, MagicMock, patch

import pytest
import requests

import os

from src.tunnel_sync import (
    get_k3s_ingress_hostnames,
    get_tunnel_config,
    load_config,
    reconcile,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
SAMPLE_K3S_INGRESSES = {
    "apiVersion": "v1",
    "items": [
        {
            "spec": {
                "rules": [
                    {"host": "argocd.completeautomate.com"},
                    {"host": "auth.completeautomate.com"},
                ],
            },
        },
        {
            "spec": {
                "rules": [
                    {"host": "grafana.completeautomate.com"},
                    {"host": "n8n.completeautomate.com"},
                ],
            },
        },
        {
            "spec": {
                "rules": [
                    {"host": "homepage.completeautomate.com"},
                    {"host": "messages.completeautomate.com"},
                ],
            },
        },
        # ingress with non-matching hostname (should be excluded)
        {
            "spec": {
                "rules": [
                    {"host": "pihole.homelab.local"},
                ],
            },
        },
    ],
}

SAMPLE_TUNNEL_CONFIG = {
    "tunnel_id": "CF_TUNNEL_ID_PLACEHOLDER",
    "version": 18,
    "config": {
        "ingress": [
            {"service": "http://192.168.128.200", "hostname": "argocd.completeautomate.com", "originRequest": {}},
            {"service": "http://192.168.128.200", "hostname": "auth.completeautomate.com", "originRequest": {}},
            {"service": "http://192.168.128.200", "hostname": "grafana.completeautomate.com", "originRequest": {}},
            {"service": "http://192.168.128.200", "hostname": "n8n.completeautomate.com", "originRequest": {}},
            {"service": "http_status:404", "originRequest": {}},
        ],
        "warp-routing": {"enabled": False},
    },
    "source": "cloudflare",
}


@pytest.fixture
def cfg():
    return {
        "api_token": "test-token",
        "account_id": "test-account",
        "tunnel_id": "test-tunnel",
        "backend": "http://192.168.128.200",
        "host_suffix": ".completeautomate.com",
    }


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------
@patch.dict(os.environ, clear=True)
def test_load_config_requires_token():
    """Missing CLOUDFLARE_API_TOKEN should raise KeyError."""
    from src.tunnel_sync import load_config as lc

    with pytest.raises(KeyError):
        lc()


@patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "my-token"}, clear=True)
def test_load_config_minimal():
    """Should use defaults for optional env vars."""
    from src.tunnel_sync import load_config as lc

    result = lc()
    assert result["api_token"] == "my-token"
    assert result["account_id"] == "CF_ACCOUNT_ID_PLACEHOLDER"
    assert result["tunnel_id"] == "CF_TUNNEL_ID_PLACEHOLDER"
    assert result["backend"] == "http://192.168.128.200"


# ---------------------------------------------------------------------------
# get_k3s_ingress_hostnames
# ---------------------------------------------------------------------------
@patch("src.tunnel_sync.subprocess.run")
def test_get_k3s_ingress_hostnames(mock_run):
    """Should return only hostnames matching the configured suffix."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(SAMPLE_K3S_INGRESSES),
    )
    hostnames = get_k3s_ingress_hostnames(".completeautomate.com")
    assert hostnames == {
        "argocd.completeautomate.com",
        "auth.completeautomate.com",
        "grafana.completeautomate.com",
        "n8n.completeautomate.com",
        "homepage.completeautomate.com",
        "messages.completeautomate.com",
    }
    # homelab.local should NOT be included
    assert "pihole.homelab.local" not in hostnames


@patch("src.tunnel_sync.subprocess.run")
def test_get_k3s_ingress_hostnames_kubectl_error(mock_run):
    """kubectl failure should raise."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="connection refused",
    )
    with pytest.raises(RuntimeError, match="kubectl failed"):
        get_k3s_ingress_hostnames()


# ---------------------------------------------------------------------------
# get_tunnel_config
# ---------------------------------------------------------------------------
@patch("src.tunnel_sync.requests.get")
def test_get_tunnel_config_success(mock_get, cfg):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"success": True, "result": SAMPLE_TUNNEL_CONFIG},
    )
    result = get_tunnel_config(cfg)
    assert result["version"] == 18
    assert len(result["config"]["ingress"]) == 5

    # Verify correct URL was called
    expected_url = (
        "https://api.cloudflare.com/client/v4/accounts/test-account"
        "/cfd_tunnel/test-tunnel/configurations"
    )
    mock_get.assert_called_once_with(expected_url, headers=ANY, timeout=30)


@patch("src.tunnel_sync.requests.get")
def test_get_tunnel_config_api_error(mock_get, cfg):
    mock_get.side_effect = requests.exceptions.HTTPError("403 Forbidden")
    with pytest.raises(requests.exceptions.HTTPError):
        get_tunnel_config(cfg)


# ---------------------------------------------------------------------------
# reconcile
# ---------------------------------------------------------------------------
@patch("src.tunnel_sync.put_tunnel_config")
@patch("src.tunnel_sync.get_tunnel_config")
@patch("src.tunnel_sync.get_k3s_ingress_hostnames")
def test_reconcile_adds_missing(mock_k3s, mock_tunnel, mock_put, cfg):
    """Should detect missing hostnames and add them before the catch-all."""
    mock_k3s.return_value = {
        "argocd.completeautomate.com",
        "auth.completeautomate.com",
        "grafana.completeautomate.com",
        "n8n.completeautomate.com",
        "homepage.completeautomate.com",
        "messages.completeautomate.com",
    }
    mock_tunnel.return_value = SAMPLE_TUNNEL_CONFIG
    mock_put.return_value = {"version": 19}

    result = reconcile(cfg, verbose=True)

    assert result["missing"] == ["homepage.completeautomate.com", "messages.completeautomate.com"]
    assert result["added"] == ["homepage.completeautomate.com", "messages.completeautomate.com"]
    assert result["version"] == 19

    # Verify put was called with correct ingress (missing added before catch-all)
    put_ingress = mock_put.call_args[0][1]
    hostnames = [r.get("hostname") for r in put_ingress]
    # Catch-all should be last
    assert hostnames[-1] is None
    # New hostnames should be in the list
    assert "homepage.completeautomate.com" in hostnames
    assert "messages.completeautomate.com" in hostnames


@patch("src.tunnel_sync.put_tunnel_config")
@patch("src.tunnel_sync.get_tunnel_config")
@patch("src.tunnel_sync.get_k3s_ingress_hostnames")
def test_reconcile_no_changes(mock_k3s, mock_tunnel, mock_put, cfg):
    """When tunnel already has all k3s hostnames, nothing should change."""
    mock_k3s.return_value = {"argocd.completeautomate.com", "auth.completeautomate.com"}
    mock_tunnel.return_value = SAMPLE_TUNNEL_CONFIG
    # Only the first two plus catch-all match
    result = reconcile(cfg)
    assert result["missing"] == []
    assert result["added"] == []
    mock_put.assert_not_called()


@patch("src.tunnel_sync.put_tunnel_config")
@patch("src.tunnel_sync.get_tunnel_config")
@patch("src.tunnel_sync.get_k3s_ingress_hostnames")
def test_reconcile_dry_run(mock_k3s, mock_tunnel, mock_put, cfg):
    """Dry-run should detect missing but NOT push changes."""
    mock_k3s.return_value = {
        "argocd.completeautomate.com",
        "homepage.completeautomate.com",
    }
    mock_tunnel.return_value = SAMPLE_TUNNEL_CONFIG
    result = reconcile(cfg, dry_run=True)
    assert result["missing"] == ["homepage.completeautomate.com"]
    assert result["added"] == []  # nothing added on dry run
    mock_put.assert_not_called()
