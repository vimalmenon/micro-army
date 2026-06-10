"""Pydantic models for youtube-svc — video metadata storage + scheduling."""

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


# ─── Response models ────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "youtube-svc"


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
