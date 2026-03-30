"""
Python bridge to Remotion for rendering motion graphics.

This module provides a Python interface to render Remotion compositions.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

from auto_video.domain import RemotionSpec
from auto_video.remotion.registry import get_registry


class RemotionRenderer:
    """
    Interface Python vers Remotion.

    This class provides methods to render Remotion compositions
    from Python code.
    """

    def __init__(self, project_path: Path):
        """
        Initialize the Remotion renderer.

        Args:
            project_path: Path to the Remotion project (containing package.json)
        """
        self.project_path = project_path
        self.node_modules = project_path / "node_modules"
        self.entry_point = project_path / "index.ts"

    def render(
        self,
        composition_id: str,
        output_path: Path,
        props: dict[str, Any],
        remotion_spec: RemotionSpec | None = None,
        codec: str = "h264",
        crf: int = 18,
        preset: str = "slow",
        image_format: str = "jpeg"
    ) -> Path:
        """
        Render a Remotion composition to video.

        Args:
            composition_id: ID of the composition (e.g., "Intro")
            output_path: Output video path
            props: Props to pass to the composition
            codec: Video codec (h264, h265, prores)
            crf: Quality factor (18 = excellent, 28 = good)
            preset: Encoding preset (slow, medium, fast)
            image_format: Intermediate image format (jpeg, png)

        Returns:
            Path to the generated video
        """
        registry = get_registry()
        normalized_spec = registry.normalize_spec(
            remotion_spec
            or RemotionSpec(
                composition_id=composition_id,
                props=props,
                render_settings={
                    "fps": 30,
                    "width": 1920,
                    "height": 1080,
                    "duration_in_frames": None,
                },
            )
        )

        # Create a temporary file for props
        props_file = output_path.parent / f"{composition_id}_props.json"
        with open(props_file, "w") as f:
            json.dump(normalized_spec.props, f)

        cmd = [
            "npx",
            "remotion",
            "render",
            str(self.entry_point),
            composition_id,
            "--props", str(props_file),
            "--output", str(output_path),
            "--codec", codec,
            "--crf", str(crf),
            "--preset", preset,
            "--image-format", image_format,
            "--fps", str(normalized_spec.render_settings.fps),
            "--width", str(normalized_spec.render_settings.width),
            "--height", str(normalized_spec.render_settings.height),
            "--duration", str(normalized_spec.render_settings.duration_in_frames or 1),
            "--overwrite",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes max
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Remotion render failed: {result.stderr}\n{result.stdout}"
                )

            return output_path

        finally:
            # Clean up props file
            if props_file.exists():
                props_file.unlink()

    def render_still(
        self,
        composition_id: str,
        output_path: Path,
        props: dict[str, Any],
        remotion_spec: RemotionSpec | None = None,
        frame: int = 0
    ) -> Path:
        """
        Render a single still frame from a composition.

        Useful for generating thumbnails or previews.

        Args:
            composition_id: ID of the composition
            output_path: Output image path
            props: Props to pass to the composition
            frame: Frame number to render (default: 0)

        Returns:
            Path to the generated image
        """
        normalized_spec = get_registry().normalize_spec(
            remotion_spec
            or RemotionSpec(
                composition_id=composition_id,
                props=props,
                render_settings={
                    "fps": 30,
                    "width": 1920,
                    "height": 1080,
                    "duration_in_frames": None,
                },
            )
        )
        props_file = output_path.parent / f"{composition_id}_props.json"
        with open(props_file, "w") as f:
            json.dump(normalized_spec.props, f)

        cmd = [
            "npx",
            "remotion",
            "still",
            str(self.entry_point),
            composition_id,
            "--props", str(props_file),
            "--output", str(output_path),
            "--fps", str(normalized_spec.render_settings.fps),
            "--width", str(normalized_spec.render_settings.width),
            "--height", str(normalized_spec.render_settings.height),
            "--duration", str(normalized_spec.render_settings.duration_in_frames or 1),
            "--frame", str(frame)
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Remotion still failed: {result.stderr}\n{result.stdout}"
                )

            return output_path

        finally:
            if props_file.exists():
                props_file.unlink()

    def get_composition_duration(
        self,
        composition_id: str,
        props: dict[str, Any] | None = None
    ) -> int:
        """
        Get the duration in frames of a composition.

        Args:
            composition_id: ID of the composition
            props: Optional props (may affect duration)

        Returns:
            Duration in frames
        """
        try:
            return get_registry().get_default_duration(composition_id, props)
        except KeyError:
            return 90

    def check_available(self) -> bool:
        """
        Check if Remotion is available and properly installed.

        Returns:
            True if Remotion is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["npx", "remotion", "versions"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


# Singleton instance for the project
_renderer_instance: Optional[RemotionRenderer] = None


def get_renderer() -> RemotionRenderer:
    """
    Get the singleton Remotion renderer instance.

    Returns:
        The RemotionRenderer instance
    """
    global _renderer_instance

    if _renderer_instance is None:
        # Path to this file's directory
        remotion_dir = Path(__file__).parent.absolute()
        _renderer_instance = RemotionRenderer(remotion_dir)

    return _renderer_instance
