"""YouTube Data API v3 integration for Orpheus — upload, metadata, stats, comments, transcripts."""

from __future__ import annotations

import logging
from typing import Any

from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuth2Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi

from config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


# ─── Auth ───────────────────────────────────────────────────────────────────


def _build_credentials() -> Credentials:
    """Build OAuth2 credentials from env vars (refresh token flow)."""
    return OAuth2Credentials(
        token=None,  # No access token yet; will refresh
        refresh_token=settings.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )


def get_youtube_service():
    """Get an authenticated YouTube API service instance.

    The credentials are built from env vars. If the access token is expired
    (it always is on first call), the refresh token is used automatically.
    """
    creds = _build_credentials()
    # Refresh now so the first API call doesn't 401
    try:
        creds.refresh(Request())
    except Exception as e:
        logger.warning("Token refresh failed on init (may still work): %s", e)
    return build("youtube", "v3", credentials=creds)


# ─── Channel ─────────────────────────────────────────────────────────────────


def get_channel_info(channel_id: str) -> dict[str, Any]:
    """Get detailed information about a YouTube channel."""
    youtube = get_youtube_service()
    try:
        request = youtube.channels().list(
            part="snippet,statistics,status,brandingSettings",
            id=channel_id,
        )
        response = request.execute()
        if not response.get("items"):
            raise ValueError(f"Channel '{channel_id}' not found")
        return _simplify_channel(response["items"][0])
    except HttpError as e:
        logger.error("YouTube API error: %s", e)
        raise


def _simplify_channel(raw: dict) -> dict[str, Any]:
    snippet = raw.get("snippet", {})
    stats = raw.get("statistics", {})
    return {
        "id": raw["id"],
        "title": snippet.get("title"),
        "description": snippet.get("description"),
        "custom_url": snippet.get("customUrl"),
        "published_at": snippet.get("publishedAt"),
        "country": snippet.get("country"),
        "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "view_count": int(stats.get("viewCount", 0)),
        "privacy_status": raw.get("status", {}).get("privacyStatus"),
    }


# ─── Videos — list ───────────────────────────────────────────────────────────


def list_channel_videos(channel_id: str, max_results: int = 50) -> list[dict[str, Any]]:
    """List all videos from a channel (published, scheduled, unlisted)."""
    youtube = get_youtube_service()

    # Get uploads playlist ID
    channel_resp = youtube.channels().list(
        part="contentDetails", id=channel_id
    ).execute()
    if not channel_resp.get("items"):
        raise ValueError(f"Channel '{channel_id}' not found")

    uploads_id = channel_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Paginate through playlist
    videos = []
    next_page = None
    while True:
        playlist_resp = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_id,
            maxResults=min(max_results, 50),
            pageToken=next_page,
        ).execute()

        for item in playlist_resp.get("items", []):
            vid = {"video_id": item["contentDetails"]["videoId"]}
            vid.update(_simplify_playlist_item(item["snippet"]))
            videos.append(vid)

        next_page = playlist_resp.get("nextPageToken")
        if not next_page or len(videos) >= max_results:
            break

    return videos[:max_results]


def _simplify_playlist_item(snippet: dict) -> dict:
    return {
        "title": snippet.get("title"),
        "description": snippet.get("description"),
        "published_at": snippet.get("videoPublishedAt") or snippet.get("publishedAt"),
        "thumbnails": snippet.get("thumbnails"),
        "channel_id": snippet.get("channelId"),
    }


# ─── Video — detail ──────────────────────────────────────────────────────────


def get_video_details(video_id: str) -> dict[str, Any]:
    """Get detailed information about a specific video."""
    youtube = get_youtube_service()
    try:
        request = youtube.videos().list(
            part="snippet,statistics,status",
            id=video_id,
        )
        response = request.execute()
        if not response.get("items"):
            raise ValueError(f"Video '{video_id}' not found")
        return _simplify_video(response["items"][0])
    except HttpError as e:
        logger.error("YouTube API error: %s", e)
        raise


def get_video_stats(video_id: str) -> dict[str, Any]:
    """Get statistics for a specific video (views, likes, comments)."""
    youtube = get_youtube_service()
    try:
        request = youtube.videos().list(part="statistics", id=video_id)
        response = request.execute()
        if not response.get("items"):
            raise ValueError(f"Video '{video_id}' not found")
        stats = response["items"][0].get("statistics", {})
        return {
            "video_id": video_id,
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        }
    except HttpError as e:
        logger.error("YouTube API error: %s", e)
        raise


def _simplify_video(raw: dict) -> dict[str, Any]:
    snippet = raw.get("snippet", {})
    stats = raw.get("statistics", {})
    status = raw.get("status", {})
    return {
        "video_id": raw["id"],
        "title": snippet.get("title"),
        "description": snippet.get("description"),
        "tags": snippet.get("tags", []),
        "category_id": snippet.get("categoryId"),
        "published_at": snippet.get("publishedAt"),
        "channel_id": snippet.get("channelId"),
        "channel_title": snippet.get("channelTitle"),
        "thumbnails": snippet.get("thumbnails"),
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "privacy_status": status.get("privacyStatus"),
        "embeddable": status.get("embeddable"),
        "license": status.get("license"),
    }


