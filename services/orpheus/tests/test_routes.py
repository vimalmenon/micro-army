"""Tests for orpheus FastAPI routes."""

from unittest.mock import patch

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
        assert resp.json() == {"status": "ok", "service": "orpheus"}


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


# ═══════════════════════════════════════════════
# YouTube Data API endpoint tests
# ═══════════════════════════════════════════════

MOCK_CHANNEL_INFO = {
    "id": "UC_test123",
    "title": "Test Channel",
    "description": "A test channel",
    "custom_url": "@testchannel",
    "published_at": "2020-01-01T00:00:00Z",
    "country": "US",
    "thumbnail_url": "https://yt3.googleusercontent.com/test",
    "subscriber_count": 1000,
    "video_count": 50,
    "view_count": 50000,
    "privacy_status": "public",
}

MOCK_VIDEO_DETAIL = {
    "video_id": "abc123",
    "title": "Test Video",
    "description": "A test video",
    "tags": ["test", "demo"],
    "category_id": "22",
    "published_at": "2024-01-01T00:00:00Z",
    "channel_id": "UC_test123",
    "channel_title": "Test Channel",
    "views": 5000,
    "likes": 200,
    "comments": 50,
    "privacy_status": "public",
    "embeddable": True,
    "license": "youtube",
}

MOCK_VIDEO_STATS = {
    "video_id": "abc123",
    "views": 5000,
    "likes": 200,
    "comments": 50,
}


class TestYouTubeChannelInfo:
    def test_returns_channel_info(self, client):
        with patch("main.get_channel_info", return_value=MOCK_CHANNEL_INFO):
            resp = client.get("/youtube/channel/UC_test123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "UC_test123"
        assert data["title"] == "Test Channel"
        assert data["subscriber_count"] == 1000

    def test_returns_404(self, client):
        with patch("main.get_channel_info", side_effect=ValueError("not found")):
            resp = client.get("/youtube/channel/nonexistent")
        assert resp.status_code == 404


class TestYouTubeChannelVideos:
    def test_returns_video_list(self, client):
        mock_videos = [
            {"video_id": "v1", "title": "Video 1", "description": "Desc 1",
             "published_at": "2024-01-01T00:00:00Z", "channel_id": "UC_test123",
             "thumbnails": {}},
        ]
        with patch("main.list_channel_videos", return_value=mock_videos):
            resp = client.get("/youtube/channel/UC_test123/videos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["video_id"] == "v1"


class TestYouTubeVideoDetail:
    def test_returns_video_detail(self, client):
        with patch("main.get_video_details", return_value=MOCK_VIDEO_DETAIL):
            resp = client.get("/youtube/video/abc123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "abc123"
        assert data["title"] == "Test Video"
        assert data["views"] == 5000

    def test_returns_404(self, client):
        with patch("main.get_video_details", side_effect=ValueError("not found")):
            resp = client.get("/youtube/video/nonexistent")
        assert resp.status_code == 404


class TestYouTubeVideoStats:
    def test_returns_stats(self, client):
        with patch("main.get_video_stats", return_value=MOCK_VIDEO_STATS):
            resp = client.get("/youtube/video/abc123/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["video_id"] == "abc123"
        assert data["views"] == 5000

    def test_returns_404(self, client):
        with patch("main.get_video_stats", side_effect=ValueError("not found")):
            resp = client.get("/youtube/video/nonexistent/stats")
        assert resp.status_code == 404


class TestYouTubeVideoTranscript:
    def test_returns_transcript(self, client):
        mock_transcript = [
            {"text": "Hello world", "start": 0.0, "duration": 2.5},
            {"text": "This is a test", "start": 2.5, "duration": 3.0},
        ]
        with patch("main.get_transcript", return_value=mock_transcript):
            resp = client.get("/youtube/video/abc123/transcript")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["text"] == "Hello world"

    def test_empty_transcript(self, client):
        with patch("main.get_transcript", return_value=[]):
            resp = client.get("/youtube/video/abc123/transcript")
        assert resp.status_code == 200
        assert resp.json() == []


class TestYouTubeUpdateMetadata:
    def test_updates_metadata(self, client):
        with patch("main.update_video_metadata", return_value=True):
            resp = client.patch(
                "/youtube/video/abc123/metadata",
                json={"title": "New Title"},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_returns_404(self, client):
        with patch("main.update_video_metadata", side_effect=ValueError("not found")):
            resp = client.patch(
                "/youtube/video/nonexistent/metadata",
                json={"title": "Nope"},
            )
        assert resp.status_code == 404


class TestYouTubePostComment:
    def test_posts_comment(self, client):
        with patch("main.post_comment", return_value=True):
            resp = client.post(
                "/youtube/video/abc123/comment",
                json={"text": "Great video!"},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_missing_text(self, client):
        resp = client.post(
            "/youtube/video/abc123/comment",
            json={},
        )
        assert resp.status_code == 422
