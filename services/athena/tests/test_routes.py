"""Tests for wiki-svc FastAPI routes."""
from fastapi import status


class TestHealth:
    def test_returns_ok(self, client, mock_dynamo_transport):
        resp = client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"status": "ok", "service": "wiki-svc"}


class TestCreateArticle:
    def test_creates_successfully(self, client, mock_dynamo_transport):
        body = {
            "id": "restart-n8n",
            "title": "How to restart n8n",
            "content": "Run `kubectl rollout restart -n n8n deploy/n8n`",
            "tags": ["homelab", "k8s"],
        }
        resp = client.post("/wiki", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["id"] == "restart-n8n"
        assert data["title"] == "How to restart n8n"
        assert "homelab" in data["tags"]
        assert data["app"] == "wiki"
        assert data["author"] == "elara"
        assert data["created_at"] != ""
        assert data["created_at"] == data["updated_at"]

    def test_dynamo_svc_error(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_status = 500

        resp = client.post(
            "/wiki",
            json={"id": "fails", "title": "Fail", "content": "Body", "tags": []},
        )
        assert resp.status_code == 502
        assert "Upstream error" in resp.json()["detail"]

    def test_invalid_slug(self, client, mock_dynamo_transport):
        resp = client.post(
            "/wiki",
            json={"id": "BAD SLUG", "title": "Test", "content": "Body", "tags": []},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_id(self, client, mock_dynamo_transport):
        resp = client.post("/wiki", json={"title": "Missing ID"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListArticles:
    def test_lists_articles(self, client, mock_dynamo_transport):
        # Response shape from POST /vimal/scan
        mock_dynamo_transport.response_data = {
            "items": [
                {"app": "wiki", "id": "a1", "title": "Article 1", "content": "Body", "tags": ["homelab"],
                 "files": [], "author": "elara", "created_at": "", "updated_at": ""},
                {"app": "wiki", "id": "a2", "title": "Article 2", "content": "Body", "tags": ["youtube"],
                 "files": [], "author": "elara", "created_at": "", "updated_at": ""},
            ],
            "count": 2,
        }

        resp = client.get("/wiki")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["articles"]) == 2

    def test_filter_by_tag(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_data = {
            "items": [
                {"app": "wiki", "id": "a1", "title": "A1", "content": "", "tags": ["homelab"],
                 "files": [], "author": "elara", "created_at": "", "updated_at": ""},
                {"app": "wiki", "id": "a2", "title": "A2", "content": "", "tags": ["youtube"],
                 "files": [], "author": "elara", "created_at": "", "updated_at": ""},
            ],
            "count": 2,
        }

        resp = client.get("/wiki?tag=homelab")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["articles"][0]["id"] == "a1"


class TestGetArticle:
    def test_gets_article(self, client, mock_dynamo_transport):
        # Response shape from GET /vimal/item/{app}?id=...
        mock_dynamo_transport.response_data = {
            "item": {
                "app": "wiki", "id": "my-article", "title": "My Title",
                "content": "Body", "tags": ["test"], "files": [],
                "author": "elara", "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        }

        resp = client.get("/wiki/my-article")
        assert resp.status_code == 200
        assert resp.json()["id"] == "my-article"

    def test_not_found(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_status = 404

        resp = client.get("/wiki/unknown")
        assert resp.status_code == 404


class TestUpdateArticle:
    def test_updates_successfully(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_data = {
            "item": {
                "app": "wiki", "id": "test-article", "title": "Old title",
                "content": "Old body", "tags": ["old"], "files": [],
                "author": "elara",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        }

        resp = client.put("/wiki/test-article", json={"title": "New title", "tags": ["new"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New title"
        assert data["tags"] == ["new"]

    def test_not_found(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_status = 404

        resp = client.put("/wiki/unknown", json={"title": "Nope"})
        assert resp.status_code == 404


class TestDeleteArticle:
    def test_deletes_successfully(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_data = {
            "item": {
                "app": "wiki", "id": "del-article", "title": "Delete me",
                "content": "Bye", "tags": [], "files": [],
                "author": "elara",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        }

        resp = client.delete("/wiki/del-article")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_not_found(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_status = 404

        resp = client.delete("/wiki/unknown")
        assert resp.status_code == 404


class TestSearch:
    def test_search_finds_match(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_data = {
            "items": [
                {"app": "wiki", "id": "n8n-restart", "title": "Restart n8n", "content": "kubectl rollout",
                 "tags": ["k8s"], "files": [], "author": "elara", "created_at": "", "updated_at": ""},
                {"app": "wiki", "id": "grafana-setup", "title": "Grafana setup", "content": "Dashboard config",
                 "tags": ["monitoring"], "files": [], "author": "elara", "created_at": "", "updated_at": ""},
            ],
            "count": 2,
        }

        resp = client.get("/wiki/search/n8n")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["articles"][0]["id"] == "n8n-restart"

    def test_search_no_matches(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_data = {
            "items": [
                {"app": "wiki", "id": "test", "title": "Test", "content": "Body",
                 "tags": [], "files": [], "author": "elara", "created_at": "", "updated_at": ""},
            ],
            "count": 1,
        }

        resp = client.get("/wiki/search/zzzzzz")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
