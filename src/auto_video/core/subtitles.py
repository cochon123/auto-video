"""Subtitles core module."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


@dataclass
class TranscriptionResult:
    segments: list[dict[str, float | str]]


class SubtitleStyle(BaseModel):
    font: str = "Arial"
    font_size: int = 24
    color: str = "white"
    background: str = "black@0.5"
    position: Literal["top", "center", "bottom"] = "bottom"


class SubtitleGenerator:
    def __init__(self, model: str = "base"):
        self.model = model

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        try:
            import whisper  # type: ignore

            whisper_model = whisper.load_model(self.model)
            result = whisper_model.transcribe(str(audio_path), word_timestamps=True)

            segments = [
                {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
                for seg in result["segments"]
                if seg["text"].strip()
            ]

            return TranscriptionResult(segments=segments)

        except (ImportError, ModuleNotFoundError):
            return self._transcribe_ffmpeg(audio_path)

    def _transcribe_ffmpeg(self, audio_path: Path) -> TranscriptionResult:
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(audio_path),
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            segments: list[dict[str, float | str]] = [
                {
                    "start": 0.0,
                    "end": self._get_audio_duration(audio_path),
                    "text": "Audio transcription requires Whisper Python library",
                }
            ]

            return TranscriptionResult(segments=segments)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return TranscriptionResult(segments=[])

    def _get_audio_duration(self, audio_path: Path) -> float:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            pass
        return 0.0

    def generate_srt(
        self, result: TranscriptionResult, output_path: Path, style: SubtitleStyle
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            for i, segment in enumerate(result.segments, 1):
                start_time = self._format_srt_time(float(segment["start"]))
                end_time = self._format_srt_time(float(segment["end"]))
                text = str(segment["text"])

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

    def _format_srt_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds % 1) * 1000))
        if millis >= 1000:
            millis = 999
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def burn_subtitles(
        self, video_path: Path, srt_path: Path, output_path: Path, style: SubtitleStyle
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        color_map = {
            "white": "&HFFFFFF",
            "black": "&H000000",
            "red": "&H0000FF",
            "green": "&H00FF00",
            "blue": "&HFF0000",
            "yellow": "&H00FFFF",
        }

        primary_colour = color_map.get(style.color.lower(), "&HFFFFFF")

        force_style = (
            f"FontSize={style.font_size},PrimaryColour={primary_colour},FontName={style.font}"
        )

        if style.position == "top":
            force_style += ",Alignment=8"
        elif style.position == "center":
            force_style += ",Alignment=5"
        else:
            force_style += ",Alignment=2"

        abs_srt_path = srt_path.absolute()

        import shutil
        import tempfile

        with tempfile.NamedTemporaryFile(
            suffix=".mp4", delete=False, dir=output_path.parent
        ) as temp_file:
            temp_path = output_path.parent / temp_file.name

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(video_path),
                    "-vf",
                    f"subtitles='{abs_srt_path}':force_style='{force_style}'",
                    "-c:a",
                    "copy",
                    str(temp_path),
                ],
                capture_output=True,
                check=True,
                timeout=600,
            )

            shutil.move(str(temp_path), str(output_path))


__all__ = ["SubtitleGenerator", "SubtitleStyle", "TranscriptionResult"]
