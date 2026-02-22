"""Test storage setup wizard."""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from auto_video.config.schema import StorageConfig
from auto_video.ui.setup import StorageSetupResult, StorageSetupWizard


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(force_terminal=True, width=100)


@pytest.fixture
def wizard(mock_console):
    """Create a wizard instance with mock console."""
    return StorageSetupWizard(mock_console)


def test_storage_setup_wizard_initialization(wizard):
    """Test wizard initialization."""
    assert wizard.console is not None


def test_storage_setup_result_dataclass():
    """Test StorageSetupResult dataclass."""
    config = StorageConfig(
        videos_path=Path("/tmp/videos"),
        temp_path=Path("/tmp/temp"),
        keep_temp=True,
    )

    result = StorageSetupResult(config=config, success=True, message="Success")

    assert result.config == config
    assert result.success is True
    assert result.message == "Success"


def test_ask_save_videos_yes(wizard):
    """Test asking to save videos with yes."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        result = wizard._ask_save_videos()
        assert result is True


def test_ask_save_videos_no(wizard):
    """Test asking to save videos with no."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        result = wizard._ask_save_videos()
        assert result is False


def test_ask_videos_path_default(wizard):
    """Test asking for videos path with default."""
    default_path = str(Path.home() / "Videos" / "auto-videos")
    with patch("auto_video.ui.setup.Prompt.ask", return_value=default_path):
        with patch.object(wizard, "_create_directory_if_needed"):
            result = wizard._ask_videos_path()
            assert result == Path.home() / "Videos" / "auto-videos"


def test_ask_videos_path_custom(wizard):
    """Test asking for videos path with custom path."""
    custom_path = "/custom/videos/path"

    with patch("auto_video.ui.setup.Prompt.ask", return_value=custom_path):
        with patch.object(wizard, "_create_directory_if_needed"):
            result = wizard._ask_videos_path()
            assert result == Path(custom_path).expanduser()


def test_ask_keep_temp_yes(wizard):
    """Test asking to keep temp files with yes."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=True):
        result = wizard._ask_keep_temp()
        assert result is True


def test_ask_keep_temp_no(wizard):
    """Test asking to keep temp files with no."""
    with patch("auto_video.ui.setup.Confirm.ask", return_value=False):
        result = wizard._ask_keep_temp()
        assert result is False


def test_ask_temp_path_default(wizard):
    """Test asking for temp path with default."""
    default_path = str(Path.home() / ".cache" / "auto-video" / "temp")
    with patch("auto_video.ui.setup.Prompt.ask", return_value=default_path):
        with patch.object(wizard, "_create_directory_if_needed"):
            result = wizard._ask_temp_path()
            assert result == Path.home() / ".cache" / "auto-video" / "temp"


def test_ask_temp_path_custom(wizard):
    """Test asking for temp path with custom path."""
    custom_path = "/custom/temp/path"

    with patch("auto_video.ui.setup.Prompt.ask", return_value=custom_path):
        with patch.object(wizard, "_create_directory_if_needed"):
            result = wizard._ask_temp_path()
            assert result == Path(custom_path).expanduser()


def test_create_directory_if_needed_exists(wizard):
    """Test creating directory when it already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "existing_dir"
        path.mkdir()

        wizard._create_directory_if_needed(path, "Test")


def test_create_directory_if_needed_new(wizard):
    """Test creating new directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "new_dir"

        assert not path.exists()

        wizard._create_directory_if_needed(path, "Test")

        assert path.exists()
        assert path.is_dir()


def test_create_directory_if_needed_not_directory(wizard):
    """Test error when path exists but is not a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "file.txt"
        path.touch()

        with pytest.raises(ValueError):
            wizard._create_directory_if_needed(path, "Test")


def test_validate_and_create_config(wizard):
    """Test validating and creating configuration."""
    videos_path = Path("/tmp/videos")
    temp_path = Path("/tmp/temp")

    config = wizard._validate_and_create_config(videos_path, temp_path, True)

    assert config is not None
    assert config.videos_path == videos_path
    assert config.temp_path == temp_path
    assert config.keep_temp is True


def test_validate_and_create_config_default_videos(wizard):
    """Test creating config with default videos path."""
    temp_path = Path("/tmp/temp")

    config = wizard._validate_and_create_config(None, temp_path, False)

    assert config is not None
    assert config.videos_path == Path.home() / "Videos" / "auto-videos"


def test_show_summary(wizard):
    """Test displaying configuration summary."""
    config = StorageConfig(
        videos_path=Path("/tmp/videos"),
        temp_path=Path("/tmp/temp"),
        keep_temp=True,
    )

    output = StringIO()
    console = Console(file=output, force_terminal=True)
    wizard.console = console

    wizard._show_summary(config)

    content = output.getvalue()
    assert "Storage Configuration Summary" in content
    assert "/tmp/videos" in content
    assert "/tmp/temp" in content
    assert "True" in content


def test_run_save_videos(wizard):
    """Test running wizard with save videos enabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        videos_path = Path(tmpdir) / "videos"
        temp_path = Path(tmpdir) / "temp"

        with patch.multiple(
            "auto_video.ui.setup",
            Confirm=MagicMock(ask=MagicMock(side_effect=[True, False])),
            Prompt=MagicMock(ask=MagicMock(side_effect=[str(videos_path), str(temp_path)])),
        ):
            with patch.object(wizard, "_create_directory_if_needed"):
                result = wizard.run()

                assert result.success is True
                assert result.config is not None
                assert result.config.videos_path == videos_path
                assert result.config.temp_path == temp_path
                assert result.config.keep_temp is False


def test_run_dont_save_videos(wizard):
    """Test running wizard without saving videos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / "temp"

        with patch.multiple(
            "auto_video.ui.setup",
            Confirm=MagicMock(ask=MagicMock(side_effect=[False, True])),
            Prompt=MagicMock(ask=MagicMock(return_value=str(temp_path))),
        ):
            with patch.object(wizard, "_create_directory_if_needed"):
                result = wizard.run()

                assert result.success is True
                assert result.config is not None
                assert result.config.videos_path == Path.home() / "Videos" / "auto-videos"
                assert result.config.temp_path == temp_path
                assert result.config.keep_temp is True
