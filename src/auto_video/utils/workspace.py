"""Workspace management for video creation."""

import shutil
import uuid
from datetime import datetime
from pathlib import Path

from auto_video.utils.security import sanitize_path_component


class Workspace:
    """Manages temporary workspace for a single video."""

    def __init__(self, base_path: Path, video_id: str | None = None) -> None:
        if video_id is not None:
            video_id = sanitize_path_component(video_id)
        self._base_path = base_path
        self._video_id = video_id if video_id else self._generate_video_id()
        self._created = False

    def _generate_video_id(self) -> str:
        """Generate a unique video ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{random_id}"

    @property
    def video_id(self) -> str:
        """Get the video ID."""
        return self._video_id

    @property
    def workspace_path(self) -> Path:
        """Get the workspace directory path."""
        return self._base_path / self._video_id

    @property
    def script_path(self) -> Path:
        """Get path for the script file."""
        return self.workspace_path / "script.txt"

    @property
    def brief_path(self) -> Path:
        """Get path for the structured video brief."""
        return self.workspace_path / "brief.json"

    @property
    def research_path(self) -> Path:
        """Get path for the research bundle."""
        return self.workspace_path / "research.json"

    @property
    def script_plan_path(self) -> Path:
        """Get path for the structured script plan."""
        return self.workspace_path / "script_plan.json"

    @property
    def scene_plan_path(self) -> Path:
        """Get path for the structured scene plan."""
        return self.workspace_path / "scene_plan.json"

    @property
    def asset_collection_path(self) -> Path:
        """Get path for the visual asset collection report."""
        return self.workspace_path / "asset_collection.json"

    @property
    def audio_path(self) -> Path:
        """Get path for the generated audio file."""
        return self.workspace_path / "audio.wav"

    @property
    def video_raw_path(self) -> Path:
        """Get path for the raw video file (before subtitles)."""
        return self.workspace_path / "video_raw.mp4"

    @property
    def subtitles_path(self) -> Path:
        """Get path for the subtitles file."""
        return self.workspace_path / "subtitles.srt"

    @property
    def thumbnail_path(self) -> Path:
        """Get path for the thumbnail image."""
        return self.workspace_path / "thumbnail.png"

    @property
    def final_path(self) -> Path:
        """Get path for the final video file."""
        return self.workspace_path / "final.mp4"

    @property
    def logs_path(self) -> Path:
        """Get path for the logs file."""
        return self.workspace_path / "generation.log"

    @property
    def state_path(self) -> Path:
        """Get path for the pipeline state file."""
        return self.workspace_path / "state.json"

    @property
    def visual_keywords_debug_path(self) -> Path:
        """Get path for the visual keywords JSON debug file."""
        return self.workspace_path / "visual_keywords_raw.json"

    @property
    def visual_asset_log_path(self) -> Path:
        """Get path for the visual asset resolution log."""
        return self.workspace_path / "visual_asset_log.jsonl"

    @property
    def assets_dir(self) -> Path:
        """Get the base assets directory."""
        return self.workspace_path / "assets"

    @property
    def assets_video_dir(self) -> Path:
        """Get the video assets directory."""
        return self.assets_dir / "video"

    @property
    def assets_image_dir(self) -> Path:
        """Get the image assets directory."""
        return self.assets_dir / "image"

    @property
    def assets_music_dir(self) -> Path:
        """Get the music assets directory."""
        return self.assets_dir / "audio" / "music"

    @property
    def assets_sfx_dir(self) -> Path:
        """Get the sound effects assets directory."""
        return self.assets_dir / "audio" / "sfx"

    @property
    def assets_remotion_dir(self) -> Path:
        """Get the Remotion assets directory."""
        return self.assets_dir / "remotion"

    @property
    def manifest_dir(self) -> Path:
        """Get the manifest directory."""
        return self.workspace_path / "manifest"

    @property
    def manifest_path(self) -> Path:
        """Get the video manifest file path."""
        return self.manifest_dir / "video_manifest.json"

    def create(self) -> None:
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.workspace_path.chmod(0o755)
        self.assets_video_dir.mkdir(parents=True, exist_ok=True)
        self.assets_image_dir.mkdir(parents=True, exist_ok=True)
        self.assets_music_dir.mkdir(parents=True, exist_ok=True)
        self.assets_sfx_dir.mkdir(parents=True, exist_ok=True)
        self.assets_remotion_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self._created = True

    def cleanup(self, keep_artifacts: bool = False) -> None:
        """Remove the workspace directory.

        Args:
            keep_artifacts: If True, only remove temp files, keep final artifacts.
        """
        if not self._created:
            return

        if keep_artifacts:
            self._cleanup_temp_only()
        else:
            shutil.rmtree(self.workspace_path, ignore_errors=True)

    def _cleanup_temp_only(self) -> None:
        """Remove only temporary files, keep final artifacts."""
        temp_files = [
            self.audio_path,
            self.video_raw_path,
            self.subtitles_path,
            self.logs_path,
            self.state_path,
        ]

        for path in temp_files:
            if path.exists():
                path.unlink()

    def list_artifacts(self) -> dict[str, Path]:
        """List all artifacts in the workspace.

        Returns:
            Dictionary mapping artifact names to their paths.
        """
        artifacts = {}

        if self.script_path.exists():
            artifacts["script"] = self.script_path

        if self.brief_path.exists():
            artifacts["brief"] = self.brief_path

        if self.research_path.exists():
            artifacts["research"] = self.research_path

        if self.script_plan_path.exists():
            artifacts["script_plan"] = self.script_plan_path

        if self.scene_plan_path.exists():
            artifacts["scene_plan"] = self.scene_plan_path

        if self.asset_collection_path.exists():
            artifacts["asset_collection"] = self.asset_collection_path

        if self.audio_path.exists():
            artifacts["audio"] = self.audio_path

        if self.video_raw_path.exists():
            artifacts["video_raw"] = self.video_raw_path

        if self.subtitles_path.exists():
            artifacts["subtitles"] = self.subtitles_path

        if self.thumbnail_path.exists():
            artifacts["thumbnail"] = self.thumbnail_path

        if self.final_path.exists():
            artifacts["final"] = self.final_path

        if self.logs_path.exists():
            artifacts["logs"] = self.logs_path

        if self.state_path.exists():
            artifacts["state"] = self.state_path

        if self.manifest_path.exists():
            artifacts["manifest"] = self.manifest_path

        if self.visual_asset_log_path.exists():
            artifacts["visual_asset_log"] = self.visual_asset_log_path

        return artifacts

    def get_file_size(self, artifact: str) -> int:
        """Get the size of an artifact in bytes.

        Args:
            artifact: Name of the artifact (e.g., "final", "audio").

        Returns:
            Size in bytes, or 0 if artifact doesn't exist.
        """
        path: Path | None = getattr(self, f"{artifact}_path", None)
        if path is None or not path.exists():
            return 0
        return path.stat().st_size

    def copy_to_output(self, output_dir: Path, artifact: str = "final") -> Path:
        """Copy an artifact to an output directory.

        Args:
            output_dir: Destination directory.
            artifact: Name of the artifact to copy (default: "final").

        Returns:
            Path to the copied file.
        """
        source: Path = getattr(self, f"{artifact}_path")
        if not source.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact}")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / source.name
        shutil.copy2(source, output_path)
        return output_path
