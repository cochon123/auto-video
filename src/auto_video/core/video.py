"""Video core module."""

import random
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from auto_video.utils.gpu import GPUDetector


@dataclass
class VideoResult:
    id: str
    url: str
    duration: int
    thumbnail: str
    quality: str


class StockProvider(ABC):
    @abstractmethod
    def search_videos(self, query: str, duration_min: int) -> list[VideoResult]: ...

    @abstractmethod
    def download_video(self, video_id: str, output_path: Path, quality: str) -> Path: ...

    @abstractmethod
    def health_check(self) -> bool: ...


@dataclass
class Asset:
    path: Path
    type: Literal["video", "image"]
    duration: float | None


class LocalAssetsManager:
    def __init__(self, path: Path, include_subdirs: bool):
        self.path = path
        self.include_subdirs = include_subdirs
        self.video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"}
        self.image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        self._assets: list[Asset] | None = None

    def scan_assets(self) -> list[Asset]:
        self._assets = []
        pattern = "**/*" if self.include_subdirs else "*"

        for file_path in self.path.glob(pattern):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.video_extensions:
                    duration = self._get_video_duration(file_path)
                    self._assets.append(Asset(file_path, "video", duration))
                elif ext in self.image_extensions:
                    self._assets.append(Asset(file_path, "image", None))

        return self._assets

    def get_random_sequence(self, duration: float) -> list[Asset]:
        if self._assets is None:
            self.scan_assets()

        if not self._assets:
            return []

        videos = [a for a in self._assets if a.type == "video"]
        images = [a for a in self._assets if a.type == "image"]

        sequence: list[Asset] = []
        total_duration = 0.0
        use_video = random.choice([True, False]) if videos and images else bool(videos)

        while total_duration < duration:
            if use_video and videos:
                asset = random.choice(videos)
                if asset.duration:
                    total_duration += asset.duration
                    sequence.append(asset)
                    use_video = False
            elif images:
                asset = random.choice(images)
                total_duration += 4.0
                sequence.append(asset)
                use_video = True
            else:
                break

        if total_duration < duration:
            self._extend_sequence(sequence, duration - total_duration)

        return sequence

    def prepare_clips(self, assets: list[Asset]) -> list[Path]:
        clips: list[Path] = []
        temp_dir = Path(tempfile.gettempdir()) / "auto_video_clips"
        temp_dir.mkdir(parents=True, exist_ok=True)

        for i, asset in enumerate(assets):
            if asset.type == "video":
                clips.append(asset.path)
            else:
                clip_path = temp_dir / f"ken_burns_{i}_{asset.path.name}.mp4"
                self._create_ken_burns_effect(asset.path, clip_path)
                clips.append(clip_path)

        return clips

    def _get_video_duration(self, video_path: Path) -> float:
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
                    str(video_path),
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

    def _create_ken_burns_effect(self, image_path: Path, output_path: Path) -> None:
        duration = 4.0
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(image_path),
                "-vf",
                f"scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                f"zoompan=z='min(zoom+0.0015,1.5)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"duration={duration}:fps=30",
                "-c:v",
                "libx264",
                "-t",
                str(duration),
                "-pix_fmt",
                "yuv420p",
                "-r",
                "30",
                str(output_path),
            ],
            capture_output=True,
            timeout=30,
        )

    def _extend_sequence(self, sequence: list[Asset], needed_duration: float) -> None:
        if not sequence:
            return

        remaining = needed_duration
        i = 0

        while remaining > 0:
            asset = sequence[i % len(sequence)]
            duration = asset.duration if asset.duration else 4.0

            if duration <= remaining:
                sequence.append(asset)
                remaining -= duration
                i += 1
            else:
                break


