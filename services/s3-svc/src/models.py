"""S3 content type detection and key generation.

Mirrors the backend's S3Data logic: files are organized into
prefix folders by their content type (images/, audio/, videos/,
json/, data/).
"""

from enum import Enum
from typing import ClassVar


class S3ContentTypeEnum(Enum):
    PNG = "image/png"
    JPEG = "image/jpeg"
    JSON = "application/json"
    PICKLE = "application/octet-stream"
    TXT = "text/plain"
    MP3 = "audio/mpeg"
    WAV = "audio/wav"
    MP4 = "video/mp4"
    OGG = "audio/ogg"
    WEBM = "video/webm"
    M4A = "audio/mp4"
    FLAC = "audio/flac"
    AAC = "audio/aac"
    OPUS = "audio/opus"
    AIFF = "audio/aiff"
    WMA = "audio/x-ms-wma"


EXTENSION_MAP: dict[str, S3ContentTypeEnum] = {
    "png": S3ContentTypeEnum.PNG,
    "jpg": S3ContentTypeEnum.JPEG,
    "jpeg": S3ContentTypeEnum.JPEG,
    "mp3": S3ContentTypeEnum.MP3,
    "wav": S3ContentTypeEnum.WAV,
    "ogg": S3ContentTypeEnum.OGG,
    "json": S3ContentTypeEnum.JSON,
    "pickle": S3ContentTypeEnum.PICKLE,
    "txt": S3ContentTypeEnum.TXT,
    "mp4": S3ContentTypeEnum.MP4,
    "webm": S3ContentTypeEnum.WEBM,
    "m4a": S3ContentTypeEnum.M4A,
    "flac": S3ContentTypeEnum.FLAC,
    "aac": S3ContentTypeEnum.AAC,
    "opus": S3ContentTypeEnum.OPUS,
    "aiff": S3ContentTypeEnum.AIFF,
    "wma": S3ContentTypeEnum.WMA,
}

_IMAGE_TYPES = {S3ContentTypeEnum.PNG, S3ContentTypeEnum.JPEG}
_AUDIO_TYPES = {
    S3ContentTypeEnum.MP3, S3ContentTypeEnum.WAV,
    S3ContentTypeEnum.OGG, S3ContentTypeEnum.M4A,
    S3ContentTypeEnum.FLAC, S3ContentTypeEnum.AAC,
    S3ContentTypeEnum.OPUS, S3ContentTypeEnum.AIFF,
    S3ContentTypeEnum.WMA,
}
_VIDEO_TYPES = {S3ContentTypeEnum.MP4, S3ContentTypeEnum.WEBM}


def detect_content_type(name: str) -> S3ContentTypeEnum:
    """Detect content type from filename extension.

    Raises ValueError if the extension is not supported.
    """
    if "." not in name:
        raise ValueError(f"Unsupported file extension: {name}")
    extension = name.rsplit(".", 1)[-1].lower()
    content_type = EXTENSION_MAP.get(extension)
    if content_type is None:
        raise ValueError(f"Unsupported file extension: {name}")
    return content_type


def s3_key_for(name: str, key: str | None = None) -> str:
    """Generate the S3 object key for a file based on its content type.

    Files are organized into prefix folders:
      images/  — PNG, JPEG
      audio/   — MP3, WAV, OGG, M4A, FLAC, AAC, OPUS, AIFF, WMA
      videos/  — MP4, WEBM
      json/    — JSON
      data/    — PICKLE, TXT

    An optional ``key`` adds a subfolder (e.g. ``images/branding/logo.png``).
    """
    content_type = detect_content_type(name)

    if content_type in _IMAGE_TYPES:
        prefix = "images"
    elif content_type in _AUDIO_TYPES:
        prefix = "audio"
    elif content_type in _VIDEO_TYPES:
        prefix = "videos"
    elif content_type == S3ContentTypeEnum.JSON:
        prefix = "json"
    elif content_type in {S3ContentTypeEnum.PICKLE, S3ContentTypeEnum.TXT}:
        prefix = "data"
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

    if key:
        return f"{prefix}/{key}/{name}"
    return f"{prefix}/{name}"


def s3_data_from_path(s3_path: str) -> dict:
    """Parse an S3 object key into {key, name, content_type}.

    Example: 'images/branding/logo.png' → {
        'key': 'images/branding/logo.png',
        'name': 'logo.png',
        'content_type': 'image/png'
    }
    """
    name = s3_path.rsplit("/", 1)[-1]
    return {
        "key": s3_path,
        "name": name,
        "content_type": detect_content_type(name).value,
    }
