"""youtube-svc — YouTube video management, metadata store, and scheduling.

Videos are stored in DynamoDB (via dynamo-svc) with `app="youtube"`.
Video files are stored in S3 (via s3-svc) and uploaded to YouTube on demand.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException

from config import settings
from models import (
    CreateVideoRequest,
    DeleteResponse,
    HealthResponse,
    ScheduleVideoRequest,
    UpdateVideoRequest,
    UploadResponse,
    VideoListResponse,
    VideoResponse,
    YouTubeChannelResponse,
    YouTubeCommentRequest,
    YouTubeMetadataUpdateRequest,
    YouTubePlaylistItem,
    YouTubeThumbnailUpdateRequest,
    YouTubeTranscriptEntry,
    YouTubeVideoDetail,
    YouTubeVideoListItem,
    YouTubeVideoStats,
    _now,
)
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

# YouTube API integration
from youtube import (
    get_channel_info,
    get_transcript,
    get_video_details,
    get_video_stats,
    list_channel_videos,
    list_playlists,
    post_comment,
    set_video_thumbnail,
    update_video_metadata,
    upload_video,
)

setup_logging("orpheus")
logger = logging.getLogger(__name__)

APP_PARTITION = "youtube"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting orpheus...")
    yield
    logger.info("Shutting down orpheus...")


app = FastAPI(
    title="orpheus",
    description="YouTube video management — metadata store, scheduling, and upload via YouTube Data API",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Prometheus metrics ─────────────────────────
app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, include_in_schema=False)


# ═══════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════


def _dynamo_url(path: str) -> str:
    return f"{settings.dynamo_svc_url.rstrip('/')}{path}"


def _s3_url(path: str) -> str:
    return f"{settings.s3_svc_url.rstrip('/')}/{path.lstrip('/')}"


async def _call_dynamo(method: str, path: str, json_body: dict | None = None) -> Any:
    url = _dynamo_url(path)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.request(method, url, json=json_body)

    if resp.status_code != 200:
        logger.error("dynamo-svc %s %s → %s: %s", method, path, resp.status_code, resp.text[:300])
        raise HTTPException(
            status_code=502,
            detail=f"Upstream error: dynamo-svc returned {resp.status_code}",
        )

    try:
        return resp.json()
    except Exception:
        logger.error("dynamo-svc returned non-JSON: %s", resp.text[:300])
        raise HTTPException(status_code=502, detail="Invalid response from dynamo-svc")


async def _call_s3(method: str, path: str, **params) -> httpx.Response | None:
    url = _s3_url(path)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, url, params=params)

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        logger.error("s3-svc %s %s → %s: %s", method, path, resp.status_code, resp.text[:300])
        raise HTTPException(
            status_code=502,
            detail=f"Upstream error: s3-svc returned {resp.status_code}",
        )
    return resp


async def _fetch_all_items(app: str = APP_PARTITION) -> list[dict[str, Any]]:
    body = {
        "filter_expression": "app = :app",
        "expression_attr_values": {":app": app},
    }
    data = await _call_dynamo("POST", "/vimal/scan", json_body=body)
    if isinstance(data, dict):
        return data.get("items", [])
    return []


async def _fetch_item(app: str, item_id: str) -> dict[str, Any] | None:
    try:
        data = await _call_dynamo("GET", f"/vimal/item/{app}?id={item_id}")
        if isinstance(data, dict) and "item" in data:
            return data["item"]
        return None
    except HTTPException:
        return None


async def _put_item(item: dict[str, Any]) -> dict:
    return await _call_dynamo("POST", "/vimal/item", json_body=item)


async def _delete_item(app: str, item_id: str) -> bool:
    try:
        await _call_dynamo("DELETE", f"/vimal/item/{app}?id={item_id}")
        return True
    except HTTPException:
        return False


async def _download_s3_to_temp(s3_key: str) -> str:
    """Download a file from S3 (via atlas) to a temp file and return the path.

    S3 key format from atlas: ``{prefix}/{key}/{name}`` (e.g. ``videos/mykey/video.mp4``).
    Atlas internal download uses ``name`` and ``key`` query params separately.
    """
    parts = s3_key.split("/")
    if len(parts) >= 3:
        name = parts[-1]
        key = parts[-2]
    elif len(parts) == 2:
        name = parts[1]
        key = parts[0]
    else:
        name = parts[0]
        key = None
        params = {"name": name}
        url = _s3_url("bytes")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail=f"S3 key '{s3_key}' not found")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Failed to download from S3: {resp.status_code}")
        suffix = os.path.splitext(name)[1] or ".tmp"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(resp.content)
        tmp.close()
        return tmp.name

    params = {"name": name, "key": key}
    url = _s3_url("bytes")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"S3 key '{s3_key}' not found")
    if resp.status_code != 200:
        logger.error("s3-svc GET /bytes → %s: %s", resp.status_code, resp.text[:300])
        raise HTTPException(status_code=502, detail=f"Failed to download from S3: {resp.status_code}")

    suffix = os.path.splitext(name)[1] or ".tmp"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


# ═══════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════

# ─── Health ─────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse()


# ─── Create video entry ─────────────────────────


@app.post("/videos", response_model=VideoResponse, status_code=201, tags=["videos"])
async def create_video(body: CreateVideoRequest):
    """Create a new video metadata entry (not yet uploaded to YouTube)."""
    now = _now()
    item = {
        "app": APP_PARTITION,
        "id": body.id,
        "title": body.title.strip(),
        "description": body.description.strip(),
        "tags": body.tags,
        "category_id": body.category_id,
        "privacy_status": body.privacy_status,
        "status": "draft",
        "youtube_id": "",
        "s3_key": body.s3_key,
        "thumbnail_s3_key": body.thumbnail_s3_key,
        "scheduled_at": "",
        "error_message": "",
        "created_at": now,
        "updated_at": now,
    }

    try:
        await _put_item(item)
    except HTTPException:
        raise

    logger.info("Video created: id=%s title=%s", item["id"], item["title"])
    return VideoResponse.from_dynamo(item)


# ─── List videos ────────────────────────────────


@app.get("/videos", response_model=VideoListResponse, tags=["videos"])
async def list_videos(status: str | None = None):
    """List all videos, optionally filtered by status."""
    items = await _fetch_all_items()
    videos = [VideoResponse.from_dynamo(i) for i in items]

    if status:
        videos = [v for v in videos if v.status == status]

    return VideoListResponse(videos=videos, count=len(videos))


# ─── Get single video ───────────────────────────


@app.get("/videos/{video_id}", response_model=VideoResponse, tags=["videos"])
async def get_video(video_id: str):
    """Get a single video entry by its internal ID."""
    item = await _fetch_item(APP_PARTITION, video_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")
    return VideoResponse.from_dynamo(item)


# ─── Update video ───────────────────────────────


@app.put("/videos/{video_id}", response_model=VideoResponse, tags=["videos"])
async def update_video(video_id: str, body: UpdateVideoRequest):
    """Update an existing video entry. Only provided fields are changed."""
    existing = await _fetch_item(APP_PARTITION, video_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    now = _now()
    if body.title is not None:
        existing["title"] = body.title.strip()
    if body.description is not None:
        existing["description"] = body.description.strip()
    if body.tags is not None:
        existing["tags"] = body.tags
    if body.category_id is not None:
        existing["category_id"] = body.category_id
    if body.privacy_status is not None:
        existing["privacy_status"] = body.privacy_status
    if body.s3_key is not None:
        existing["s3_key"] = body.s3_key
    if body.thumbnail_s3_key is not None:
        existing["thumbnail_s3_key"] = body.thumbnail_s3_key
    existing["updated_at"] = now

    await _put_item(existing)
    logger.info("Video updated: id=%s", video_id)
    return VideoResponse.from_dynamo(existing)


# ─── Delete video ───────────────────────────────


@app.delete("/videos/{video_id}", response_model=DeleteResponse, tags=["videos"])
async def delete_video(video_id: str):
    """Delete a video entry."""
    existing = await _fetch_item(APP_PARTITION, video_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    deleted = await _delete_item(APP_PARTITION, video_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete video from database")

    logger.info("Video deleted: id=%s", video_id)
    return DeleteResponse(deleted=True, id=video_id)


# ─── Schedule video ─────────────────────────────


@app.put("/videos/{video_id}/schedule", response_model=VideoResponse, tags=["scheduling"])
async def schedule_video(video_id: str, body: ScheduleVideoRequest):
    """Set the scheduled upload time for a video."""
    existing = await _fetch_item(APP_PARTITION, video_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    # Validate the datetime string
    try:
        datetime.fromisoformat(body.scheduled_at)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO 8601.")

    now = _now()
    existing["scheduled_at"] = body.scheduled_at
    existing["status"] = "scheduled"
    existing["updated_at"] = now

    await _put_item(existing)
    logger.info("Video scheduled: id=%s scheduled_at=%s", video_id, body.scheduled_at)
    return VideoResponse.from_dynamo(existing)


# ─── Upload to YouTube ──────────────────────────


@app.post("/videos/{video_id}/upload", response_model=UploadResponse, tags=["youtube"])
async def upload_to_youtube(video_id: str):
    """Upload a video to YouTube. Video file must already be in S3.

    Downloads the video from S3 (via atlas), then uploads to YouTube via the Data API.
    The DynamoDB record is automatically updated with the YouTube ID.
    """
    existing = await _fetch_item(APP_PARTITION, video_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    if not existing.get("s3_key"):
        raise HTTPException(
            status_code=400,
            detail="No video file in S3. Set s3_key first via PUT /videos/{id} or set it on creation.",
        )

    try:
        local_path = await _download_s3_to_temp(existing["s3_key"])
        result = upload_video(
            video_path=local_path,
            title=existing.get("title", "Untitled"),
            description=existing.get("description", ""),
            tags=existing.get("tags", []),
            category_id=existing.get("category_id", "22"),
            privacy_status=existing.get("privacy_status", "private"),
            scheduled_at=existing.get("scheduled_at") or None,
        )
        os.unlink(local_path)

        # Update DynamoDB record
        now = _now()
        existing["youtube_id"] = result["video_id"]
        existing["status"] = "uploaded"
        existing["updated_at"] = now
        await _put_item(existing)

        return UploadResponse(
            success=True,
            youtube_id=result["video_id"],
            video_url=result.get("video_url", f"https://youtu.be/{result['video_id']}"),
            message=f"Video uploaded: {result.get('title', existing['title'])}",
        )
    except Exception as e:
        logger.error("Upload error for %s: %s", video_id, e)
        raise HTTPException(status_code=502, detail=f"Upload failed: {str(e)[:200]}")


# ═══════════════════════════════════════════════
# Routes — YouTube Data API
# ═══════════════════════════════════════════════


@app.get("/youtube/channel/{channel_id}", response_model=YouTubeChannelResponse, tags=["youtube"])
async def youtube_channel_info(channel_id: str):
    """Get detailed information about a YouTube channel."""
    try:
        info = get_channel_info(channel_id)
        return YouTubeChannelResponse(**info)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Channel info error: %s", e)
        raise HTTPException(status_code=502, detail=f"YouTube API error: {str(e)}")


@app.get("/youtube/channel/{channel_id}/videos", response_model=list[YouTubeVideoListItem], tags=["youtube"])
async def youtube_channel_videos(channel_id: str, max_results: int = 50):
    """List all videos from a channel."""
    try:
        videos = list_channel_videos(channel_id, max_results=min(max_results, 200))
        return [YouTubeVideoListItem(**v) for v in videos]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Channel videos error: %s", e)
        raise HTTPException(status_code=502, detail=f"YouTube API error: {str(e)}")


@app.get("/youtube/channel/{channel_id}/playlists", response_model=list[YouTubePlaylistItem], tags=["youtube"])
async def youtube_channel_playlists(channel_id: str, max_results: int = 50):
    """List all playlists from a channel."""
    try:
        playlists = list_playlists(channel_id, max_results=min(max_results, 200))
        return [YouTubePlaylistItem(**p) for p in playlists]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Playlist list error: %s", e)
        raise HTTPException(status_code=502, detail=f"YouTube API error: {str(e)}")


@app.get("/youtube/video/{video_id}", response_model=YouTubeVideoDetail, tags=["youtube"])
async def youtube_video_detail(video_id: str):
    """Get detailed information about a specific YouTube video."""
    try:
        detail = get_video_details(video_id)
        return YouTubeVideoDetail(**detail)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Video detail error: %s", e)
        raise HTTPException(status_code=502, detail=f"YouTube API error: {str(e)}")


@app.get("/youtube/video/{video_id}/stats", response_model=YouTubeVideoStats, tags=["youtube"])
async def youtube_video_stats(video_id: str):
    """Get statistics for a video (views, likes, comments)."""
    try:
        stats = get_video_stats(video_id)
        return YouTubeVideoStats(**stats)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Video stats error: %s", e)
        raise HTTPException(status_code=502, detail=f"YouTube API error: {str(e)}")


@app.get("/youtube/video/{video_id}/transcript", response_model=list[YouTubeTranscriptEntry], tags=["youtube"])
async def youtube_video_transcript(video_id: str):
    """Get the transcript/captions for a video."""
    try:
        entries = get_transcript(video_id)
        return [YouTubeTranscriptEntry(**e) for e in entries]
    except Exception as e:
        logger.warning("Transcript error for %s: %s", video_id, e)
        return []


@app.patch("/youtube/video/{video_id}/metadata", tags=["youtube"])
async def youtube_update_metadata(video_id: str, body: YouTubeMetadataUpdateRequest):
    """Update a video's title, description, tags, or category on YouTube."""
    try:
        result = update_video_metadata(
            video_id=video_id,
            title=body.title,
            description=body.description,
            tags=body.tags,
            category_id=body.category_id,
        )
        return {"success": result, "video_id": video_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Metadata update error: %s", e)
        raise HTTPException(status_code=502, detail=f"YouTube API error: {str(e)}")


@app.post("/youtube/video/{video_id}/thumbnail", tags=["youtube"])
async def youtube_set_thumbnail(video_id: str, body: YouTubeThumbnailUpdateRequest):
    """Set a custom thumbnail for a video. The image file must already be in S3."""
    try:
        local_path = await _download_s3_to_temp(body.s3_key)
        try:
            result = set_video_thumbnail(video_id, local_path)
            return {"success": result, "video_id": video_id}
        finally:
            os.unlink(local_path)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Thumbnail set error: %s", e)
        raise HTTPException(status_code=502, detail=f"YouTube API error: {str(e)}")


@app.post("/youtube/video/{video_id}/comment", tags=["youtube"])
async def youtube_post_comment(video_id: str, body: YouTubeCommentRequest):
    """Post a top-level comment on a video."""
    try:
        result = post_comment(video_id, body.text)
        return {"success": result, "video_id": video_id}
    except Exception as e:
        logger.error("Comment post error: %s", e)
        raise HTTPException(status_code=502, detail=f"YouTube API error: {str(e)}")
