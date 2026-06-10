"""Tests for atlas models — content type detection and S3 key generation."""

import pytest

from models import S3ContentTypeEnum, detect_content_type, s3_key_for


class TestDetectContentType:
    """Content type detection from filename extension."""

    def test_detects_png(self):
        assert detect_content_type("logo.png") == S3ContentTypeEnum.PNG

    def test_detects_jpg(self):
        assert detect_content_type("photo.jpg") == S3ContentTypeEnum.JPEG

    def test_detects_jpeg(self):
        assert detect_content_type("image.jpeg") == S3ContentTypeEnum.JPEG

    def test_detects_mp3(self):
        assert detect_content_type("song.mp3") == S3ContentTypeEnum.MP3

    def test_detects_wav(self):
        assert detect_content_type("audio.wav") == S3ContentTypeEnum.WAV

    def test_detects_ogg(self):
        assert detect_content_type("audio.ogg") == S3ContentTypeEnum.OGG

    def test_detects_m4a(self):
        assert detect_content_type("audio.m4a") == S3ContentTypeEnum.M4A

    def test_detects_flac(self):
        assert detect_content_type("audio.flac") == S3ContentTypeEnum.FLAC

    def test_detects_aac(self):
        assert detect_content_type("audio.aac") == S3ContentTypeEnum.AAC

    def test_detects_opus(self):
        assert detect_content_type("audio.opus") == S3ContentTypeEnum.OPUS

    def test_detects_aiff(self):
        assert detect_content_type("audio.aiff") == S3ContentTypeEnum.AIFF

    def test_detects_wma(self):
        assert detect_content_type("audio.wma") == S3ContentTypeEnum.WMA

    def test_detects_mp4(self):
        assert detect_content_type("video.mp4") == S3ContentTypeEnum.MP4

    def test_detects_webm(self):
        assert detect_content_type("video.webm") == S3ContentTypeEnum.WEBM

    def test_detects_json(self):
        assert detect_content_type("data.json") == S3ContentTypeEnum.JSON

    def test_detects_pickle(self):
        assert detect_content_type("model.pickle") == S3ContentTypeEnum.PICKLE

    def test_detects_txt(self):
        assert detect_content_type("notes.txt") == S3ContentTypeEnum.TXT

    def test_raises_on_unknown_extension(self):
        with pytest.raises(ValueError, match="Unsupported file extension"):
            detect_content_type("file.xyz")

    def test_raises_on_no_extension(self):
        with pytest.raises(ValueError):
            detect_content_type("README")

    def test_is_case_insensitive(self):
        assert detect_content_type("Photo.JPG") == S3ContentTypeEnum.JPEG
        assert detect_content_type("Song.MP3") == S3ContentTypeEnum.MP3


class TestS3KeyGeneration:
    """S3 key generation groups files by content type into prefix folders."""

    def test_image_key_no_key(self):
        """Images go under images/."""
        assert s3_key_for("logo.png") == "images/logo.png"

    def test_image_key_with_key(self):
        """Images with category key go under images/{key}/."""
        assert s3_key_for("logo.png", key="branding") == "images/branding/logo.png"

    def test_image_key_with_nested_key(self):
        assert s3_key_for("thumb.jpg", key="YouTubeVideo#abc") == "images/YouTubeVideo#abc/thumb.jpg"

    def test_audio_key_no_key(self):
        """Audio files go under audio/."""
        assert s3_key_for("song.mp3") == "audio/song.mp3"

    def test_audio_key_with_key(self):
        assert s3_key_for("song.mp3", key="podcast") == "audio/podcast/song.mp3"

    def test_wav_audio_key(self):
        assert s3_key_for("recording.wav") == "audio/recording.wav"

    def test_ogg_audio_key(self):
        assert s3_key_for("voice.ogg") == "audio/voice.ogg"

    def test_m4a_audio_key(self):
        assert s3_key_for("voice.m4a") == "audio/voice.m4a"

    def test_flac_audio_key(self):
        assert s3_key_for("voice.flac") == "audio/voice.flac"

    def test_aac_audio_key(self):
        assert s3_key_for("voice.aac") == "audio/voice.aac"

    def test_opus_audio_key(self):
        assert s3_key_for("voice.opus") == "audio/voice.opus"

    def test_aiff_audio_key(self):
        assert s3_key_for("voice.aiff") == "audio/voice.aiff"

    def test_wma_audio_key(self):
        assert s3_key_for("voice.wma") == "audio/voice.wma"

    def test_video_key_no_key(self):
        """Video files go under videos/."""
        assert s3_key_for("clip.mp4") == "videos/clip.mp4"

    def test_video_key_with_key(self):
        assert s3_key_for("clip.mp4", key="tutorials") == "videos/tutorials/clip.mp4"

    def test_webm_video_key(self):
        assert s3_key_for("clip.webm") == "videos/clip.webm"

    def test_json_key(self):
        """JSON files go under json/."""
        assert s3_key_for("config.json") == "json/config.json"

    def test_json_key_with_key(self):
        assert s3_key_for("config.json", key="app") == "json/app/config.json"

    def test_pickle_key(self):
        """Pickle files go under data/."""
        assert s3_key_for("model.pickle") == "data/model.pickle"

    def test_pickle_key_with_key(self):
        assert s3_key_for("model.pickle", key="ml") == "data/ml/model.pickle"

    def test_txt_key(self):
        """TXT files go under data/."""
        assert s3_key_for("notes.txt") == "data/notes.txt"

    def test_raises_on_unknown(self):
        with pytest.raises(ValueError, match="Unsupported file extension"):
            s3_key_for("file.xyz")
