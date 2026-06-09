"""wiki-svc — Tag-based wiki knowledge store over DynamoDB + S3.

Articles are stored in DynamoDB (via dynamo-svc) with `app="wiki"`.
File attachments go to S3 (via s3-svc). Tags enable flexible categorisation
for homelab configs, video scripts, blog posts, AI memory, and more.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from config import settings
from models import (
    ArticleListResponse,
    ArticleResponse,
    CreateArticleRequest,
    DeleteResponse,
    FileAttachRequest,
    FileAttachResponse,
    HealthResponse,
    UpdateArticleRequest,
    _now,
)
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

setup_logging("wiki-svc")
logger = logging.getLogger(__name__)

# All wiki articles live under this DynamoDB partition
APP_PARTITION = "wiki"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting wiki-svc...")
    yield
    logger.info("Shutting down wiki-svc...")


app = FastAPI(
    title="wiki-svc",
    description="Tag-based wiki knowledge store — DynamoDB-backed, S3 file attachments",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Prometheus metrics ─────────────────────────
app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, include_in_schema=False)


# ═══════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════

DYNAMO_API = ""


def _dynamo_url(path: str) -> str:
    return f"{settings.dynamo_svc_url.rstrip('/')}{path}"


async def _call_dynamo(method: str, path: str, json_body: dict | None = None) -> Any:
    """Call dynamo-svc and return parsed JSON response. Raises on non-200."""
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
    """Call s3-svc. Returns None for 404s (not found), raises for errors."""
    url = f"{settings.s3_svc_url.rstrip('/')}{path}"
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
    """Fetch all items for a given app partition from dynamo-svc."""
    data = await _call_dynamo("GET", f"/vimal/items?app={app}")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", data.get("data", []))
    return []


async def _fetch_item(app: str, item_id: str) -> dict[str, Any] | None:
    """Fetch a single item. Returns None if not found."""
    try:
        data = await _call_dynamo("GET", f"/vimal/item?app={app}&id={item_id}")
        return data if isinstance(data, dict) else None
    except HTTPException as e:
        if e.status_code == 502:
            # Check if it's a 404 from dynamo-svc vs a real error
            return None
        raise


async def _put_item(item: dict[str, Any]) -> dict:
    """Create or update an item in DynamoDB via dynamo-svc."""
    return await _call_dynamo("POST", "/vimal/item", json_body=item)


async def _delete_item(app: str, item_id: str) -> bool:
    """Delete an item from DynamoDB. Returns True if deleted."""
    try:
        await _call_dynamo("DELETE", f"/vimal/item?app={app}&id={item_id}")
        return True
    except HTTPException:
        return False


def _sanitise_filename(name: str) -> str:
    """Strip path traversal and dangerous characters from a filename."""
    # Remove anything that isn't alphanumeric, dot, hyphen, underscore
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    # Prevent path traversal
    safe = safe.replace("..", "_")
    # Limit length
    return safe[:255]


def _validate_file(name: str, data_b64: str) -> tuple[str, bytes]:
    """Validate filename extension and size. Returns (safe_name, decoded_bytes)."""
    # Check extension
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type '.{ext}' not allowed. Allowed: {', '.join(settings.allowed_extensions)}",
        )

    # Sanitise name
    safe_name = _sanitise_filename(name)

    # Decode and check size
    try:
        raw = base64.b64decode(data_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 data")

    if len(raw) > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(raw)} bytes). Max: {settings.max_file_size} bytes",
        )

    return safe_name, raw


# ═══════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════

# ─── Health ─────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse()


# ─── List articles ───────────────────────────────


@app.get("/wiki", response_model=ArticleListResponse, tags=["wiki"])
async def list_articles(
    tag: list[str] = Query(default=[], description="Filter by tag(s) — AND logic"),
    author: str | None = Query(None, description="Filter by author"),
):
    """List all wiki articles, optionally filtered by tag(s) and/or author."""
    items = await _fetch_all_items()
    articles = [ArticleResponse.from_dynamo(i) for i in items]

    # Filter by tags (AND — all specified tags must be present)
    if tag:
        tag_set = set(tag)
        articles = [a for a in articles if tag_set.issubset(set(a.tags))]

    # Filter by author
    if author:
        articles = [a for a in articles if a.author == author]

    return ArticleListResponse(articles=articles, count=len(articles))


# ─── Get single article ──────────────────────────


@app.get("/wiki/{article_id}", response_model=ArticleResponse, tags=["wiki"])
async def get_article(article_id: str):
    """Get a single wiki article by its slug."""
    item = await _fetch_item(APP_PARTITION, article_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found")
    return ArticleResponse.from_dynamo(item)


# ─── Search articles ─────────────────────────────


@app.get("/wiki/search/{query}", response_model=ArticleListResponse, tags=["wiki"])
async def search_articles(query: str):
    """Search article titles and content for a query string."""
    items = await _fetch_all_items()
    q = query.lower()
    matches = [
        ArticleResponse.from_dynamo(i)
        for i in items
        if q in i.get("title", "").lower()
        or q in i.get("content", "").lower()
        or any(q in t.lower() for t in i.get("tags", []))
    ]
    return ArticleListResponse(articles=matches, count=len(matches))


# ─── Create article ──────────────────────────────


@app.post("/wiki", response_model=ArticleResponse, status_code=201, tags=["wiki"])
async def create_article(body: CreateArticleRequest, author: str = Query("elara", description="Article author")):
    """Create a new wiki article."""
    now = _now()
    item = {
        "app": APP_PARTITION,
        "id": body.id,
        "title": body.title.strip(),
        "content": body.content.strip(),
        "tags": body.tags,
        "files": [],
        "author": author,
        "created_at": now,
        "updated_at": now,
    }

    try:
        await _put_item(item)
    except HTTPException:
        raise  # re-raise 502 from upstream

    logger.info("Article created: id=%s title=%s tags=%s", item["id"], item["title"], item["tags"])
    return ArticleResponse.from_dynamo(item)


# ─── Update article ──────────────────────────────


@app.put("/wiki/{article_id}", response_model=ArticleResponse, tags=["wiki"])
async def update_article(article_id: str, body: UpdateArticleRequest):
    """Update an existing wiki article. Only provided fields are changed."""
    existing = await _fetch_item(APP_PARTITION, article_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found")

    now = _now()
    if body.title is not None:
        existing["title"] = body.title.strip()
    if body.content is not None:
        existing["content"] = body.content.strip()
    if body.tags is not None:
        existing["tags"] = body.tags
    existing["updated_at"] = now

    await _put_item(existing)
    logger.info("Article updated: id=%s", article_id)
    return ArticleResponse.from_dynamo(existing)


# ─── Delete article ──────────────────────────────


@app.delete("/wiki/{article_id}", response_model=DeleteResponse, tags=["wiki"])
async def delete_article(article_id: str):
    """Delete a wiki article and its file attachments."""
    # Fetch the article first to clean up files
    existing = await _fetch_item(APP_PARTITION, article_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found")

    # Delete any attached files from S3
    for f in existing.get("files", []):
        try:
            await _call_s3("DELETE", "/delete", name=f.get("name", ""), key=f.get("key", ""))
        except HTTPException:
            logger.warning("Failed to delete S3 file: %s", f.get("key", "unknown"))

    # Delete the DynamoDB item
    deleted = await _delete_item(APP_PARTITION, article_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete article from database")

    logger.info("Article deleted: id=%s files_cleaned=%d", article_id, len(existing.get("files", [])))
    return DeleteResponse(deleted=True, id=article_id)


# ─── Attach file ─────────────────────────────────


@app.post("/wiki/{article_id}/files", response_model=FileAttachResponse, status_code=201, tags=["files"])
async def attach_file(article_id: str, body: FileAttachRequest):
    """Upload a file attachment to an existing wiki article."""
    # Verify article exists
    existing = await _fetch_item(APP_PARTITION, article_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found")

    # Validate file
    safe_name, raw_data = _validate_file(body.name, body.data)

    # Upload to S3 via s3-svc — organise under images/wiki/{article_id}/
    s3_key = f"images/wiki/{article_id}"
    import base64 as b64
    data_b64 = b64.b64encode(raw_data).decode()

    # Call s3-svc upload
    url = f"{settings.s3_svc_url.rstrip('/')}/upload"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json={"name": safe_name, "data": data_b64, "key": s3_key})

    if resp.status_code != 200:
        logger.error("s3-svc upload failed: %s: %s", resp.status_code, resp.text[:300])
        raise HTTPException(status_code=502, detail="File upload to S3 failed")

    full_s3_key = resp.json().get("s3_key", f"{s3_key}/{safe_name}")

    # Update the article's files list in DynamoDB
    file_entry = {"name": safe_name, "key": full_s3_key, "size": len(raw_data)}
    files = existing.get("files", [])
    files.append(file_entry)
    existing["files"] = files
    existing["updated_at"] = _now()
    await _put_item(existing)

    logger.info("File attached: article=%s file=%s size=%d", article_id, safe_name, len(raw_data))
    return FileAttachResponse(success=True, s3_key=full_s3_key, name=safe_name, size=len(raw_data))


# ─── Download file ───────────────────────────────


@app.get("/wiki/{article_id}/files/{file_name}", tags=["files"])
async def download_file(article_id: str, file_name: str):
    """Download a file attached to a wiki article."""
    # Verify article exists
    existing = await _fetch_item(APP_PARTITION, article_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found")

    # Find the file in the article's files list
    file_entry = next((f for f in existing.get("files", []) if f.get("name") == file_name), None)
    if file_entry is None:
        raise HTTPException(status_code=404, detail=f"File '{file_name}' not found on article '{article_id}'")

    # Fetch from s3-svc
    resp = await _call_s3("GET", "/bytes", name=file_name, key=f"images/wiki/{article_id}")
    if resp is None:
        raise HTTPException(status_code=404, detail="File not found in S3")

    content_type = file_entry.get("content_type", "application/octet-stream")
    return Response(content=resp.content, media_type=content_type)


# ─── List files for article ──────────────────────


@app.get("/wiki/{article_id}/files", tags=["files"])
async def list_files(article_id: str):
    """List all file attachments for a wiki article."""
    existing = await _fetch_item(APP_PARTITION, article_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found")

    return {"files": existing.get("files", []), "count": len(existing.get("files", []))}
