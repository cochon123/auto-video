"""Test YouTube uploader."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from auto_video.upload.youtube import (  # type: ignore
    QuotaInfo,
    UploadResult,
    YouTubeUploader,
    YouTubeUploadError,
)


def test_upload_result_dataclass() -> None:
    """Test UploadResult dataclass."""
    result = UploadResult(
        video_id="abc123", url="https://youtube.com/watch?v=abc123", status="uploaded"
    )

    assert result.video_id == "abc123"
    assert result.url == "https://youtube.com/watch?v=abc123"
    assert result.status == "uploaded"


def test_quota_info_dataclass() -> None:
    """Test QuotaInfo dataclass."""
    quota = QuotaInfo(uploaded=10, remaining=9990, limit=10000)

    assert quota.uploaded == 10
    assert quota.remaining == 9990
    assert quota.limit == 10000


def test_youtube_uploader_initialization(tmp_path: Path) -> None:
    """Test YouTubeUploader initialization."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}")

    uploader = YouTubeUploader(credentials_file)

    assert uploader.credentials_path == credentials_file
    assert uploader._service is None
    assert uploader._credentials is None


def test_youtube_uploader_authenticate_missing_credentials(tmp_path: Path) -> None:
    """Test YouTubeUploader.authenticate raises FileNotFoundError for missing credentials."""
    non_existent = tmp_path / "nonexistent.json"
    uploader = YouTubeUploader(non_existent)

    with pytest.raises(FileNotFoundError, match="Credentials file not found"):
        uploader.authenticate()


def test_youtube_uploader_authenticate_existing_token(tmp_path: Path) -> None:
    """Test YouTubeUploader.authenticate with existing token."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text(
        '{"installed":{"client_id":"test","project_id":"test","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token"}}'
    )

    token_file = tmp_path / "token.json"
    token_file.write_text(
        '{"token":"test","refresh_token":"test","client_id":"test","client_secret":"test","scopes":["https://www.googleapis.com/auth/youtube.upload"],"expiry":"2099-01-01T00:00:00Z"}'
    )

    with patch("auto_video.upload.youtube.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        uploader = YouTubeUploader(credentials_file)
        uploader.authenticate()

        assert uploader._service is not None
        mock_build.assert_called_once()


def test_youtube_uploader_upload_missing_video(tmp_path: Path) -> None:
    """Test YouTubeUploader.upload raises FileNotFoundError for missing video."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}")
    uploader = YouTubeUploader(credentials_file)

    non_existent_video = tmp_path / "nonexistent.mp4"

    with patch.object(uploader, "_ensure_authenticated"):
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            uploader.upload(
                non_existent_video,
                title="Test",
                description="Test",
                tags=["test"],
                privacy="unlisted",
            )


def test_youtube_uploader_upload_with_mock(tmp_path: Path) -> None:
    """Test YouTubeUploader.upload with mock service."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}")
    uploader = YouTubeUploader(credentials_file)

    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake_video_data")

    mock_service = MagicMock()
    mock_request = MagicMock()
    mock_request.next_chunk.return_value = (None, {"id": "test123"})
    mock_service.videos.return_value.insert.return_value = mock_request
    uploader._service = mock_service

    result = uploader.upload(
        video_file,
        title="Test Video",
        description="Test Description",
        tags=["test"],
        privacy="unlisted",
    )

    assert result.video_id == "test123"
    assert result.url == "https://www.youtube.com/watch?v=test123"
    assert result.status == "uploaded"


def test_youtube_uploader_upload_with_progress_callback(tmp_path: Path) -> None:
    """Test YouTubeUploader.upload with progress callback."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}")
    uploader = YouTubeUploader(credentials_file)

    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake_video_data")

    progress_calls = []

    def progress_callback(progress: int, total: int) -> None:
        progress_calls.append((progress, total))

    mock_service = MagicMock()
    mock_request = MagicMock()
    mock_status = Mock()
    mock_status.resumable_progress = 500
    mock_status.total_size = 1000
    mock_request.next_chunk.side_effect = [
        (mock_status, None),
        (None, {"id": "test123"}),
    ]
    mock_service.videos.return_value.insert.return_value = mock_request
    uploader._service = mock_service

    result = uploader.upload(
        video_file,
        title="Test Video",
        description="Test Description",
        tags=["test"],
        privacy="unlisted",
        progress_callback=progress_callback,
    )

    assert len(progress_calls) == 1
    assert progress_calls[0] == (500, 1000)
    assert result.video_id == "test123"


def test_youtube_uploader_set_thumbnail_missing_file(tmp_path: Path) -> None:
    """Test YouTubeUploader.set_thumbnail raises FileNotFoundError for missing thumbnail."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}")
    uploader = YouTubeUploader(credentials_file)

    non_existent_thumbnail = tmp_path / "nonexistent.jpg"

    with patch.object(uploader, "_ensure_authenticated"):
        with pytest.raises(FileNotFoundError, match="Thumbnail file not found"):
            uploader.set_thumbnail("video123", non_existent_thumbnail)


def test_youtube_uploader_set_thumbnail_with_mock(tmp_path: Path) -> None:
    """Test YouTubeUploader.set_thumbnail with mock service."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}")
    uploader = YouTubeUploader(credentials_file)

    thumbnail_file = tmp_path / "thumbnail.jpg"
    thumbnail_file.write_bytes(b"fake_thumbnail_data")

    mock_service = MagicMock()
    mock_service.thumbnails.return_value.set.return_value.execute.return_value = None
    uploader._service = mock_service

    uploader.set_thumbnail("video123", thumbnail_file)

    mock_service.thumbnails.return_value.set.assert_called_once()


def test_youtube_uploader_get_quota_usage_with_mock(tmp_path: Path) -> None:
    """Test YouTubeUploader.get_quota_usage with mock service."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}")
    uploader = YouTubeUploader(credentials_file)

    mock_service = MagicMock()
    mock_service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "1"}, {"id": "2"}],
        "nextPageToken": None,
    }
    uploader._service = mock_service

    quota = uploader.get_quota_usage()

    assert quota.uploaded == 2
    assert quota.remaining == 9998
    assert quota.limit == 10000


def test_youtube_uploader_get_quota_usage_with_pagination(tmp_path: Path) -> None:
    """Test YouTubeUploader.get_quota_usage with pagination."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("{}")
    uploader = YouTubeUploader(credentials_file)

    mock_service = MagicMock()
    mock_videos = MagicMock()
    mock_request = MagicMock()

    mock_request.execute.side_effect = [
        {"items": [{"id": str(i)} for i in range(50)], "nextPageToken": "token1"},
        {"items": [{"id": str(i)} for i in range(50, 100)], "nextPageToken": None},
    ]
    mock_videos.list.return_value = mock_request
    mock_service.videos.return_value = mock_videos
    uploader._service = mock_service

    quota = uploader.get_quota_usage()

    assert quota.uploaded == 100
    assert quota.remaining == 9900
    assert quota.limit == 10000


def test_youtube_upload_error() -> None:
    """Test YouTubeUploadError can be raised and caught."""
    with pytest.raises(YouTubeUploadError):
        raise YouTubeUploadError("Test error")

    try:
        raise YouTubeUploadError("Test error")
    except YouTubeUploadError as e:
        assert str(e) == "Test error"
