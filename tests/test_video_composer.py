"""Test video composer functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from auto_video.core.video import VideoComposer


def test_video_composer_initialization():
    """Test VideoComposer initialization."""
    composer = VideoComposer()

    assert composer.ffmpeg_path == "ffmpeg"
    assert composer.ffprobe_path == "ffprobe"


def test_video_composer_custom_ffmpeg_path():
    """Test VideoComposer with custom ffmpeg path."""
    composer = VideoComposer(ffmpeg_path="/usr/local/bin/ffmpeg")

    assert composer.ffmpeg_path == "/usr/local/bin/ffmpeg"
    assert composer.ffprobe_path == "/usr/local/bin/ffprobe"


def test_concatenate_clips_creates_output():
    """Test concatenate_clips creates output file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        clip1_path = base_path / "clip1.mp4"
        clip1_path.write_bytes(b"fake video data")

        output_path = base_path / "output.mp4"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch.object(composer, "get_duration", return_value=5.0):
                composer.concatenate_clips([clip1_path], output_path, 10.0)

            assert output_path.parent.exists()
            assert mock_run.called


def test_concatenate_clips_with_multiple_clips():
    """Test concatenate_clips with multiple clips."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        clip1_path = base_path / "clip1.mp4"
        clip2_path = base_path / "clip2.mp4"
        clip3_path = base_path / "clip3.mp4"

        clip1_path.write_bytes(b"clip1 data")
        clip2_path.write_bytes(b"clip2 data")
        clip3_path.write_bytes(b"clip3 data")

        output_path = base_path / "output.mp4"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch.object(composer, "get_duration", return_value=3.0):
                with patch.object(composer, "_trim_clip"):
                    composer.concatenate_clips(
                        [clip1_path, clip2_path, clip3_path], output_path, 10.0
                    )

            assert mock_run.called


def test_concatenate_clips_trims_to_target_duration():
    """Test concatenate_clips trims clips to target duration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        clip1_path = base_path / "clip1.mp4"
        clip2_path = base_path / "clip2.mp4"

        clip1_path.write_bytes(b"clip1 data")
        clip2_path.write_bytes(b"clip2 data")

        output_path = base_path / "output.mp4"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch.object(composer, "get_duration", side_effect=[7.0, 5.0]):
                with patch.object(composer, "_trim_clip") as mock_trim:
                    composer.concatenate_clips([clip1_path, clip2_path], output_path, 10.0)

                    mock_trim.assert_called_once()


