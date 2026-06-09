"""youtube-svc — YouTube video management, metadata store, and scheduling.

Videos are stored in DynamoDB (via dynamo-svc) with `app="youtube"`.
Video files are stored in S3 (via s3-svc) and uploaded to YouTube on demand.
"""

from __future__ import annotations

import json
import logging
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
    _now,
)
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

setup_logging("youtube-svc")
logger = logging.getLogger(__name__)

APP_PARTITION = "youtube"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting youtube-svc...")
    yield
    logger.info("Shutting down youtube-svc...")


app = FastAPI(
    title="youtube-svc",
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
    return f"{settings.s3_svc_url.rstrip('/')}{path}"


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
    """Upload a video to YouTube. Video file must already be in S3."""
    # This is a stub — YouTube upload logic will be implemented in a dedicated module.
    # For now, it validates the video exists and has an s3_key set.
    existing = await _fetch_item(APP_PARTITION, video_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    if not existing.get("s3_key"):
        raise HTTPException(
            status_code=400,
            detail="No video file in S3. Set s3_key first via PUT /videos/{id} or set it on creation.",
        )

    return UploadResponse(
        success=False,
        youtube_id="",
        video_url="",
        message="YouTube upload endpoint ready — requires YouTube API credentials to be configured.",
    )
