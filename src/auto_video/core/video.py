"""Video core module.

This module now contains only LocalAssetsManager and VideoComposer.
The base provider classes have been moved to core.providers.base.
For backwards compatibility, these classes are re-exported.
"""

from __future__ import annotations

import logging
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from auto_video.core.providers.base import Asset, ImageResult, StockProvider, VideoResult
from auto_video.utils.gpu import GPUDetector

logger = logging.getLogger(__name__)

# Re-export for backwards compatibility
__all__ = ["VideoResult", "ImageResult", "StockProvider", "Asset", "LocalAssetsManager", "VideoComposer"]


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

    def _normalize_clip(self, input_path: Path, output_path: Path) -> None:
        """Normalize a video clip to standard properties.

        Standard properties:
        - Codec: h264
        - Resolution: 640x360 (landscape)
        - Frame rate: 30 fps
        - Pixel format: yuv420p
        - No audio track

        Args:
            input_path: Path to input video file
            output_path: Path for normalized output video
        """
        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(input_path),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-vf",
                "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,fps=30",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "30",
                "-an",
                str(output_path),
            ],
            capture_output=True,
            check=True,
            timeout=120,
        )

    def _extract_video_stream(self, input_path: Path, output_path: Path) -> None:
        """Extract only the video stream from a file.

        Removes any audio tracks and ensures clean video-only file.

        Args:
            input_path: Path to input video file
            output_path: Path for video-only output
        """
        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(input_path),
                "-c:v",
                "copy",
                "-an",
                str(output_path),
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )

    def concatenate_clips(self, clips: list[Path], output: Path, target_duration: float) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = output.parent / "temp_concat"
        temp_dir.mkdir(exist_ok=True)

        logger.info(
            "[VideoComposer] Concatenating %d clips to %s (target_duration=%.2fs)",
            len(clips),
            output.name,
            target_duration,
        )

        total_duration = 0.0
        normalized_clips: list[Path] = []

        for i, clip_path in enumerate(clips):
            clip_duration = self.get_duration(clip_path)
            remaining = target_duration - total_duration

            logger.debug(
                "[VideoComposer] Processing clip %d: %s (%.2fs), remaining: %.2fs",
                i + 1,
                clip_path.name,
                clip_duration,
                remaining,
            )

            if remaining <= 0:
                logger.debug("[VideoComposer] Target duration reached, stopping")
                break

            if clip_duration <= remaining:
                normalized_clip = temp_dir / f"normalized_{clip_path.stem}.mp4"
                self._normalize_clip(clip_path, normalized_clip)
                normalized_clips.append(normalized_clip)
                total_duration += clip_duration
                logger.debug("[VideoComposer] Added full clip: %.2fs (total: %.2fs)", clip_duration, total_duration)
            elif remaining > 0:
                temp_clip = temp_dir / f"temp_{clip_path.stem}.mp4"
                self._trim_clip(clip_path, temp_clip, remaining)
                normalized_clip = temp_dir / f"normalized_{clip_path.stem}.mp4"
                self._normalize_clip(temp_clip, normalized_clip)
                normalized_clips.append(normalized_clip)
                total_duration += remaining
                logger.debug("[VideoComposer] Added trimmed clip: %.2fs (total: %.2fs)", remaining, total_duration)

            if total_duration >= target_duration:
                break

        logger.info(
            "[VideoComposer] Concatenating %d normalized clips (total_duration=%.2fs)",
            len(normalized_clips),
            total_duration,
        )

        manifest_path = temp_dir / "concat_manifest.txt"
        with manifest_path.open("w") as f:
            for clip in normalized_clips:
                f.write(f"file '{clip.absolute()}'\n")

        logger.debug("[VideoComposer] Running ffmpeg concat...")
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
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "30",
                str(output),
            ],
            capture_output=True,
            check=True,
            timeout=600,
        )
        logger.info("[VideoComposer] ✓ Concatenation complete: %s", output)

    def add_audio(self, video_path: Path, audio_path: Path, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "[VideoComposer] Adding audio to video: video=%s, audio=%s, output=%s",
            video_path.name,
            audio_path.name,
            output.name,
        )

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

        logger.info("[VideoComposer] ✓ Audio added successfully")

    def trim_video_to_duration(
        self, video_path: Path, output_path: Path, target_duration: float
    ) -> None:
        """Trim video to match target audio duration.

        If video is longer than target_duration, cut it to match.
        This ensures video length matches audio length for proper sync.

        Args:
            video_path: Path to input video file.
            output_path: Path to save trimmed video.
            target_duration: Target duration in seconds.
        """
        video_duration = self.get_duration(video_path)

        if video_duration <= target_duration:
            logger.info(
                "[VideoComposer] Video duration (%.2fs) matches or is shorter than audio (%.2fs), no trim needed",
                video_duration,
                target_duration,
            )
            if video_path != output_path:
                shutil.copy2(video_path, output_path)
            return

        logger.info("[VideoComposer] Trimming video from %.2fs to %.2fs", video_duration, target_duration)

        final_output = output_path
        temp_output = output_path
        if video_path == output_path:
            temp_output = output_path.with_name(f"{output_path.stem}.trimmed{output_path.suffix}")

        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(video_path),
                "-t",
                str(target_duration),
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                str(temp_output),
            ],
            capture_output=True,
            check=True,
            timeout=600,
        )

        if temp_output != final_output:
            shutil.move(str(temp_output), str(final_output))

        logger.info("[VideoComposer] ✓ Video trimmed to %.2fs", target_duration)

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
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
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
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "30",
                "-an",
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

    # ==================== NEW ENHANCED METHODS ====================

    def create_ken_burns_effect(
        self,
        image_path: Path,
        output_path: Path,
        effect_type: str = "zoom_in",
        duration: float = 4.0,
        zoom_level: float = 1.5
    ) -> None:
        """Create a Ken Burns effect with several pan/zoom variants."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        scaled_path = output_path.parent / f"{output_path.stem}_scaled.jpg"
        clamped_zoom = max(1.05, min(zoom_level, 2.0))
        total_frames = max(int(duration * 30), 1)

        zoom_expr = "1.0"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"

        if effect_type == "zoom_in":
            zoom_expr = f"min(zoom+0.0015*{clamped_zoom:.2f}, {clamped_zoom:.2f})"
        elif effect_type == "zoom_out":
            zoom_expr = f"if(eq(on,1),{clamped_zoom:.2f},max(zoom-0.0015,1.0))"
        elif effect_type == "pan_left":
            zoom_expr = "1.1"
            x_expr = f"(iw-iw/zoom)*(1-on/{total_frames})"
        elif effect_type == "pan_right":
            zoom_expr = "1.1"
            x_expr = f"(iw-iw/zoom)*(on/{total_frames})"
        elif effect_type == "diagonal":
            zoom_expr = f"min(zoom+0.0012*{clamped_zoom:.2f}, {clamped_zoom:.2f})"
            x_expr = f"(iw-iw/zoom)*(on/{total_frames})"
            y_expr = f"(ih-ih/zoom)*(on/{total_frames})"

        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(image_path),
                "-vf",
                "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                "-qscale:v",
                "2",
                str(scaled_path),
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )

        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-loop",
                "1",
                "-i",
                str(scaled_path),
                "-vf",
                f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d=1:s=1920x1080:fps=30",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-t",
                str(duration),
                "-pix_fmt",
                "yuv420p",
                "-r",
                "30",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            capture_output=True,
            check=True,
            timeout=120,
        )
        scaled_path.unlink(missing_ok=True)

    def apply_transition(
        self,
        clip1_path: Path,
        clip2_path: Path,
        output_path: Path,
        transition_type: str = "fade",
        duration: float = 1.0
    ) -> None:
        """
        Apply a transition between two clips.

        Args:
            clip1_path: First clip
            clip2_path: Second clip
            output_path: Output video
            transition_type: fade, dissolve, wipeleft, wiperight, etc.
            duration: Transition duration
        """
        # Get duration of first clip
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-v", "error", "-show_entries",
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                 str(clip1_path)],
                capture_output=True, text=True, timeout=10
            )
            clip1_duration = float(result.stdout.strip())
            offset = max(0, clip1_duration - duration)
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            offset = duration

        filter_complex = (
            f"[0:v][1:v]xfade=transition={transition_type}:duration={duration}:offset={offset}[vout];"
            f"[0:a][1:a]acrossfade=d={duration}[aout]"
        )
        try:
            subprocess.run(
                [
                    self.ffmpeg_path,
                    "-y",
                    "-i",
                    str(clip1_path),
                    "-i",
                    str(clip2_path),
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "[vout]",
                    "-map",
                    "[aout]",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(output_path),
                ],
                capture_output=True,
                check=True,
                timeout=120,
            )
        except subprocess.CalledProcessError:
            subprocess.run(
                [
                    self.ffmpeg_path,
                    "-y",
                    "-i",
                    str(clip1_path),
                    "-i",
                    str(clip2_path),
                    "-filter_complex",
                    f"[0:v][1:v]xfade=transition={transition_type}:duration={duration}:offset={offset}[vout]",
                    "-map",
                    "[vout]",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                    str(output_path),
                ],
                capture_output=True,
                check=True,
                timeout=120,
            )

    def add_animated_text(
        self,
        video_path: Path,
        text: str,
        output_path: Path,
        position: str = "bottom",
        animation: str = "fade_in_out"
    ) -> None:
        """
        Add animated text to a video.

        Args:
            video_path: Source video
            text: Text to display
            output_path: Output video
            position: top, bottom, center
            animation: fade_in_out, slide_up
        """
        position_map = {
            "top": "50",
            "bottom": "h-th-50",
            "center": "(h-th)/2"
        }

        clip_duration = self.get_duration(video_path) or 4.0
        fade_window = min(1.0, max(0.3, clip_duration * 0.15))
        safe_text = (
            text.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", r"\'")
            .replace("%", r"\%")
            .replace("\n", " ")
        )
        alpha_expr = (
            f"alpha='if(lt(t,{fade_window:.2f}),t/{fade_window:.2f},"
            f"if(gt(t,{max(clip_duration - fade_window, 0.0):.2f}),"
            f"({clip_duration:.2f}-t)/{fade_window:.2f},1))'"
        )

        subprocess.run(
            [
                self.ffmpeg_path, "-y",
                "-i", str(video_path),
                "-vf",
                f"drawtext=text='{safe_text}':fontsize=48:fontcolor=white:"
                f"x=(w-tw)/2:y={position_map.get(position, position_map['bottom'])}:"
                f"{alpha_expr}:box=1:boxcolor=black@0.5:boxborderw=5",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                str(output_path)
            ],
            capture_output=True,
            check=True,
            timeout=120
        )

    def mix_audio_tracks(
        self,
        video_path: Path,
        voiceover_path: Path,
        music_path: Path | None = None,
        sound_effects: list[tuple[Path, float]] | None = None,
        output_path: Path | None = None,
        music_volume: float = 0.3,
        voice_volume: float = 1.0
    ) -> Path:
        """
        Mix multiple audio tracks together.

        Args:
            video_path: Video with original audio
            voiceover_path: Voiceover file
            music_path: (optional) Background music
            sound_effects: (optional) List of (path, start_time)
            output_path: Output video path (defaults to video_path)
            music_volume: Music volume (0.0 to 1.0)
            voice_volume: Voiceover volume (0.0 to 1.0)

        Returns:
            Path to output video
        """
        if output_path is None:
            output_path = video_path

        inputs = ["-i", str(video_path), "-i", str(voiceover_path)]
        filter_parts: list[str] = []
        mix_inputs: list[str] = []

        if self._has_audio_stream(video_path):
            filter_parts.append("[0:a]volume=0.15[video_audio]")
            mix_inputs.append("[video_audio]")
        filter_parts.extend(
            [
            f"[1:a]volume={voice_volume}[voice]"
            ]
        )
        mix_inputs.append("[voice]")

        input_idx = 2

        # Add music
        if music_path:
            inputs.extend(["-i", str(music_path)])
            filter_parts.append(
                f"[{input_idx}:a]volume={music_volume},"
                f"aloop=loop=-1:size=2e+09[music]"
            )
            mix_inputs.append("[music]")
            input_idx += 1

        # Add sound effects
        sfx_inputs = []
        if sound_effects:
            for sfx_path, start_time in sound_effects:
                inputs.extend(["-i", str(sfx_path)])
                delay_ms = int(start_time * 1000)
                filter_parts.append(
                    f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[sfx{input_idx}]"
                )
                sfx_inputs.append(f"[sfx{input_idx}]")
                input_idx += 1

        # Mix all tracks
        all_inputs = "".join(mix_inputs) + "".join(sfx_inputs)
        num_tracks = len(mix_inputs) + len(sfx_inputs or [])
        filter_parts.append(
            f"{all_inputs}amix=inputs={num_tracks}:duration=first[outa]"
        )

        subprocess.run(
            [
                self.ffmpeg_path, "-y",
                *inputs,
                "-filter_complex", ";".join(filter_parts),
                "-map", "0:v",
                "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(output_path)
            ],
            capture_output=True,
            check=True,
            timeout=600
        )

        return output_path

    def concatenate_with_transitions(
        self,
        clips: list[Path],
        output: Path,
        total_duration: float,
        transition_duration: float = 1.0,
        transition_type: str = "fade"
    ) -> None:
        """
        Concatenate clips with transitions between them.

        Args:
            clips: List of clip paths
            output: Output video path
            total_duration: Total target duration
            transition_duration: Duration of each transition
            transition_type: Type of transition
        """
        if len(clips) < 2:
            # Single clip, just copy
            shutil.copy(clips[0], output)
            final_duration = self.get_duration(output)
            if final_duration < total_duration:
                self.extend_video_to_duration(output, output, total_duration)
            return

        temp_dir = output.parent / "transition_concat"
        temp_dir.mkdir(parents=True, exist_ok=True)
        current_output = clips[0]
        intermediates: list[Path] = []

        try:
            for index, next_clip in enumerate(clips[1:], start=1):
                merged = temp_dir / f"transition_{index:03d}.mp4"
                self.apply_transition(
                    current_output,
                    next_clip,
                    merged,
                    transition_type=transition_type,
                    duration=transition_duration,
                )
                intermediates.append(merged)
                current_output = merged

            final_duration = self.get_duration(current_output)
            if final_duration > total_duration:
                self.trim_video_to_duration(current_output, output, total_duration)
            elif final_duration < total_duration:
                self.extend_video_to_duration(current_output, output, total_duration)
            else:
                shutil.copy2(current_output, output)
        except Exception:
            concat_file = output.parent / "concat_fallback.txt"
            with open(concat_file, "w") as f:
                for clip in clips:
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
                    str(concat_file),
                    "-c",
                    "copy",
                    str(output),
                ],
                capture_output=True,
                check=True,
                timeout=600,
            )
            final_duration = self.get_duration(output)
            if final_duration < total_duration:
                self.extend_video_to_duration(output, output, total_duration)

    def extend_video_to_duration(self, input_path: Path, output_path: Path, target_duration: float) -> Path:
        """Freeze the last frame so a clip reaches the requested duration."""
        current_duration = self.get_duration(input_path)
        if current_duration >= target_duration:
            if input_path != output_path:
                shutil.copy2(input_path, output_path)
            return output_path

        pad_duration = max(target_duration - current_duration, 0.0)
        temp_output = output_path
        if input_path == output_path:
            temp_output = output_path.with_name(f"{output_path.stem}_padded{output_path.suffix}")

        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(input_path),
                "-vf",
                f"tpad=stop_mode=clone:stop_duration={pad_duration:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(temp_output),
            ],
            capture_output=True,
            check=True,
            timeout=300,
        )

        if temp_output != output_path:
            shutil.move(temp_output, output_path)
        return output_path

    def _has_audio_stream(self, video_path: Path) -> bool:
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=codec_type",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and result.stdout.strip() == "audio"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


__all__ = ["VideoResult", "StockProvider", "Asset", "LocalAssetsManager", "VideoComposer"]