def test_add_audio_merges_audio_and_video():
    """Test add_audio merges audio and video tracks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        audio_path = base_path / "audio.mp3"
        output_path = base_path / "output.mp4"

        video_path.write_bytes(b"video data")
        audio_path.write_bytes(b"audio data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            composer.add_audio(video_path, audio_path, output_path)

            assert output_path.parent.exists()
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "-c:v" in call_args
            assert "copy" in call_args
            assert "-c:a" in call_args
            assert "aac" in call_args


def test_add_audio_preserves_video_quality():
    """Test add_audio preserves video quality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        audio_path = base_path / "audio.mp3"
        output_path = base_path / "output.mp4"

        video_path.write_bytes(b"video data")
        audio_path.write_bytes(b"audio data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            composer.add_audio(video_path, audio_path, output_path)

            call_args = mock_run.call_args[0][0]
            assert "-map" in call_args
            assert "0:v:0" in call_args
            assert "1:a:0" in call_args
            assert "-shortest" in call_args


def test_apply_format_short():
    """Test apply_format with 'short' format (9:16)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        output_path = base_path / "output.mp4"

        video_path.write_bytes(b"video data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            composer.apply_format(video_path, output_path, "short")

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            vf_index = call_args.index("-vf")
            vf_value = call_args[vf_index + 1]
            assert "scale=1080:-2" in vf_value
            assert "crop=1080:1920" in vf_value


def test_apply_format_long():
    """Test apply_format with 'long' format (16:9)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        output_path = base_path / "output.mp4"

        video_path.write_bytes(b"video data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            composer.apply_format(video_path, output_path, "long")

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            vf_index = call_args.index("-vf")
            vf_value = call_args[vf_index + 1]
            assert "scale=1920:-2" in vf_value
            assert "crop=1920:1080" in vf_value


def test_apply_format_crops_and_pads_correctly():
    """Test apply_format crops and pads correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        output_path = base_path / "output.mp4"

        video_path.write_bytes(b"video data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            composer.apply_format(video_path, output_path, "short")

            call_args = mock_run.call_args[0][0]
            vf_index = call_args.index("-vf")
            vf_value = call_args[vf_index + 1]
            assert "pad=1080:1920" in vf_value
            assert "(ow-iw)/2:(oh-ih)/2" in vf_value
            assert "black" in vf_value


def test_get_duration_returns_duration():
    """Test get_duration returns correct duration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        video_path.write_bytes(b"video data")

        with patch("subprocess.run") as mock_run:
            mock_process = MagicMock(returncode=0, stdout="15.5\n")
            mock_run.return_value = mock_process

            duration = composer.get_duration(video_path)

            assert duration == 15.5
            assert mock_run.called


def test_get_duration_handles_errors_gracefully():
    """Test get_duration handles errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        video_path.write_bytes(b"video data")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            duration = composer.get_duration(video_path)

            assert duration == 0.0


def test_get_duration_invalid_output():
    """Test get_duration with invalid ffprobe output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        video_path.write_bytes(b"video data")

        with patch("subprocess.run") as mock_run:
            mock_process = MagicMock(returncode=0, stdout="invalid\n")
            mock_run.return_value = mock_process

            duration = composer.get_duration(video_path)

            assert duration == 0.0


def test_trim_clip_works_correctly():
    """Test _trim_clip works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        input_path = base_path / "input.mp4"
        output_path = base_path / "output.mp4"

        input_path.write_bytes(b"video data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            composer._trim_clip(input_path, output_path, 5.5)

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "-t" in call_args
            assert "5.5" in call_args
            assert "-c" in call_args
            assert "copy" in call_args


def test_apply_vertical_format_creates_9_16():
    """Test _apply_vertical_format creates 9:16 aspect ratio."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        output_path = base_path / "output.mp4"

        video_path.write_bytes(b"video data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            composer._apply_vertical_format(video_path, output_path)

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            vf_index = call_args.index("-vf")
            vf_value = call_args[vf_index + 1]
            assert "scale=1080:-2" in vf_value
            assert "crop=1080:1920" in vf_value
            assert "libx264" in call_args
            assert "-crf" in call_args
            assert "22" in call_args


def test_apply_horizontal_format_creates_16_9():
    """Test _apply_horizontal_format creates 16:9 aspect ratio."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        output_path = base_path / "output.mp4"

        video_path.write_bytes(b"video data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            composer._apply_horizontal_format(video_path, output_path)

            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            vf_index = call_args.index("-vf")
            vf_value = call_args[vf_index + 1]
            assert "scale=1920:-2" in vf_value
            assert "crop=1920:1080" in vf_value
            assert "libx264" in call_args
            assert "-crf" in call_args
            assert "22" in call_args


def test_apply_format_invalid_format():
    """Test apply_format raises ValueError for invalid format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        video_path = base_path / "video.mp4"
        output_path = base_path / "output.mp4"

        video_path.write_bytes(b"video data")

        with pytest.raises(ValueError) as exc_info:
            composer.apply_format(video_path, output_path, "invalid")

        assert "Unknown format: invalid" in str(exc_info.value)


def test_concatenate_clips_empty_list():
    """Test concatenate_clips with empty clip list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        composer = VideoComposer()

        output_path = base_path / "output.mp4"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            composer.concatenate_clips([], output_path, 10.0)

            assert output_path.parent.exists()
