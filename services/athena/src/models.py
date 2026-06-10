"""Pydantic models for wiki-svc — articles tagged by category."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ─── Internal helpers ───────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Request models ─────────────────────────────


class CreateArticleRequest(BaseModel):
    """Create a new wiki article."""
    id: str = Field(..., min_length=1, max_length=128, description="URL-safe slug")
    title: str = Field(..., min_length=1, max_length=256)
    content: str = Field(default="", description="Markdown body")
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("id")
    @classmethod
    def slug_must_be_url_safe(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$|^[a-z0-9]$", v):
            raise ValueError(
                "id must be a URL-safe slug: lowercase, numbers, hyphens, underscores only"
            )
        return v

    @field_validator("tags")
    @classmethod
    def tags_must_be_lowercase(cls, v: list[str]) -> list[str]:
        return [t.strip().lower().replace(" ", "-") for t in v]


class UpdateArticleRequest(BaseModel):
    """Partial update — only provided fields are changed."""
    title: str | None = Field(None, min_length=1, max_length=256)
    content: str | None = None
    tags: list[str] | None = Field(None, max_length=20)

    @field_validator("tags")
    @classmethod
    def tags_must_be_lowercase(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            return [t.strip().lower().replace(" ", "-") for t in v]
        return v


class FileAttachRequest(BaseModel):
    """Upload a file attachment to a wiki article."""
    name: str = Field(..., min_length=1, max_length=255)
    data: str = Field(..., description="Base64-encoded file bytes")


# ─── Response models ────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "wiki-svc"


class ArticleResponse(BaseModel):
    """Full article as stored in DynamoDB."""
    app: str = "wiki"
    id: str
    title: str
    content: str
    tags: list[str] = []
    files: list[dict[str, Any]] = []
    author: str = "unknown"
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dynamo(cls, item: dict[str, Any]) -> ArticleResponse:
        """Build from a dynamo-svc item response."""
        return cls(
            app=item.get("app", "wiki"),
            id=item.get("id", ""),
            title=item.get("title", ""),
            content=item.get("content", ""),
            tags=item.get("tags", []),
            files=item.get("files", []),
            author=item.get("author", "unknown"),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
        )


class ArticleListResponse(BaseModel):
    articles: list[ArticleResponse]
    count: int


class FileAttachResponse(BaseModel):
    success: bool
    s3_key: str
    name: str
    size: int


class DeleteResponse(BaseModel):
    deleted: bool
    id: str
