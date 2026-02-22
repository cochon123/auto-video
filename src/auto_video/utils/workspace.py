"""Workspace management for video creation."""

import shutil
import uuid
from datetime import datetime
from pathlib import Path


class Workspace:
    """Manages temporary workspace for a single video."""

    def __init__(self, base_path: Path, video_id: str | None = None) -> None:
        """Initialize workspace.

        Args:
            base_path: Base path for all workspaces.
            video_id: Optional video ID. If None, generates a unique ID.
        """
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

    def create(self) -> None:
        """Create the workspace directory structure."""
        self.workspace_path.mkdir(parents=True, exist_ok=True)
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

        return artifacts

    def get_file_size(self, artifact: str) -> int:
        """Get the size of an artifact in bytes.

        Args:
            artifact: Name of the artifact (e.g., "final", "audio").

        Returns:
            Size in bytes, or 0 if artifact doesn't exist.
        """
        path = getattr(self, f"{artifact}_path", None)
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
        source = getattr(self, f"{artifact}_path")
        if not source.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact}")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / source.name
        shutil.copy2(source, output_path)
        return output_path
