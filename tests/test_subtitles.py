"""Test subtitles module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from auto_video.core.subtitles import (
    SubtitleGenerator,
    SubtitleStyle,
    TranscriptionResult,
)


def test_subtitle_style_creation_with_defaults():
    """Test SubtitleStyle creates with default values."""
    style = SubtitleStyle()

    assert style.font == "Arial"
    assert style.font_size == 24
    assert style.color == "white"
    assert style.background == "black@0.5"
    assert style.position == "bottom"


def test_subtitle_style_with_custom_values():
    """Test SubtitleStyle accepts custom values."""
    style = SubtitleStyle(
        font="Helvetica",
        font_size=32,
        color="yellow",
        background="blue@0.3",
        position="top",
    )

    assert style.font == "Helvetica"
    assert style.font_size == 32
    assert style.color == "yellow"
    assert style.background == "blue@0.3"
    assert style.position == "top"


def test_subtitle_generator_initialization():
    """Test SubtitleGenerator initializes with default model."""
    generator = SubtitleGenerator()

    assert generator.model == "base"


def test_subtitle_generator_initialization_with_custom_model():
    """Test SubtitleGenerator initializes with custom model."""
    generator = SubtitleGenerator(model="small")

    assert generator.model == "small"


def test_transcribe_returns_transcription_result():
    """Test transcribe returns TranscriptionResult instance."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_bytes(b"fake audio data")

    try:
        mock_whisper_module = MagicMock()
        mock_model = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model
        mock_model.transcribe.return_value = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Hello world"},
                {"start": 2.0, "end": 4.0, "text": "Test segment"},
            ]
        }

        with patch.dict("sys.modules", {"whisper": mock_whisper_module}):
            generator = SubtitleGenerator()
            result = generator.transcribe(tmp_path)

        assert isinstance(result, TranscriptionResult)
        assert len(result.segments) == 2
    finally:
        tmp_path.unlink(missing_ok=True)


def test_transcribe_with_whisper_available():
    """Test transcribe uses Whisper when available."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_bytes(b"fake audio data")

    try:
        mock_whisper_module = MagicMock()
        mock_model = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model
        mock_model.transcribe.return_value = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "  Hello world  "},
            ]
        }

        with patch.dict("sys.modules", {"whisper": mock_whisper_module}):
            generator = SubtitleGenerator()
            result = generator.transcribe(tmp_path)

            mock_whisper_module.load_model.assert_called_once_with("base")
            mock_model.transcribe.assert_called_once()

        assert result.segments[0]["text"] == "Hello world"
    finally:
        tmp_path.unlink(missing_ok=True)


def test_transcribe_with_ffmpeg_fallback():
    """Test transcribe falls back to FFmpeg when Whisper unavailable."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_bytes(b"fake audio data")

    try:
        with patch.dict("sys.modules", {}, clear=False):
            with patch.object(SubtitleGenerator, "_get_audio_duration", return_value=10.5):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)

                    generator = SubtitleGenerator()
                    result = generator.transcribe(tmp_path)

        assert len(result.segments) == 1
        assert result.segments[0]["start"] == 0.0
        assert result.segments[0]["end"] == 10.5
    finally:
        tmp_path.unlink(missing_ok=True)


def test_transcribe_handles_errors_gracefully():
    """Test transcribe handles errors gracefully."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_bytes(b"fake audio data")

    try:
        with patch.dict("sys.modules", {}, clear=False):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                generator = SubtitleGenerator()
                result = generator.transcribe(tmp_path)

        assert result.segments == []
    finally:
        tmp_path.unlink(missing_ok=True)


def test_generate_srt_creates_file():
    """Test generate_srt creates SRT file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.srt"
        result = TranscriptionResult(
            segments=[
                {"start": 0.0, "end": 2.0, "text": "First subtitle"},
                {"start": 2.0, "end": 4.0, "text": "Second subtitle"},
            ]
        )
        style = SubtitleStyle()

        generator = SubtitleGenerator()
        generator.generate_srt(result, output_path, style)

        assert output_path.exists()
        assert output_path.is_file()


def test_generate_srt_formats_timestamps_correctly():
    """Test generate_srt formats timestamps in SRT format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.srt"
        result = TranscriptionResult(
            segments=[
                {"start": 0.5, "end": 3.5, "text": "Test text"},
            ]
        )
        style = SubtitleStyle()

        generator = SubtitleGenerator()
        generator.generate_srt(result, output_path, style)

        content = output_path.read_text(encoding="utf-8")

        assert "00:00:00,500" in content
        assert "00:00:03,500" in content
        assert "-->" in content


def test_generate_srt_writes_correct_content():
    """Test generate_srt writes correct subtitle content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.srt"
        result = TranscriptionResult(
            segments=[
                {"start": 0.0, "end": 2.0, "text": "Hello world"},
                {"start": 2.0, "end": 4.0, "text": "Second line"},
            ]
        )
        style = SubtitleStyle()

        generator = SubtitleGenerator()
        generator.generate_srt(result, output_path, style)

        content = output_path.read_text(encoding="utf-8")

        assert "1\n" in content
        assert "2\n" in content
        assert "Hello world" in content
        assert "Second line" in content


