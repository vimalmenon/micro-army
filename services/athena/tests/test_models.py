"""Tests for Pydantic models used in wiki-svc."""
import json

import pydantic
import pytest

from models import CreateArticleRequest, HealthResponse, UpdateArticleRequest


class TestHealthResponse:
    def test_defaults(self):
        resp = HealthResponse()
        assert resp.status == "ok"
        assert resp.service == "wiki-svc"

    def test_serialization(self):
        data = json.loads(HealthResponse().model_dump_json())
        assert data == {"status": "ok", "service": "wiki-svc"}


class TestCreateArticleRequest:
    def test_valid(self):
        req = CreateArticleRequest(
            id="restart-n8n",
            title="Restart n8n",
            content="Steps to restart",
            tags=["homelab", "k8s"],
        )
        assert req.id == "restart-n8n"
        assert req.title == "Restart n8n"
        assert req.tags == ["homelab", "k8s"]

    def test_slug_validation_valid(self):
        valid_slugs = ["hello-world", "test123", "a", "n8n-restart-deploy"]
        for slug in valid_slugs:
            req = CreateArticleRequest(id=slug, title="Test")
            assert req.id == slug

    def test_slug_validation_invalid(self):
        invalid_slugs = [
            "-leading-hyphen",
            "trailing-hyphen-",
            "CAPS",
            "has spaces",
            "special!chars",
            "a" * 200,  # exceeds 128
        ]
        for slug in invalid_slugs:
            with pytest.raises(pydantic.ValidationError):
                CreateArticleRequest(id=slug, title="Test")

    def test_tags_normalised(self):
        req = CreateArticleRequest(
            id="test", title="Test", tags=["  Homelab ", "K8S ", "  N8n  "]
        )
        assert req.tags == ["homelab", "k8s", "n8n"]

    def test_missing_title(self):
        with pytest.raises(pydantic.ValidationError):
            CreateArticleRequest(id="test")

    def test_empty_id(self):
        with pytest.raises(pydantic.ValidationError):
            CreateArticleRequest(id="", title="Test")


class TestUpdateArticleRequest:
    def test_partial_update_title_only(self):
        req = UpdateArticleRequest(title="New title")
        assert req.title == "New title"
        assert req.content is None
        assert req.tags is None

    def test_partial_update_all_fields(self):
        req = UpdateArticleRequest(
            title="New", content="Updated body", tags=["homelab"]
        )
        assert req.title == "New"
        assert req.content == "Updated body"
        assert req.tags == ["homelab"]
