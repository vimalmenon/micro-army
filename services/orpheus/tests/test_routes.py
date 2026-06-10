"""Tests for youtube-svc FastAPI routes."""

from fastapi import status

# Default video item used in mock responses
DEFAULT_VIDEO_ITEM = {
    "app": "youtube", "id": "test-video", "title": "Test Video",
    "description": "Test description", "tags": ["test"], "category_id": "22",
    "privacy_status": "private", "status": "draft", "youtube_id": "",
    "s3_key": "", "thumbnail_s3_key": "", "scheduled_at": "",
    "error_message": "", "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


class TestHealth:
    def test_returns_ok(self, client, mock_dynamo_transport):
        resp = client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"status": "ok", "service": "youtube-svc"}


class TestCreateVideo:
    def test_creates_successfully(self, client, mock_dynamo_transport):
        body = {
            "id": "my-first-video",
            "title": "My First Video",
            "description": "A test video description",
            "tags": ["test", "demo"],
        }
        resp = client.post("/videos", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["id"] == "my-first-video"
        assert data["title"] == "My First Video"
        assert data["app"] == "youtube"
        assert data["status"] == "draft"
        assert data["privacy_status"] == "private"
        assert data["created_at"] != ""
        assert data["created_at"] == data["updated_at"]

    def test_dynamo_svc_error(self, client, mock_dynamo_transport):
        mock_dynamo_transport.response_status = 500
        resp = client.post(
            "/videos",
            json={"id": "fails", "title": "Fail", "description": "Body", "tags": []},
        )
        assert resp.status_code == 502
        assert "Upstream error" in resp.json()["detail"]

    def test_missing_id(self, client, mock_dynamo_transport):
        resp = client.post("/videos", json={"title": "Missing ID"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_privacy(self, client, mock_dynamo_transport):
        resp = client.post(
            "/videos",
            json={"id": "v1", "title": "V1", "privacy_status": "invalid"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListVideos:
    def test_lists_videos(self, client, mock_dynamo_transport):
        mock_dynamo_transport.scan_items = [
            {"app": "youtube", "id": "v1", "title": "Video 1", "description": "Desc 1",
             "tags": ["test"], "category_id": "22", "privacy_status": "private",
             "status": "draft", "youtube_id": "", "s3_key": "", "thumbnail_s3_key": "",
             "scheduled_at": "", "error_message": "", "created_at": "", "updated_at": ""},
            {"app": "youtube", "id": "v2", "title": "Video 2", "description": "Desc 2",
             "tags": ["demo"], "category_id": "22", "privacy_status": "unlisted",
             "status": "uploaded", "youtube_id": "abc123", "s3_key": "",
             "thumbnail_s3_key": "", "scheduled_at": "", "error_message": "",
             "created_at": "", "updated_at": ""},
        ]
        resp = client.get("/videos")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["videos"]) == 2

    def test_filter_by_status(self, client, mock_dynamo_transport):
        mock_dynamo_transport.scan_items = [
            {"app": "youtube", "id": "v1", "title": "V1", "description": "",
             "tags": [], "category_id": "22", "privacy_status": "private",
             "status": "draft", "youtube_id": "", "s3_key": "", "thumbnail_s3_key": "",
             "scheduled_at": "", "error_message": "", "created_at": "", "updated_at": ""},
            {"app": "youtube", "id": "v2", "title": "V2", "description": "",
             "tags": [], "category_id": "22", "privacy_status": "unlisted",
             "status": "uploaded", "youtube_id": "abc123", "s3_key": "",
             "thumbnail_s3_key": "", "scheduled_at": "", "error_message": "",
             "created_at": "", "updated_at": ""},
        ]
        resp = client.get("/videos?status=uploaded")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["videos"][0]["id"] == "v2"


class TestGetVideo:
    def test_gets_existing(self, client, mock_dynamo_transport):
        resp = client.get("/videos/test-video")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "test-video"
        assert data["app"] == "youtube"

    def test_returns_404(self, client, mock_dynamo_transport):
        mock_dynamo_transport.item_missing = True
        resp = client.get("/videos/nonexistent")
        assert resp.status_code == 404


class TestUpdateVideo:
    def test_updates_title(self, client, mock_dynamo_transport):
        resp = client.put("/videos/test-video", json={"title": "Updated Title"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated Title"

    def test_returns_404(self, client, mock_dynamo_transport):
        mock_dynamo_transport.item_missing = True
        resp = client.put("/videos/nonexistent", json={"title": "Nope"})
        assert resp.status_code == 404

    def test_partial_update(self, client, mock_dynamo_transport):
        resp = client.put("/videos/test-video", json={"tags": ["new-tag"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["tags"] == ["new-tag"]
        # Original title preserved from fixture
        assert data["title"] == "Test Video"


class TestDeleteVideo:
    def test_deletes_existing(self, client, mock_dynamo_transport):
        resp = client.delete("/videos/test-video")
        assert resp.status_code == 200
        assert resp.json() == {"deleted": True, "id": "test-video"}

    def test_returns_404(self, client, mock_dynamo_transport):
        mock_dynamo_transport.item_missing = True
        resp = client.delete("/videos/nonexistent")
        assert resp.status_code == 404


class TestScheduleVideo:
    def test_schedules_video(self, client, mock_dynamo_transport):
        body = {"scheduled_at": "2026-07-01T09:00:00Z"}
        resp = client.put("/videos/test-video/schedule", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["scheduled_at"] == "2026-07-01T09:00:00Z"
        assert data["status"] == "scheduled"

    def test_returns_404(self, client, mock_dynamo_transport):
        mock_dynamo_transport.item_missing = True
        resp = client.put("/videos/nonexistent/schedule", json={"scheduled_at": "2026-07-01T00:00:00Z"})
        assert resp.status_code == 404

    def test_invalid_datetime(self, client, mock_dynamo_transport):
        resp = client.put("/videos/test-video/schedule", json={"scheduled_at": "not-a-date"})
        assert resp.status_code == 400


class TestUploadToYouTube:
    def test_s3_key_missing(self, client, mock_dynamo_transport):
        resp = client.post("/videos/test-video/upload")
        assert resp.status_code == 400
        assert "s3_key" in resp.json()["detail"]

    def test_returns_404(self, client, mock_dynamo_transport):
        mock_dynamo_transport.item_missing = True
        resp = client.post("/videos/nonexistent/upload")
        assert resp.status_code == 404

    def test_stub_response_with_s3_key(self, client, mock_dynamo_transport):
        # Mock a video with s3_key set
        mock_dynamo_transport.item_response = {
            "item": {
                "app": "youtube", "id": "test-video", "title": "Test",
                "description": "Desc", "tags": [], "category_id": "22",
                "privacy_status": "private", "status": "draft", "youtube_id": "",
                "s3_key": "videos/my-video.mp4", "thumbnail_s3_key": "",
                "scheduled_at": "", "error_message": "",
                "created_at": "", "updated_at": "",
            }
        }
        resp = client.post("/videos/test-video/upload")
        assert resp.status_code == 200
        assert resp.json()["success"] is False
        assert "YouTube upload endpoint ready" in resp.json()["message"]