def test_burn_subtitles_creates_output_video():
    """Test burn_subtitles creates output video file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "input.mp4"
        srt_path = Path(tmpdir) / "subtitles.srt"
        output_path = Path(tmpdir) / "output.mp4"
        style = SubtitleStyle()

        video_path.write_bytes(b"fake video data")
        srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest\n", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()

            generator = SubtitleGenerator()
            generator.burn_subtitles(video_path, srt_path, output_path, style)

            mock_run.assert_called_once()


def test_burn_subtitles_applies_style():
    """Test burn_subtitles applies subtitle style correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "input.mp4"
        srt_path = Path(tmpdir) / "subtitles.srt"
        output_path = Path(tmpdir) / "output.mp4"
        style = SubtitleStyle(font="Helvetica", font_size=32, color="yellow", position="top")

        video_path.write_bytes(b"fake video data")
        srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest\n", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()

            generator = SubtitleGenerator()
            generator.burn_subtitles(video_path, srt_path, output_path, style)

            call_args = mock_run.call_args[0][0]
            vf_arg = [arg for arg in call_args if arg.startswith("subtitles=")][0]

            assert "FontSize=32" in vf_arg
            assert "PrimaryColour=&H00FFFF" in vf_arg
            assert "FontName=Helvetica" in vf_arg
            assert "Alignment=8" in vf_arg


def test_format_srt_time_converts_seconds():
    """Test _format_srt_time converts seconds to SRT format."""
    generator = SubtitleGenerator()

    result = generator._format_srt_time(3661.5)

    assert result == "01:01:01,500"


def test_format_srt_time_with_zero_seconds():
    """Test _format_srt_time handles zero seconds."""
    generator = SubtitleGenerator()

    result = generator._format_srt_time(0.0)

    assert result == "00:00:00,000"


def test_format_srt_time_with_fractional_seconds():
    """Test _format_srt_time handles fractional seconds."""
    generator = SubtitleGenerator()

    result = generator._format_srt_time(65.123)

    assert result == "00:01:05,123"


def test_burn_subtitles_position_bottom():
    """Test burn_subtitles uses bottom alignment by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "input.mp4"
        srt_path = Path(tmpdir) / "subtitles.srt"
        output_path = Path(tmpdir) / "output.mp4"
        style = SubtitleStyle(position="bottom")

        video_path.write_bytes(b"fake video data")
        srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest\n", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()

            generator = SubtitleGenerator()
            generator.burn_subtitles(video_path, srt_path, output_path, style)

            call_args = mock_run.call_args[0][0]
            vf_arg = [arg for arg in call_args if arg.startswith("subtitles=")][0]

            assert "Alignment=2" in vf_arg


def test_burn_subtitles_position_center():
    """Test burn_subtitles uses center alignment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "input.mp4"
        srt_path = Path(tmpdir) / "subtitles.srt"
        output_path = Path(tmpdir) / "output.mp4"
        style = SubtitleStyle(position="center")

        video_path.write_bytes(b"fake video data")
        srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest\n", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()

            generator = SubtitleGenerator()
            generator.burn_subtitles(video_path, srt_path, output_path, style)

            call_args = mock_run.call_args[0][0]
            vf_arg = [arg for arg in call_args if arg.startswith("subtitles=")][0]

            assert "Alignment=5" in vf_arg


def test_burn_subtitles_color_white():
    """Test burn_subtitles uses correct color mapping for white."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "input.mp4"
        srt_path = Path(tmpdir) / "subtitles.srt"
        output_path = Path(tmpdir) / "output.mp4"
        style = SubtitleStyle(color="white")

        video_path.write_bytes(b"fake video data")
        srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest\n", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()

            generator = SubtitleGenerator()
            generator.burn_subtitles(video_path, srt_path, output_path, style)

            call_args = mock_run.call_args[0][0]
            vf_arg = [arg for arg in call_args if arg.startswith("subtitles=")][0]

            assert "PrimaryColour=&HFFFFFF" in vf_arg


def test_burn_subtitles_color_red():
    """Test burn_subtitles uses correct color mapping for red."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / "input.mp4"
        srt_path = Path(tmpdir) / "subtitles.srt"
        output_path = Path(tmpdir) / "output.mp4"
        style = SubtitleStyle(color="red")

        video_path.write_bytes(b"fake video data")
        srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nTest\n", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()

            generator = SubtitleGenerator()
            generator.burn_subtitles(video_path, srt_path, output_path, style)

            call_args = mock_run.call_args[0][0]
            vf_arg = [arg for arg in call_args if arg.startswith("subtitles=")][0]

            assert "PrimaryColour=&H0000FF" in vf_arg
