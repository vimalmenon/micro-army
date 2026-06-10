"""Tests for atlas FastAPI routes — all AWS calls mocked."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_s3_client():
    """Reset singleton between tests."""
    from s3_client import S3Client
    S3Client._instance = None


@pytest.fixture
def client():
    """TestClient with mocked S3Client singleton and env config."""
    # Mock the settings object that s3_client and main import
    mock_settings = MagicMock()
    mock_settings.aws_bucket = "test-bucket"
    mock_settings.aws_region = "us-east-1"
    mock_settings.aws_access_key_id = ""
    mock_settings.aws_secret_access_key = ""

    mock_s3 = MagicMock()
    mock_s3.upload_bytes.return_value = True
    mock_s3.get_bytes.return_value = b"testdata"
    mock_s3.delete.return_value = True
    mock_s3.list_items.return_value = [
        {"key": "images/logo.png", "name": "logo.png", "content_type": "image/png"},
    ]

    import s3_client as s3_mod
    with patch.object(s3_mod, "settings", mock_settings):
        with patch.object(s3_mod, "S3Client", return_value=mock_s3):
            import main as main_mod
            with patch.object(main_mod, "settings", mock_settings):
                with patch.object(main_mod, "s3", mock_s3):
                    app = main_mod.app
                    with TestClient(app) as tc:
                        yield tc


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "atlas"


class TestUpload:
    def test_upload_bytes(self, client):
        resp = client.post("/upload", json={
            "name": "notes.txt",
            "data": "aGVsbG8=",  # base64 of "hello"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["s3_key"] == "data/notes.txt"

    def test_upload_with_key(self, client):
        resp = client.post("/upload", json={
            "name": "photo.png",
            "key": "branding",
            "data": "aW1hZ2U=",
        })
        assert resp.status_code == 200
        assert resp.json()["s3_key"] == "images/branding/photo.png"

    def test_upload_rejects_missing_name(self, client):
        resp = client.post("/upload", json={"data": "dGVzdA=="})
        assert resp.status_code == 422

    def test_upload_rejects_invalid_extension(self, client):
        resp = client.post("/upload", json={
            "name": "file.xyz",
            "data": "dGVzdA==",
        })
        assert resp.status_code == 400
        assert "unsupported" in resp.json()["detail"].lower()


class TestDownload:
    def test_get_bytes(self, client):
        resp = client.get("/bytes?name=notes.txt")
        assert resp.status_code == 200
        assert resp.content == b"testdata"

    def test_get_bytes_with_key(self, client):
        resp = client.get("/bytes?name=photo.png&key=branding")
        assert resp.status_code == 200

    def test_get_bytes_not_found(self, client):
        import main as main_mod
        main_mod.s3.get_bytes.side_effect = RuntimeError("S3 error")
        resp = client.get("/bytes?name=missing.txt")
        assert resp.status_code == 404


class TestDelete:
    def test_delete(self, client):
        resp = client.delete("/delete", params={"name": "notes.txt"})
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_not_found(self, client):
        import main as main_mod
        main_mod.s3.delete.return_value = True
        resp = client.delete("/delete", params={"name": "missing.txt"})
        assert resp.status_code == 200


class TestList:
    def test_list_items(self, client):
        resp = client.get("/list?prefix=images/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["count"] == 1

    def test_list_no_prefix(self, client):
        resp = client.get("/list")
        assert resp.status_code == 200