class VideoComposer:
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        gpu_acceleration: str = "auto",
        preset: str = "fast",
        quality: int = 22,
    ) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffmpeg_path.replace("ffmpeg", "ffprobe")

        if gpu_acceleration == "auto":
            detected_gpu = GPUDetector.detect_available_acceleration()
            gpu_mode: Literal["nvenc", "amf", "qsv", "cpu"] = (
                detected_gpu if detected_gpu != "none" else "cpu"
            )
            self.gpu_acceleration = gpu_mode
        else:
            self.gpu_acceleration = gpu_acceleration  # type: ignore[assignment]

        self.preset = preset
        self.quality = quality

        self.video_codec = GPUDetector.get_codec_name(self.gpu_acceleration)
        self._build_ffmpeg_params()

    def _build_ffmpeg_params(self) -> None:
        """Build FFmpeg encoding parameters based on GPU acceleration."""
        self.video_params: list[str] = ["-c:v", self.video_codec]

        if self.gpu_acceleration == "nvenc":
            nvenc_preset = GPUDetector.get_nvenc_preset(self.preset)
            self.video_params.extend(["-preset", nvenc_preset, "-cq", str(self.quality)])
        elif self.gpu_acceleration == "amf":
            amf_preset = GPUDetector.get_amf_preset(self.preset)
            self.video_params.extend(
                [
                    "-quality",
                    amf_preset,
                    "-rc",
                    "cqp",
                    "-qp_i",
                    str(self.quality),
                    "-qp_p",
                    str(self.quality),
                ]
            )
        elif self.gpu_acceleration == "qsv":
            self.video_params.extend(["-preset", self.preset, "-global_quality", str(self.quality)])
        else:
            self.video_params.extend(
                ["-preset", self.preset, "-crf", str(self.quality), "-threads", "0"]
            )

    def concatenate_clips(self, clips: list[Path], output: Path, target_duration: float) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = output.parent / "temp_concat"
        temp_dir.mkdir(exist_ok=True)

        total_duration = 0.0
        adjusted_clips: list[Path] = []

        for clip_path in clips:
            clip_duration = self.get_duration(clip_path)
            remaining = target_duration - total_duration

            if clip_duration <= remaining:
                adjusted_clips.append(clip_path)
                total_duration += clip_duration
            elif remaining > 0:
                adjusted_clip = temp_dir / f"adjusted_{clip_path.stem}.mp4"
                self._trim_clip(clip_path, adjusted_clip, remaining)
                adjusted_clips.append(adjusted_clip)
                total_duration += remaining

            if total_duration >= target_duration:
                break

        manifest_path = temp_dir / "concat_manifest.txt"
        with manifest_path.open("w") as f:
            for clip in adjusted_clips:
                f.write(f"file '{clip.absolute()}'\n")

        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest_path),
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                str(output),
            ],
            capture_output=True,
            check=True,
            timeout=600,
        )

    def add_audio(self, video_path: Path, audio_path: Path, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-shortest",
                str(output),
            ],
            capture_output=True,
            check=True,
            timeout=300,
        )

    def apply_format(self, video_path: Path, output: Path, format: str) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)

        if format == "short":
            self._apply_vertical_format(video_path, output)
        elif format == "long":
            self._apply_horizontal_format(video_path, output)
        else:
            raise ValueError(f"Unknown format: {format}")

    def apply_format_with_temp(self, video_path: Path, output: Path, format: str) -> None:
        """Apply format using a temporary file to avoid input/output conflict.

        Args:
            video_path: Path to input video
            output: Path where final output should be saved
            format: Target video format (short or long)
        """
        output.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        import tempfile

        with tempfile.NamedTemporaryFile(
            suffix=".mp4", delete=False, dir=output.parent
        ) as temp_file:
            temp_path = output.parent / temp_file.name

            if format == "short":
                self._apply_vertical_format(video_path, temp_path)
            elif format == "long":
                self._apply_horizontal_format(video_path, temp_path)
            else:
                raise ValueError(f"Unknown format: {format}")

            shutil.move(str(temp_path), str(output))

    def get_duration(self, video_path: Path) -> float:
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(video_path),
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

    def _trim_clip(self, input_path: Path, output_path: Path, duration: float) -> None:
        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(input_path),
                "-t",
                str(duration),
                "-c",
                "copy",
                str(output_path),
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )

    def _apply_vertical_format(self, video_path: Path, output: Path) -> None:
        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(video_path),
                "-vf",
                "scale=1080:-2",
                "-pix_fmt",
                "yuv420p",
            ]
            + self.video_params
            + [
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                str(output),
            ],
            capture_output=True,
            check=True,
            timeout=600,
        )

    def _apply_horizontal_format(self, video_path: Path, output: Path) -> None:
        width, height = self._get_video_dimensions(video_path)

        if width == 1920 and height == 1080:
            if video_path != output:
                import shutil

                shutil.copy2(video_path, output)
            return

        scale_filter = "scale=1920:1080"

        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(video_path),
                "-vf",
                scale_filter,
                "-pix_fmt",
                "yuv420p",
            ]
            + self.video_params
            + [
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                str(output),
            ],
            capture_output=True,
            check=True,
            timeout=600,
        )

    def _get_video_dimensions(self, video_path: Path) -> tuple[int, int]:
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height",
                    "-of",
                    "csv=s=x:p=0",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("x")
                if len(parts) == 2:
                    return int(parts[0]), int(parts[1])
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            pass
        return 0, 0


__all__ = ["VideoResult", "StockProvider", "Asset", "LocalAssetsManager", "VideoComposer"]
