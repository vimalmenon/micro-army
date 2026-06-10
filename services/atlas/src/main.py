"""s3-svc: S3 file storage microservice.

Organizes files by content type into prefix folders (images/, audio/,
videos/, json/, data/). Uses ESO-injected AWS credentials.
"""

import base64
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from config import settings
from models import detect_content_type, s3_key_for
from s3_client import S3Client
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

setup_logging("s3-svc")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting s3-svc...")
    S3Client()
    yield
    logger.info("Shutting down s3-svc...")


app = FastAPI(
    title="s3-svc",
    description="S3 file storage gateway microservice",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Prometheus metrics ─────────────────────────
app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, include_in_schema=False)

s3 = S3Client()


# ─── Request / Response models ──────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "s3-svc"


class UploadRequest(BaseModel):
    name: str
    data: str  # base64-encoded
    key: str | None = None


class UploadResponse(BaseModel):
    success: bool
    s3_key: str


class DeleteResponse(BaseModel):
    deleted: bool


class ListResponse(BaseModel):
    items: list[dict]
    count: int


# ─── Health ─────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse()


# ─── Upload ─────────────────────────────────────


@app.post("/upload", response_model=UploadResponse, tags=["storage"])
async def upload(body: UploadRequest):
    """Upload a file to S3. Data must be base64-encoded bytes."""
    try:
        detect_content_type(body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        raw_data = base64.b64decode(body.data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 data")

    s3_key = s3_key_for(body.name, key=body.key)
    success = s3.upload_bytes(raw_data, body.name, key=body.key)
    if not success:
        raise HTTPException(status_code=500, detail="Upload to S3 failed")

    return UploadResponse(success=True, s3_key=s3_key)


# ─── Download ───────────────────────────────────


@app.get("/bytes", tags=["storage"])
async def get_bytes(
    name: str = Query(..., description="Filename"),
    key: str | None = Query(None, description="Optional subfolder key"),
):
    """Retrieve raw file bytes from S3."""
    try:
        data = s3.get_bytes(name, key=key)
        content_type = detect_content_type(name).value
        from fastapi.responses import Response
        return Response(content=data, media_type=content_type)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Delete ─────────────────────────────────────


@app.delete("/delete", response_model=DeleteResponse, tags=["storage"])
async def delete(
    name: str = Query(..., description="Filename"),
    key: str | None = Query(None, description="Optional subfolder key"),
):
    """Delete a file from S3."""
    try:
        s3.delete(name, key=key, silent=True)
        return DeleteResponse(deleted=True)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── List ───────────────────────────────────────


@app.get("/list", response_model=ListResponse, tags=["storage"])
async def list_items(
    prefix: str = Query("", description="S3 key prefix filter"),
):
    """List files in the S3 bucket, optionally filtered by prefix."""
    try:
        items = s3.list_items(prefix=prefix)
        return ListResponse(items=items, count=len(items))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