# ─── Upload ──────────────────────────────────────────────────────────────────


def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "22",
    privacy_status: str = "private",
    scheduled_at: str | None = None,
) -> dict[str, Any]:
    """Upload a video to YouTube.

    Args:
        video_path: Local path to the video file.
        title: Video title (max 100 chars).
        description: Video description.
        tags: List of tags.
        category_id: YouTube category ID (default: 22 = Science & Technology).
        privacy_status: 'public', 'unlisted', or 'private'.
        scheduled_at: ISO datetime for scheduled publishing (requires public access).

    Returns:
        Dict with video_id, video_url, and other metadata.
    """
    # Title max 100 chars
    if len(title) > 100:
        title = title[:100]

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }

    # Scheduled publishing
    if scheduled_at:
        body["status"]["publishAt"] = scheduled_at

    youtube = get_youtube_service()
    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=video_path,
        )
        response = request.execute()
        video_id = response["id"]
        logger.info("Video uploaded: id=%s title=%s", video_id, title)
        return {
            "success": True,
            "video_id": video_id,
            "video_url": f"https://youtu.be/{video_id}",
            "title": title,
        }
    except HttpError as e:
        logger.error("YouTube upload error: %s", e)
        raise


# ─── Metadata update ─────────────────────────────────────────────────────────


def update_video_metadata(
    video_id: str,
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    category_id: str | None = None,
) -> bool:
    """Update a video's title, description, tags, or category."""
    youtube = get_youtube_service()
    try:
        # Fetch current snippet
        video_resp = youtube.videos().list(part="snippet", id=video_id).execute()
        if not video_resp.get("items"):
            raise ValueError(f"Video '{video_id}' not found")

        current = video_resp["items"][0]["snippet"]
        updated_snippet = {
            "categoryId": category_id or current.get("categoryId", "22"),
            "title": title if title is not None else current.get("title", ""),
            "description": description if description is not None else current.get("description", ""),
        }
        if tags is not None:
            updated_snippet["tags"] = tags
        elif "tags" in current:
            updated_snippet["tags"] = current["tags"]

        youtube.videos().update(
            part="snippet",
            body={"id": video_id, "snippet": updated_snippet},
        ).execute()

        logger.info("Video metadata updated: id=%s", video_id)
        return True
    except HttpError as e:
        logger.error("YouTube metadata update error: %s", e)
        raise


# ─── Thumbnail ───────────────────────────────────────────────────────────────


def set_video_thumbnail(video_id: str, thumbnail_path: str) -> bool:
    """Set a custom thumbnail for a video.

    The thumbnail file must be a JPEG or PNG under 2 MB.
    """
    youtube = get_youtube_service()
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=thumbnail_path,
        ).execute()
        logger.info("Thumbnail updated: video_id=%s", video_id)
        return True
    except HttpError as e:
        logger.error("Thumbnail update error: %s", e)
        raise


# ─── Comment ─────────────────────────────────────────────────────────────────


def post_comment(video_id: str, text: str) -> bool:
    """Post a top-level comment on a video."""
    youtube = get_youtube_service()
    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {"textOriginal": text},
            },
        },
    }
    try:
        youtube.commentThreads().insert(part="snippet", body=body).execute()
        logger.info("Comment posted: video_id=%s", video_id)
        return True
    except HttpError as e:
        logger.error("Comment post error: %s", e)
        raise


# ─── Transcript ──────────────────────────────────────────────────────────────


def get_transcript(video_id: str) -> list[dict[str, Any]]:
    """Get the transcript/captions for a video."""
    try:
        transcript_list = YouTubeTranscriptApi.fetch(video_id)
        return [
            {"text": entry.get("text", ""), "start": entry.get("start", 0), "duration": entry.get("duration", 0)}
            for entry in transcript_list
        ]
    except Exception as e:
        logger.warning("Transcript not available for %s: %s", video_id, e)
        return []


# ─── Playlist ────────────────────────────────────────────────────────────────


def list_playlists(channel_id: str, max_results: int = 50) -> list[dict[str, Any]]:
    """List all playlists from a channel."""
    youtube = get_youtube_service()
    try:
        playlists = []
        next_page = None
        while True:
            resp = youtube.playlists().list(
                part="snippet,contentDetails",
                channelId=channel_id,
                maxResults=min(max_results, 50),
                pageToken=next_page,
            ).execute()

            for item in resp.get("items", []):
                playlists.append({
                    "playlist_id": item["id"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"].get("description", ""),
                    "item_count": item["contentDetails"].get("itemCount", 0),
                    "published_at": item["snippet"]["publishedAt"],
                    "thumbnails": item["snippet"].get("thumbnails"),
                })

            next_page = resp.get("nextPageToken")
            if not next_page or len(playlists) >= max_results:
                break

        return playlists[:max_results]
    except HttpError as e:
        logger.error("Playlist list error: %s", e)
        raise
