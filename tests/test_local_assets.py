"""Test local assets management."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from auto_video.core.video import Asset, LocalAssetsManager


def test_asset_creation():
    """Test Asset dataclass creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.mp4"
        asset = Asset(path, "video", 10.5)

        assert asset.path == path
        assert asset.type == "video"
        assert asset.duration == 10.5


def test_asset_with_video_type():
    """Test Asset with video type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "video.mov"
        asset = Asset(path, "video", 15.0)

        assert asset.type == "video"
        assert isinstance(asset.duration, float)
        assert asset.duration > 0


def test_asset_with_image_type():
    """Test Asset with image type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "image.jpg"
        asset = Asset(path, "image", None)

        assert asset.type == "image"
        assert asset.duration is None


def test_local_assets_manager_initialization():
    """Test LocalAssetsManager initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        manager = LocalAssetsManager(path, include_subdirs=True)

        assert manager.path == path
        assert manager.include_subdirs is True
        assert manager._assets is None
        assert manager.video_extensions == {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"}


def test_scan_assets_returns_list():
    """Test scan_assets() returns list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        manager = LocalAssetsManager(path, include_subdirs=False)

        assets = manager.scan_assets()

        assert isinstance(assets, list)
        assert manager._assets is not None


def test_scan_assets_detects_videos():
    """Test scan_assets() detects videos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "video1.mp4").touch()
        (path / "video2.mov").touch()
        (path / "video3.avi").touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "10.0"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=False)
            assets = manager.scan_assets()

            assert len(assets) == 3
            assert all(a.type == "video" for a in assets)


def test_scan_assets_detects_images():
    """Test scan_assets() detects images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "image1.jpg").touch()
        (path / "image2.png").touch()
        (path / "image3.gif").touch()

        manager = LocalAssetsManager(path, include_subdirs=False)
        assets = manager.scan_assets()

        assert len(assets) == 3
        assert all(a.type == "image" for a in assets)
        assert all(a.duration is None for a in assets)


def test_scan_assets_with_subdirs():
    """Test scan_assets() with subdirs when include_subdirs=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        subdir = path / "subdir"
        subdir.mkdir()

        (path / "root.mp4").touch()
        (subdir / "nested.jpg").touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "10.0"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=True)
            assets = manager.scan_assets()

            assert len(assets) == 2


def test_scan_assets_without_subdirs():
    """Test scan_assets() without subdirs when include_subdirs=False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        subdir = path / "subdir"
        subdir.mkdir()

        (path / "root.mp4").touch()
        (subdir / "nested.jpg").touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "10.0"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=False)
            assets = manager.scan_assets()

            assert len(assets) == 1
            assert assets[0].path.name == "root.mp4"


def test_get_random_sequence_returns_assets():
    """Test get_random_sequence() returns assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "video.mp4").touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "10.0"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=False)
            assets = manager.get_random_sequence(15.0)

            assert isinstance(assets, list)
            assert len(assets) > 0


def test_get_random_sequence_repeats_assets():
    """Test get_random_sequence() repeats assets if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "video.mp4").touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "5.0"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=False)
            assets = manager.get_random_sequence(20.0)

            assert len(assets) >= 4


def test_get_random_sequence_distributes_evenly():
    """Test get_random_sequence() distributes evenly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "video.mp4").touch()
        (path / "image.jpg").touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "5.0"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=False)
            assets = manager.get_random_sequence(30.0)

            video_count = sum(1 for a in assets if a.type == "video")
            image_count = sum(1 for a in assets if a.type == "image")

            assert video_count >= 1
            assert image_count >= 1


def test_prepare_clips_returns_paths():
    """Test prepare_clips() returns paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "video.mp4").touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "10.0"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=False)
            assets = manager.scan_assets()
            clips = manager.prepare_clips(assets)

            assert isinstance(clips, list)
            assert len(clips) == 1
            assert isinstance(clips[0], Path)


def test_prepare_clips_creates_ken_burns():
    """Test prepare_clips() creates Ken Burns effect for images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "image.jpg").touch()

        manager = LocalAssetsManager(path, include_subdirs=False)
        assets = manager.scan_assets()

        with patch.object(subprocess, "run"):
            clips = manager.prepare_clips(assets)

            assert len(clips) == 1
            assert clips[0].name.startswith("ken_burns_")


def test_prepare_clips_returns_videos_as_is():
    """Test prepare_clips() returns videos as-is."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        video_path = path / "video.mp4"
        video_path.touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "10.0"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=False)
            assets = manager.scan_assets()
            clips = manager.prepare_clips(assets)

            assert len(clips) == 1
            assert clips[0] == video_path


def test_local_assets_manager_with_invalid_files():
    """Test LocalAssetsManager ignores invalid files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "document.txt").touch()
        (path / "data.json").touch()
        (path / "script.py").touch()

        manager = LocalAssetsManager(path, include_subdirs=False)
        assets = manager.scan_assets()

        assert len(assets) == 0


def test_get_video_duration_timeout():
    """Test _get_video_duration handles timeout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        video_path = path / "video.mp4"
        video_path.touch()

        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("ffprobe", 10)):
            manager = LocalAssetsManager(path, include_subdirs=False)
            duration = manager._get_video_duration(video_path)

            assert duration == 0.0


def test_get_video_duration_invalid_output():
    """Test _get_video_duration handles invalid output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        video_path = path / "video.mp4"
        video_path.touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "invalid"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=False)
            duration = manager._get_video_duration(video_path)

            assert duration == 0.0


def test_get_random_sequence_empty_assets():
    """Test get_random_sequence with no assets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        manager = LocalAssetsManager(path, include_subdirs=False)

        assets = manager.get_random_sequence(10.0)

        assert assets == []


def test_scan_assets_mixed_content():
    """Test scan_assets with mixed video and image content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "video1.mp4").touch()
        (path / "video2.mov").touch()
        (path / "image1.jpg").touch()
        (path / "image2.png").touch()
        (path / "document.txt").touch()

        with patch.object(subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "10.0"
            mock_run.return_value = mock_result

            manager = LocalAssetsManager(path, include_subdirs=False)
            assets = manager.scan_assets()

            assert len(assets) == 4
            video_count = sum(1 for a in assets if a.type == "video")
            image_count = sum(1 for a in assets if a.type == "image")
            assert video_count == 2
            assert image_count == 2
