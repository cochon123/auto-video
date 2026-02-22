"""Test workspace management."""

import tempfile
from pathlib import Path

import pytest

from auto_video.utils.workspace import Workspace


def test_workspace_initialization():
    """Test workspace initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path)

        assert ws.video_id is not None
        assert isinstance(ws.video_id, str)
        assert len(ws.video_id) > 0


def test_workspace_with_custom_video_id():
    """Test workspace with custom video ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        custom_id = "test_video_123"
        ws = Workspace(base_path, video_id=custom_id)

        assert ws.video_id == custom_id
        assert ws.workspace_path == base_path / custom_id


def test_workspace_paths():
    """Test workspace path properties."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        assert ws.workspace_path == base_path / "test_001"
        assert ws.script_path == base_path / "test_001" / "script.txt"
        assert ws.audio_path == base_path / "test_001" / "audio.wav"
        assert ws.video_raw_path == base_path / "test_001" / "video_raw.mp4"
        assert ws.subtitles_path == base_path / "test_001" / "subtitles.srt"
        assert ws.thumbnail_path == base_path / "test_001" / "thumbnail.png"
        assert ws.final_path == base_path / "test_001" / "final.mp4"
        assert ws.logs_path == base_path / "test_001" / "generation.log"
        assert ws.state_path == base_path / "test_001" / "state.json"


def test_workspace_create():
    """Test workspace directory creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        assert not ws.workspace_path.exists()

        ws.create()

        assert ws.workspace_path.exists()
        assert ws.workspace_path.is_dir()


def test_workspace_create_already_exists():
    """Test workspace creation when directory already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()
        assert ws.workspace_path.exists()

        ws.create()
        assert ws.workspace_path.exists()


def test_workspace_cleanup():
    """Test workspace cleanup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()
        assert ws.workspace_path.exists()

        ws.cleanup()

        assert not ws.workspace_path.exists()


def test_workspace_cleanup_when_not_created():
    """Test workspace cleanup when not created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        assert not ws.workspace_path.exists()

        ws.cleanup()

        assert not ws.workspace_path.exists()


def test_workspace_cleanup_keep_artifacts():
    """Test workspace cleanup keeping artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()

        ws.final_path.write_text("final video content")

        ws.cleanup(keep_artifacts=True)

        assert ws.workspace_path.exists()
        assert ws.final_path.exists()
        assert not ws.audio_path.exists()


def test_list_artifacts_empty():
    """Test listing artifacts in empty workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()
        artifacts = ws.list_artifacts()

        assert artifacts == {}


def test_list_artifacts_with_files():
    """Test listing artifacts with files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()

        ws.script_path.write_text("script content")
        ws.audio_path.write_bytes(b"audio data")
        ws.final_path.write_bytes(b"final video data")

        artifacts = ws.list_artifacts()

        assert len(artifacts) == 3
        assert "script" in artifacts
        assert "audio" in artifacts
        assert "final" in artifacts
        assert artifacts["script"] == ws.script_path


def test_get_file_size():
    """Test getting file size of an artifact."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()

        ws.audio_path.write_bytes(b"test audio content")

        size = ws.get_file_size("audio")

        assert size == 18


def test_get_file_size_nonexistent():
    """Test getting file size of non-existent artifact."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()

        size = ws.get_file_size("audio")

        assert size == 0


def test_copy_to_output():
    """Test copying artifact to output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()

        ws.final_path.write_bytes(b"final video data")

        output_dir = Path(tmpdir) / "output"
        copied_path = ws.copy_to_output(output_dir, "final")

        assert copied_path.exists()
        assert copied_path.name == "final.mp4"
        assert copied_path.read_bytes() == b"final video data"


def test_copy_to_output_nonexistent():
    """Test copying non-existent artifact raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()

        output_dir = Path(tmpdir) / "output"

        with pytest.raises(FileNotFoundError):
            ws.copy_to_output(output_dir, "final")


def test_video_id_generation():
    """Test that video IDs are unique."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        ws1 = Workspace(base_path)
        ws2 = Workspace(base_path)
        ws3 = Workspace(base_path)

        ids = [ws1.video_id, ws2.video_id, ws3.video_id]

        assert len(ids) == len(set(ids))
        assert all("_" in id_ for id_ in ids)


def test_workspace_script_write_read():
    """Test writing and reading script file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()

        ws.script_path.write_text("This is a test script.")

        content = ws.script_path.read_text()

        assert content == "This is a test script."
        assert ws.script_path.exists()


def test_workspace_audio_write_read():
    """Test writing and reading audio file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        ws = Workspace(base_path, video_id="test_001")

        ws.create()

        ws.audio_path.write_bytes(b"fake audio data")

        content = ws.audio_path.read_bytes()

        assert content == b"fake audio data"
        assert ws.audio_path.exists()
