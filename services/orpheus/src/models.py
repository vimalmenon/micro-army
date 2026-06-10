"""Pydantic models for orpheus — video metadata, scheduling, and YouTube Data API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Request models ─────────────────────────────


class CreateVideoRequest(BaseModel):
    """Create a new video metadata entry (not yet uploaded to YouTube)."""
    id: str = Field(..., min_length=1, max_length=128, description="URL-safe internal ID")
    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="", description="YouTube video description")
    tags: list[str] = Field(default_factory=list, max_length=50)
    category_id: str = Field(default="22", description="YouTube category ID")
    privacy_status: str = Field(default="private", pattern=r"^(public|unlisted|private)$")
    s3_key: str = Field(default="", description="S3 key of the video file")
    thumbnail_s3_key: str = Field(default="", description="S3 key of the thumbnail image")


class UpdateVideoRequest(BaseModel):
    """Partial update — only provided fields are changed."""
    title: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None
    tags: list[str] | None = Field(None, max_length=50)
    category_id: str | None = None
    privacy_status: str | None = Field(None, pattern=r"^(public|unlisted|private)$")
    s3_key: str | None = None
    thumbnail_s3_key: str | None = None


class ScheduleVideoRequest(BaseModel):
    """Set the scheduled upload time for a video."""
    scheduled_at: str = Field(..., description="ISO datetime for scheduled upload")


# ─── YouTube API request models ─────────────────


class YouTubeUploadRequest(BaseModel):
    """Upload a video to YouTube from an S3 key."""
    s3_key: str = Field(..., description="S3 key of the video file")
    title: str = Field(..., min_length=1, max_length=100, description="YouTube video title (max 100 chars)")
    description: str = Field(default="")
    tags: list[str] = Field(default_factory=list, max_length=50)
    category_id: str = Field(default="22")
    privacy_status: str = Field(default="private", pattern=r"^(public|unlisted|private)$")
    scheduled_at: str | None = Field(None, description="ISO datetime for scheduled publishing")


class YouTubeMetadataUpdateRequest(BaseModel):
    """Update YouTube video metadata."""
    title: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    tags: list[str] | None = Field(None, max_length=50)
    category_id: str | None = None


class YouTubeThumbnailUpdateRequest(BaseModel):
    """Set a custom thumbnail from an S3 key."""
    s3_key: str = Field(..., description="S3 key of the thumbnail image")


class YouTubeCommentRequest(BaseModel):
    """Post a comment on a video."""
    text: str = Field(..., min_length=1, max_length=5000)


# ─── Response models ────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "orpheus"


class VideoResponse(BaseModel):
    """Full video record as stored in DynamoDB."""
    app: str = "youtube"
    id: str
    title: str
    description: str
    tags: list[str] = []
    category_id: str = "22"
    privacy_status: str = "private"
    status: str = "draft"
    youtube_id: str = ""
    s3_key: str = ""
    thumbnail_s3_key: str = ""
    scheduled_at: str = ""
    error_message: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dynamo(cls, item: dict[str, Any]) -> VideoResponse:
        return cls(
            app=item.get("app", "youtube"),
            id=item.get("id", ""),
            title=item.get("title", ""),
            description=item.get("description", ""),
            tags=item.get("tags", []),
            category_id=item.get("category_id", "22"),
            privacy_status=item.get("privacy_status", "private"),
            status=item.get("status", "draft"),
            youtube_id=item.get("youtube_id", ""),
            s3_key=item.get("s3_key", ""),
            thumbnail_s3_key=item.get("thumbnail_s3_key", ""),
            scheduled_at=item.get("scheduled_at", ""),
            error_message=item.get("error_message", ""),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
        )


class VideoListResponse(BaseModel):
    videos: list[VideoResponse]
    count: int


class DeleteResponse(BaseModel):
    deleted: bool
    id: str


class UploadResponse(BaseModel):
    success: bool
    youtube_id: str = ""
    video_url: str = ""
    message: str = ""


# ─── YouTube API response models ────────────────


class YouTubeChannelResponse(BaseModel):
    id: str
    title: str
    description: str = ""
    custom_url: str = ""
    published_at: str = ""
    country: str = ""
    thumbnail_url: str = ""
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0
    privacy_status: str = ""


class YouTubeVideoDetail(BaseModel):
    video_id: str
    title: str = ""
    description: str = ""
    tags: list[str] = []
    category_id: str = ""
    published_at: str = ""
    channel_id: str = ""
    channel_title: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    privacy_status: str = ""
    embeddable: bool = True
    license: str = ""


class YouTubeVideoStats(BaseModel):
    video_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0


class YouTubeVideoListItem(BaseModel):
    video_id: str
    title: str = ""
    description: str = ""
    published_at: str = ""
    channel_id: str = ""
    thumbnails: dict[str, Any] = {}


class YouTubePlaylistItem(BaseModel):
    playlist_id: str
    title: str = ""
    description: str = ""
    item_count: int = 0
    published_at: str = ""
    thumbnails: dict[str, Any] = {}


class YouTubeTranscriptEntry(BaseModel):
    text: str
    start: float = 0.0
    duration: float = 0.0
