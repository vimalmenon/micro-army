"""Tests for S3Client — all AWS calls mocked."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from config import Settings
from s3_client import S3Client


@pytest.fixture
def mock_boto3():
    """Mock boto3.client('s3') so no real AWS calls are made."""
    with patch("s3_client.boto3") as mock:
        s3_mock = MagicMock()
        mock.client.return_value = s3_mock
        yield s3_mock


@pytest.fixture
def client(mock_boto3):
    """S3Client with mocked boto3 and a known bucket."""
    import s3_client as s3_mod
    mock_settings = MagicMock()
    mock_settings.aws_bucket = "test-bucket"
    mock_settings.aws_region = "us-east-1"
    mock_settings.aws_access_key_id = "test-key"
    mock_settings.aws_secret_access_key = "test-secret"
    with patch.object(s3_mod, "settings", mock_settings):
        S3Client._instance = None
        yield S3Client()


class TestS3ClientUpload:
    def test_upload_bytes(self, client, mock_boto3):
        result = client.upload_bytes(b"hello world", "notes.txt")
        assert result is True
        mock_boto3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="data/notes.txt",
            Body=b"hello world",
            ContentType="text/plain",
        )

    def test_upload_bytes_with_key(self, client, mock_boto3):
        result = client.upload_bytes(b"data", "config.json", key="app")
        assert result is True
        mock_boto3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="json/app/config.json",
            Body=b"data",
            ContentType="application/json",
        )

    def test_upload_returns_false_on_client_error(self, client, mock_boto3):
        mock_boto3.put_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "PutObject"
        )
        result = client.upload_bytes(b"data", "file.txt")
        assert result is False

    def test_upload_image_sets_correct_content_type(self, client, mock_boto3):
        client.upload_bytes(b"imgdata", "photo.png")
        mock_boto3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="images/photo.png",
            Body=b"imgdata",
            ContentType="image/png",
        )

    def test_upload_audio_sets_correct_content_type(self, client, mock_boto3):
        client.upload_bytes(b"audiodata", "song.mp3")
        mock_boto3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="audio/song.mp3",
            Body=b"audiodata",
            ContentType="audio/mpeg",
        )

    def test_upload_video_sets_correct_content_type(self, client, mock_boto3):
        client.upload_bytes(b"videodata", "clip.mp4")
        mock_boto3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="videos/clip.mp4",
            Body=b"videodata",
            ContentType="video/mp4",
        )


class TestS3ClientDownload:
    def test_get_bytes(self, client, mock_boto3):
        mock_boto3.get_object.return_value = {"Body": MagicMock(read=lambda: b"filecontent")}
        result = client.get_bytes("notes.txt")
        assert result == b"filecontent"
        mock_boto3.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="data/notes.txt"
        )

    def test_get_bytes_with_key(self, client, mock_boto3):
        mock_boto3.get_object.return_value = {"Body": MagicMock(read=lambda: b"data")}
        result = client.get_bytes("config.json", key="app")
        assert result == b"data"
        mock_boto3.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="json/app/config.json"
        )

    def test_get_bytes_raises_on_client_error(self, client, mock_boto3):
        mock_boto3.get_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "GetObject"
        )
        with pytest.raises(RuntimeError, match="S3 error"):
            client.get_bytes("missing.txt")


class TestS3ClientDelete:
    def test_delete(self, client, mock_boto3):
        client.delete("notes.txt")
        mock_boto3.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="data/notes.txt"
        )

    def test_delete_with_key(self, client, mock_boto3):
        client.delete("photo.png", key="branding")
        mock_boto3.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="images/branding/photo.png"
        )

    def test_delete_raises_on_client_error(self, client, mock_boto3):
        mock_boto3.delete_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Error"}}, "DeleteObject"
        )
        with pytest.raises(RuntimeError, match="S3 error"):
            client.delete("file.txt")

    def test_delete_silent_on_not_found(self, client, mock_boto3):
        mock_boto3.delete_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "DeleteObject"
        )
        # Should not raise — 404 on delete is idempotent
        result = client.delete("missing.txt", silent=True)
        assert result is True


class TestS3ClientList:
    def test_list_empty(self, client, mock_boto3):
        mock_boto3.list_objects_v2.return_value = {}
        result = client.list_items()
        assert result == []

    def test_list_with_prefix(self, client, mock_boto3):
        mock_boto3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "images/logo.png"},
                {"Key": "images/photo.jpg"},
            ]
        }
        result = client.list_items(prefix="images/")
        assert len(result) == 2
        assert result[0] == {"key": "images/logo.png", "name": "logo.png", "content_type": "image/png"}
        assert result[1] == {"key": "images/photo.jpg", "name": "photo.jpg", "content_type": "image/jpeg"}
        mock_boto3.list_objects_v2.assert_called_once_with(
            Bucket="test-bucket", Prefix="images/", MaxKeys=1000
        )
