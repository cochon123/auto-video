"""Subtitles core module using Whisper (C++ preferred, Python fallback)."""

import json
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    segments: list[dict[str, float | str]]
    text: str


class SubtitleStyle(BaseModel):
    font: str = "Arial"
    font_size: int = 24
    color: str = "white"
    background: str = "black@0.5"
    position: Literal["top", "center", "bottom"] = "bottom"


class SubtitleGenerator:
    _backend: Literal["whisper_cpp_cli", "whisper_gael", "whisper_cpp", "whisper"]

    def __init__(self, model: str = "base"):
        self.model = model
        self._check_model_available()

    def _check_model_available(self) -> None:
        """Check for whisper.cpp CLI, whisper-gael CLI, Whisper C++, or fallback to Whisper Python."""
        # Priority 1: Check for whisper.cpp CLI binary
        whisper_cpp_cli_path = (
            Path.home() / ".local" / "share" / "whisper.cpp" / "build" / "bin" / "whisper-cli"
        )
        if whisper_cpp_cli_path.exists() and whisper_cpp_cli_path.is_file():
            self._backend = "whisper_cpp_cli"
            logger.info(f"Using whisper.cpp CLI binary: {whisper_cpp_cli_path}")
            return

        # Priority 2: Check for whisper-gael CLI
        whisper_gael_path = shutil.which("whisper-gael.whisper")
        if whisper_gael_path:
            self._backend = "whisper_gael"
            logger.info(f"Using whisper-gael CLI: {whisper_gael_path}")
            return

        # Priority 3: Check for Whisper C++ Python package
        try:
            import whisper_cpp

            whisper_cpp.WhisperCpp.from_pretrained(model_name_or_path=self.model)

            self._backend = "whisper_cpp"
            logger.info(f"Whisper C++ model loaded: {self.model}")
        except Exception as e:
            logger.warning(f"Whisper C++ not available: {e}")
            logger.info("Falling back to Whisper Python")
            import importlib.util

            if importlib.util.find_spec("whisper"):
                self._backend = "whisper"
                logger.info(f"Whisper Python available: {self.model}")
            else:
                logger.error(
                    "Neither whisper.cpp CLI, whisper-gael, Whisper C++ nor Whisper Python is available"
                )
                raise ImportError(
                    "Install whisper.cpp CLI, whisper-gael snap: sudo snap install whisper-gael, "
                    "or whisper-cpp: pip install whisper-cpp, "
                    "or Whisper Python: pip install openai-whisper"
                )

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe audio using Whisper (whisper.cpp CLI, whisper-gael, C++, or Python).

        Args:
            audio_path: Path to audio file.

        Returns:
            TranscriptionResult with segments and full text.
        """
        if self._backend == "whisper_cpp_cli":
            return self._transcribe_whisper_cpp_cli(audio_path)
        elif self._backend == "whisper_gael":
            return self._transcribe_whisper_gael(audio_path)
        elif self._backend == "whisper_cpp":
            return self._transcribe_whisper_cpp(audio_path)
        else:
            return self._transcribe_whisper_python(audio_path)

    def _transcribe_whisper_cpp(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using Whisper C++."""
        try:
            import whisper_cpp

            logger.info(f"Transcribing {audio_path} with Whisper C++ (model: {self.model})")

            whisper_model = whisper_cpp.WhisperCpp.from_pretrained(
                model_name_or_path=self.model,
                n_threads=4,
                print_realtime=False,
                print_progress=False,
            )

            segments_data = whisper_model.transcribe(
                audio=str(audio_path),
                word_timestamps=True,
                language=None,
            )

            segments = [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                }
                for seg in segments_data.segments
                if seg.text.strip()
            ]

            full_text = " ".join(seg["text"] for seg in segments)

            logger.info(
                f"Transcription complete: {len(segments)} segments, {len(full_text)} characters"
            )

            return TranscriptionResult(segments=segments, text=full_text)

        except Exception as e:
            logger.error(f"Whisper C++ transcription failed: {e}")
            return self._transcribe_ffmpeg(audio_path)

    def _transcribe_whisper_cpp_cli(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using whisper.cpp CLI binary with GPU acceleration."""
        # Setup temp directory in home to avoid snap confinement issues
        temp_base = Path.home() / ".cache" / "auto-video" / "whisper_temp"
        temp_base.mkdir(parents=True, exist_ok=True)
        temp_dir = tempfile.mkdtemp(dir=temp_base)
        temp_path = Path(temp_dir)

        try:
            logger.info(
                f"Transcribing {audio_path} with whisper.cpp CLI (model: {self.model}, GPU enabled)"
            )

            # Determine model file path
            model_name = f"ggml-{self.model}.bin"
            model_path = Path.home() / ".local" / "share" / "whisper.cpp" / "models" / model_name

            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return self._transcribe_ffmpeg(audio_path)

            # Output file path (without extension)
            output_file = temp_path / "output"

            # Run whisper.cpp CLI with GPU acceleration
            subprocess.run(
                [
                    str(
                        Path.home()
                        / ".local"
                        / "share"
                        / "whisper.cpp"
                        / "build"
                        / "bin"
                        / "whisper-cli"
                    ),
                    "-m",
                    str(model_path),
                    "-l",
                    "auto",
                    "-oj",
                    "-of",
                    str(output_file),
                    "-f",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=600,
                check=True,
            )

            # Find and parse JSON output file
            json_files = list(temp_path.glob("*.json"))
            if not json_files:
                logger.error("No JSON output file found from whisper.cpp CLI")
                return self._transcribe_ffmpeg(audio_path)

            json_file = json_files[0]
            with json_file.open("r", encoding="utf-8") as f:
                result_data = json.load(f)

            # Parse transcription from JSON output
            def parse_timestamp(ts: str) -> float:
                """Parse HH:MM:SS,mmm format to seconds."""
                time_part, millis_part = ts.split(",")
                hours, minutes, seconds = map(int, time_part.split(":"))
                return hours * 3600 + minutes * 60 + seconds + int(millis_part) / 1000

            segments = []
            for seg in result_data.get("transcription", []):
                text = seg.get("text", "").strip()
                if text:
                    start = parse_timestamp(seg["timestamps"]["from"])
                    end = parse_timestamp(seg["timestamps"]["to"])
                    segments.append({"start": start, "end": end, "text": text})

            full_text = " ".join(seg["text"] for seg in segments)

            logger.info(
                f"Transcription complete: {len(segments)} segments, {len(full_text)} characters"
            )

            return TranscriptionResult(segments=segments, text=full_text)

        except subprocess.TimeoutExpired:
            logger.error("Whisper.cpp CLI transcription timed out")
            return self._transcribe_ffmpeg(audio_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"Whisper.cpp CLI failed: {e.stderr}")
            return self._transcribe_ffmpeg(audio_path)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse whisper.cpp CLI JSON output: {e}")
            return self._transcribe_ffmpeg(audio_path)
        except Exception as e:
            logger.error(f"Whisper.cpp CLI transcription failed: {e}")
            return self._transcribe_ffmpeg(audio_path)
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _transcribe_whisper_gael(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using whisper-gael CLI."""
        try:
            logger.info(f"Transcribing {audio_path} with whisper-gael CLI (model: {self.model})")

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                subprocess.run(
                    [
                        "whisper-gael.whisper",
                        str(audio_path),
                        "--model",
                        self.model,
                        "--output_format",
                        "json",
                        "--output_dir",
                        str(temp_path),
                        "--task",
                        "transcribe",
                        "--verbose",
                        "False",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=600,
                    check=True,
                )

                json_files = list(temp_path.glob("*.json"))
                if not json_files:
                    logger.error("No JSON output file found from whisper-gael")
                    return self._transcribe_ffmpeg(audio_path)

                json_file = json_files[0]
                with json_file.open("r", encoding="utf-8") as f:
                    result_data = json.load(f)

                segments = [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"].strip(),
                    }
                    for seg in result_data.get("segments", [])
                    if seg.get("text", "").strip()
                ]

                full_text = " ".join(seg["text"] for seg in segments)

                logger.info(
                    f"Transcription complete: {len(segments)} segments, {len(full_text)} characters"
                )

                return TranscriptionResult(segments=segments, text=full_text)

        except subprocess.TimeoutExpired:
            logger.error("Whisper-gael transcription timed out")
            return self._transcribe_ffmpeg(audio_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"Whisper-gael CLI failed: {e.stderr}")
            return self._transcribe_ffmpeg(audio_path)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse whisper-gael JSON output: {e}")
            return self._transcribe_ffmpeg(audio_path)
        except Exception as e:
            logger.error(f"Whisper-gael transcription failed: {e}")
            return self._transcribe_ffmpeg(audio_path)

    def _transcribe_whisper_python(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe using Whisper Python."""
        try:
            import whisper

            logger.info(f"Transcribing {audio_path} with Whisper Python (model: {self.model})")

            whisper_model = whisper.load_model(self.model)
            result = whisper_model.transcribe(str(audio_path), word_timestamps=True)

            segments = [
                {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
                for seg in result["segments"]
                if seg["text"].strip()
            ]

            full_text = " ".join(seg["text"] for seg in segments)

            logger.info(
                f"Transcription complete: {len(segments)} segments, {len(full_text)} characters"
            )

            return TranscriptionResult(segments=segments, text=full_text)

        except Exception as e:
            logger.error(f"Whisper Python transcription failed: {e}")
            return self._transcribe_ffmpeg(audio_path)

    def transcribe_with_timing(self, audio_path: Path) -> tuple[TranscriptionResult, list[float]]:
        """Transcribe audio and return segments with timing info.

        Returns:
            Tuple of (TranscriptionResult, segment_durations).
            segment_durations: List of duration in seconds for each segment.
        """
        if self._backend == "whisper_cpp_cli":
            return self._transcribe_with_timing_whisper_cpp_cli(audio_path)
        elif self._backend == "whisper_gael":
            return self._transcribe_with_timing_gael(audio_path)
        elif self._backend == "whisper_cpp":
            return self._transcribe_with_timing_cpp(audio_path)
        else:
            return self._transcribe_with_timing_python(audio_path)

    def _transcribe_with_timing_cpp(
        self, audio_path: Path
    ) -> tuple[TranscriptionResult, list[float]]:
        """Transcribe with timing using Whisper C++."""
        try:
            import whisper_cpp

            logger.info(
                f"Transcribing {audio_path} with Whisper C++ (model: {self.model}) with timing"
            )

            whisper_model = whisper_cpp.WhisperCpp.from_pretrained(
                model_name_or_path=self.model,
                n_threads=4,
                print_realtime=False,
                print_progress=False,
            )

            segments_data = whisper_model.transcribe(
                audio=str(audio_path),
                word_timestamps=True,
                language=None,
            )

            segments = []
            segment_durations = []

            for seg in segments_data.segments:
                if seg.text.strip():
                    start = seg.start
                    end = seg.end
                    duration = end - start
                    text = seg.text.strip()

                    segments.append({"start": start, "end": end, "text": text})
                    segment_durations.append(duration)

                    logger.debug(
                        f"Segment: [{start:.2f} - {end:.2f}] ({duration:.2f}s): {text[:50]}..."
                    )

            full_text = " ".join(seg["text"] for seg in segments)

            logger.info(
                f"Transcription complete: {len(segments)} segments, "
                f"{len(full_text)} characters, total: {sum(segment_durations):.2f}s"
            )

            return TranscriptionResult(segments=segments, text=full_text), segment_durations

        except Exception as e:
            logger.error(f"Whisper C++ transcription failed: {e}")
            return self._transcribe_ffmpeg_with_timing(audio_path)

    def _transcribe_with_timing_whisper_cpp_cli(
        self, audio_path: Path
    ) -> tuple[TranscriptionResult, list[float]]:
        """Transcribe with timing using whisper.cpp CLI binary with GPU acceleration."""
        # Setup temp directory in home to avoid snap confinement issues
        temp_base = Path.home() / ".cache" / "auto-video" / "whisper_temp"
        temp_base.mkdir(parents=True, exist_ok=True)
        temp_dir = tempfile.mkdtemp(dir=temp_base)
        temp_path = Path(temp_dir)

        try:
            logger.info(
                f"Transcribing {audio_path} with whisper.cpp CLI (model: {self.model}, GPU enabled) with timing"
            )

            # Determine model file path
            model_name = f"ggml-{self.model}.bin"
            model_path = Path.home() / ".local" / "share" / "whisper.cpp" / "models" / model_name

            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return self._transcribe_ffmpeg_with_timing(audio_path)

            # Output file path (without extension)
            output_file = temp_path / "output"

            # Run whisper.cpp CLI with GPU acceleration
            subprocess.run(
                [
                    str(
                        Path.home()
                        / ".local"
                        / "share"
                        / "whisper.cpp"
                        / "build"
                        / "bin"
                        / "whisper-cli"
                    ),
                    "-m",
                    str(model_path),
                    "-l",
                    "auto",
                    "-oj",
                    "-of",
                    str(output_file),
                    "-f",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=600,
                check=True,
            )

            # Find and parse JSON output file
            json_files = list(temp_path.glob("*.json"))
            if not json_files:
                logger.error("No JSON output file found from whisper.cpp CLI")
                return self._transcribe_ffmpeg_with_timing(audio_path)

            json_file = json_files[0]
            with json_file.open("r", encoding="utf-8") as f:
                result_data = json.load(f)

            # Parse transcription with timing from JSON output
            def parse_timestamp(ts: str) -> float:
                """Parse HH:MM:SS,mmm format to seconds."""
                time_part, millis_part = ts.split(",")
                hours, minutes, seconds = map(int, time_part.split(":"))
                return hours * 3600 + minutes * 60 + seconds + int(millis_part) / 1000

            segments = []
            segment_durations = []

            for seg in result_data.get("transcription", []):
                text = seg.get("text", "").strip()
                if text:
                    start = parse_timestamp(seg["timestamps"]["from"])
                    end = parse_timestamp(seg["timestamps"]["to"])
                    duration = end - start

                    segments.append({"start": start, "end": end, "text": text})
                    segment_durations.append(duration)

                    logger.debug(
                        f"Segment: [{start:.2f} - {end:.2f}] ({duration:.2f}s): {text[:50]}..."
                    )

            full_text = " ".join(seg["text"] for seg in segments)

            logger.info(
                f"Transcription complete: {len(segments)} segments, "
                f"{len(full_text)} characters, total: {sum(segment_durations):.2f}s"
            )

            return TranscriptionResult(segments=segments, text=full_text), segment_durations

        except subprocess.TimeoutExpired:
            logger.error("Whisper.cpp CLI transcription timed out")
            return self._transcribe_ffmpeg_with_timing(audio_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"Whisper.cpp CLI failed: {e.stderr}")
            return self._transcribe_ffmpeg_with_timing(audio_path)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse whisper.cpp CLI JSON output: {e}")
            return self._transcribe_ffmpeg_with_timing(audio_path)
        except Exception as e:
            logger.error(f"Whisper.cpp CLI transcription failed: {e}")
            return self._transcribe_ffmpeg_with_timing(audio_path)
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _transcribe_with_timing_gael(
        self, audio_path: Path
    ) -> tuple[TranscriptionResult, list[float]]:
        """Transcribe with timing using whisper-gael CLI."""
        try:
            logger.info(
                f"Transcribing {audio_path} with whisper-gael CLI (model: {self.model}) with timing"
            )

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                subprocess.run(
                    [
                        "whisper-gael.whisper",
                        str(audio_path),
                        "--model",
                        self.model,
                        "--output_format",
                        "json",
                        "--output_dir",
                        str(temp_path),
                        "--task",
                        "transcribe",
                        "--word_timestamps",
                        "--verbose",
                        "False",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=600,
                    check=True,
                )

                json_files = list(temp_path.glob("*.json"))
                if not json_files:
                    logger.error("No JSON output file found from whisper-gael")
                    return self._transcribe_ffmpeg_with_timing(audio_path)

                json_file = json_files[0]
                with json_file.open("r", encoding="utf-8") as f:
                    result_data = json.load(f)

                segments = []
                segment_durations = []

                for seg in result_data.get("segments", []):
                    text = seg.get("text", "").strip()
                    if text:
                        start = seg["start"]
                        end = seg["end"]
                        duration = end - start

                        segments.append({"start": start, "end": end, "text": text})
                        segment_durations.append(duration)

                        logger.debug(
                            f"Segment: [{start:.2f} - {end:.2f}] ({duration:.2f}s): {text[:50]}..."
                        )

                full_text = " ".join(seg["text"] for seg in segments)

                logger.info(
                    f"Transcription complete: {len(segments)} segments, "
                    f"{len(full_text)} characters, total: {sum(segment_durations):.2f}s"
                )

                return TranscriptionResult(segments=segments, text=full_text), segment_durations

        except subprocess.TimeoutExpired:
            logger.error("Whisper-gael transcription timed out")
            return self._transcribe_ffmpeg_with_timing(audio_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"Whisper-gael CLI failed: {e.stderr}")
            return self._transcribe_ffmpeg_with_timing(audio_path)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse whisper-gael JSON output: {e}")
            return self._transcribe_ffmpeg_with_timing(audio_path)
        except Exception as e:
            logger.error(f"Whisper-gael transcription failed: {e}")
            return self._transcribe_ffmpeg_with_timing(audio_path)

    def _transcribe_with_timing_python(
        self, audio_path: Path
    ) -> tuple[TranscriptionResult, list[float]]:
        """Transcribe with timing using Whisper Python."""
        try:
            import whisper

            logger.info(
                f"Transcribing {audio_path} with Whisper Python (model: {self.model}) with timing"
            )

            whisper_model = whisper.load_model(self.model)
            result = whisper_model.transcribe(str(audio_path), word_timestamps=True)

            segments = []
            segment_durations = []

            for seg in result["segments"]:
                if seg["text"].strip():
                    start = seg["start"]
                    end = seg["end"]
                    duration = end - start
                    text = seg["text"].strip()

                    segments.append({"start": start, "end": end, "text": text})
                    segment_durations.append(duration)

                    logger.debug(
                        f"Segment: [{start:.2f} - {end:.2f}] ({duration:.2f}s): {text[:50]}..."
                    )

            full_text = " ".join(seg["text"] for seg in segments)

            logger.info(
                f"Transcription complete: {len(segments)} segments, "
                f"{len(full_text)} characters, total: {sum(segment_durations):.2f}s"
            )

            return TranscriptionResult(segments=segments, text=full_text), segment_durations

        except Exception as e:
            logger.error(f"Whisper Python transcription failed: {e}")
            return self._transcribe_ffmpeg_with_timing(audio_path)

    def _transcribe_ffmpeg_with_timing(
        self, audio_path: Path
    ) -> tuple[TranscriptionResult, list[float]]:
        """Fallback FFmpeg transcription (returns single segment)."""
        try:
            duration = self._get_audio_duration(audio_path)
            segments: list[dict[str, float | str]] = [
                {
                    "start": 0.0,
                    "end": duration,
                    "text": "Audio transcription requires Whisper library",
                }
            ]

            text: str = str(segments[0]["text"])
            return TranscriptionResult(segments=segments, text=text), [duration]

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return TranscriptionResult(segments=[], text=""), []

    def _transcribe_ffmpeg(self, audio_path: Path) -> TranscriptionResult:
        """Fallback FFmpeg transcription (returns single segment)."""
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

            duration = self._get_audio_duration(audio_path)
            segments: list[dict[str, float | str]] = [
                {
                    "start": 0.0,
                    "end": duration,
                    "text": "Audio transcription requires Whisper library",
                }
            ]

            text: str = str(segments[0]["text"])
            return TranscriptionResult(segments=segments, text=text)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return TranscriptionResult(segments=[], text="")

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio file duration using ffprobe."""
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
        """Generate SRT subtitle file.

        Args:
            result: Transcription result with segments.
            output_path: Path to save SRT file.
            style: Subtitle style settings.
        """
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
        """Format seconds to SRT time format (HH:MM:SS,mmm)."""
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
        """Burn subtitles into video using FFmpeg.

        Args:
            video_path: Path to input video.
            srt_path: Path to SRT subtitle file.
            output_path: Path to save output video.
            style: Subtitle style settings.
        """
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


__all__ = [
    "SubtitleGenerator",
    "SubtitleStyle",
    "TranscriptionResult",
]
