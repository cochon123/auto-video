"""FFmpeg video effects.

This module provides reusable FFmpeg effect implementations.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def create_ken_burns_video(
    image_path: Path,
    output_path: Path,
    duration: float = 4.0,
    effect_type: str = "zoom_in",
    zoom_level: float = 1.5,
    ffmpeg_path: str = "ffmpeg",
) -> Path:
    """Convert an image to a video with Ken Burns (pan/zoom) effect.

    This is the canonical implementation of the Ken Burns effect.
    All other code should use this function.

    Args:
        image_path: Path to the source image.
        output_path: Path where the video should be saved.
        duration: Target video duration in seconds.
        effect_type: Type of effect - zoom_in, zoom_out, pan_left, pan_right, diagonal
        zoom_level: Maximum zoom level (1.05 to 2.0)
        ffmpeg_path: Path to ffmpeg executable

    Returns:
        Path to the generated video

    Raises:
        FileNotFoundError: If image_path doesn't exist
        RuntimeError: If FFmpeg fails
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Clamp zoom level to reasonable bounds
    clamped_zoom = max(1.05, min(zoom_level, 2.0))
    total_frames = max(int(duration * 30), 1)

    # Set up zoom and pan expressions based on effect type
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

    # First, scale the image to 1920x1080 with padding if needed
    scaled_path = output_path.parent / f"{output_path.stem}_scaled.jpg"

    try:
        subprocess.run(
            [
                ffmpeg_path,
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
    except subprocess.CalledProcessError as e:
        logger.error("[KenBurns] Failed to scale image: %s", e.stderr.decode() if e.stderr else e)
        raise RuntimeError(f"Failed to scale image: {e}") from e

    # Create video with Ken Burns effect using zoompan filter
    try:
        subprocess.run(
            [
                ffmpeg_path,
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
    except subprocess.CalledProcessError as e:
        logger.error("[KenBurns] Failed to create video: %s", e.stderr.decode() if e.stderr else e)
        raise RuntimeError(f"Failed to create Ken Burns video: {e}") from e
    finally:
        # Clean up scaled image
        scaled_path.unlink(missing_ok=True)

    # Verify the output video was created and has content
    if not output_path.exists() or output_path.stat().st_size < 1000:
        raise RuntimeError(f"Output video is invalid or empty: {output_path}")

    logger.debug("[KenBurns] Created video: %s", output_path)
    return output_path


__all__ = ["create_ken_burns_video"]
