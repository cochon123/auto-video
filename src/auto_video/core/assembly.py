"""Assembly engine for multi-agent video manifests."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from auto_video.core.video import VideoComposer
from auto_video.manifest import VideoManifest, save_manifest
from auto_video.manifest.schema import TimelineAsset
from auto_video.remotion import get_renderer
from auto_video.utils.workspace import Workspace

logger = logging.getLogger(__name__)


class AssemblyEngine:
    """Render a final video from a structured manifest."""

    AUDIO_SYNC_TOLERANCE_S = 0.25

    def __init__(self, composer: VideoComposer | None = None) -> None:
        self.composer = composer or VideoComposer()

    def render_from_manifest(
        self,
        manifest: VideoManifest,
        workspace: Workspace,
        audio_path: Path,
        output_path: Path,
        video_format: str,
    ) -> Path:
        workspace.create()
        clip_paths: list[Path] = []
        audio_duration = self._safe_duration(audio_path)
        planning_duration = self._planning_duration(manifest)
        if audio_duration is None or audio_duration <= 0:
            fallback_audio = manifest.metadata.get("actual_audio_duration_s")
            if isinstance(fallback_audio, (int, float)) and fallback_audio > 0:
                audio_duration = float(fallback_audio)
            else:
                raise ValueError("Audio duration is required for final assembly")

        for scene in manifest.scenes:
            if scene.render_mode == "remotion":
                clip_paths.append(self._render_remotion_scene(scene, workspace))
            else:
                clip_paths.append(self._render_scene(scene, workspace))

        if not clip_paths:
            raise ValueError("Manifest does not contain any renderable scenes")

        self.composer.concatenate_with_transitions(
            clip_paths,
            workspace.video_raw_path,
            planning_duration,
        )
        raw_duration = self._safe_duration(workspace.video_raw_path)
        logger.info(
            "[Assembly] Duration planning=%.2fs, audio=%.2fs, raw_before_sync=%s",
            planning_duration,
            audio_duration,
            f"{raw_duration:.2f}s" if raw_duration is not None else "unknown",
        )
        self._normalize_video_to_audio(workspace.video_raw_path, audio_duration)
        normalized_duration = self._safe_duration(workspace.video_raw_path)
        logger.info(
            "[Assembly] Raw video normalized to audio: raw_after_sync=%s",
            f"{normalized_duration:.2f}s" if normalized_duration is not None else "unknown",
        )
        self.composer.add_audio(workspace.video_raw_path, audio_path, output_path)
        try:
            self.composer.apply_format_with_temp(output_path, output_path, video_format)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            logger.warning(
                "[Assembly] Hardware formatting failed, retrying with CPU encoder: %s",
                exc,
            )
            fallback_composer = VideoComposer(
                ffmpeg_path=self.composer.ffmpeg_path,
                gpu_acceleration="cpu",
                preset=self.composer.preset,
                quality=self.composer.quality,
            )
            fallback_composer.apply_format_with_temp(output_path, output_path, video_format)

        final_duration = self._safe_duration(output_path) or audio_duration
        manifest.output_video = str(output_path)
        manifest.total_duration_s = max(final_duration, 0.1)
        manifest.metadata.update(
            {
                "planning_target_duration_s": round(float(planning_duration), 2),
                "actual_audio_duration_s": round(float(audio_duration), 2),
                "actual_video_duration_s": round(float(final_duration), 2),
            }
        )
        logger.info(
            "[Assembly] Final duration after mux/format: %.2fs",
            final_duration,
        )
        save_manifest(manifest, workspace.manifest_path)
        return output_path

    def _render_scene(self, scene, workspace: Workspace) -> Path:
        if not scene.assets:
            raise ValueError(f"Scene {scene.scene_id} has no resolved assets")

        scene_output_dir = workspace.assets_dir / "assembled" / scene.scene_id
        scene_output_dir.mkdir(parents=True, exist_ok=True)
        scene_output = scene_output_dir / f"{scene.scene_id}.mp4"
        ordered_assets = self._ordered_assets(scene.assets)
        scene_duration = self._scene_duration(scene)

        if len(ordered_assets) == 1:
            asset_path = Path(ordered_assets[0].path)
            self.composer.trim_video_to_duration(asset_path, scene_output, scene_duration)
            logger.info(
                "[Assembly] Scene %s rendered from 1 asset -> %s",
                scene.scene_id,
                scene_output,
            )
            return scene_output

        segment_paths: list[Path] = []
        for index, asset in enumerate(ordered_assets):
            asset_input = Path(asset.path)
            if not asset_input.exists():
                raise FileNotFoundError(f"Scene asset not found: {asset_input}")

            segment_duration = self._asset_duration(asset)
            segment_output = scene_output_dir / f"{index:02d}_{asset.asset_id}.mp4"
            self.composer.trim_video_to_duration(asset_input, segment_output, segment_duration)
            segment_paths.append(segment_output)

        transition_duration = min(1.0, max(scene_duration / max(len(segment_paths) * 6, 1), 0.25))
        self.composer.concatenate_with_transitions(
            segment_paths,
            scene_output,
            scene_duration,
            transition_duration=transition_duration,
        )
        rendered_scene_duration = self._safe_duration(scene_output)
        if rendered_scene_duration is not None and rendered_scene_duration > scene_duration:
            self.composer.trim_video_to_duration(scene_output, scene_output, scene_duration)
        elif rendered_scene_duration is not None and rendered_scene_duration < scene_duration and hasattr(self.composer, "extend_video_to_duration"):
            self.composer.extend_video_to_duration(scene_output, scene_output, scene_duration)
        logger.info(
            "[Assembly] Scene %s rendered from %d assets -> %s",
            scene.scene_id,
            len(segment_paths),
            scene_output,
        )
        return scene_output

    def _safe_duration(self, media_path: Path) -> float | None:
        get_duration = getattr(self.composer, "get_duration", None)
        if get_duration is None:
            return self._probe_duration(media_path)
        try:
            duration = get_duration(media_path)
        except Exception:
            return self._probe_duration(media_path)
        if isinstance(duration, (int, float)) and duration > 0:
            return float(duration)
        return self._probe_duration(media_path)

    def _probe_duration(self, media_path: Path) -> float | None:
        try:
            result = subprocess.run(
                [
                    getattr(self.composer, "ffprobe_path", "ffprobe"),
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(media_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if result.returncode != 0 or not result.stdout.strip():
            return None
        try:
            return float(result.stdout.strip())
        except ValueError:
            return None

    def _planning_duration(self, manifest: VideoManifest) -> float:
        metadata_duration = manifest.metadata.get("planning_target_duration_s")
        if isinstance(metadata_duration, (int, float)) and metadata_duration > 0:
            return float(metadata_duration)
        return max(float(manifest.total_duration_s), 0.1)

    def _normalize_video_to_audio(self, video_path: Path, audio_duration: float) -> None:
        current_duration = self._safe_duration(video_path)
        if current_duration is None:
            logger.warning(
                "[Assembly] Could not measure raw video duration before audio mux; skipping pre-mux normalization"
            )
            return
        delta = current_duration - audio_duration
        if abs(delta) <= self.AUDIO_SYNC_TOLERANCE_S:
            return
        if delta > 0:
            self.composer.trim_video_to_duration(video_path, video_path, audio_duration)
            return
        if hasattr(self.composer, "extend_video_to_duration"):
            self.composer.extend_video_to_duration(video_path, video_path, audio_duration)

    def _render_remotion_scene(self, scene, workspace: Workspace) -> Path:
        renderer = get_renderer()
        if not renderer.check_available():
            raise RuntimeError(
                "Remotion is required for this scene but is not available. "
                "Install dependencies in src/auto_video/remotion."
            )

        if not scene.remotion_composition:
            raise ValueError(f"Scene {scene.scene_id} is remotion but has no composition")

        output_path = workspace.assets_remotion_dir / f"{scene.scene_id}.mp4"
        composition_id = (
            scene.remotion_spec.composition_id
            if getattr(scene, "remotion_spec", None) is not None
            else scene.remotion_composition
        )
        props = (
            scene.remotion_spec.props
            if getattr(scene, "remotion_spec", None) is not None
            else scene.remotion_props
        )
        renderer.render(
            composition_id=composition_id,
            output_path=output_path,
            props=props,
            remotion_spec=getattr(scene, "remotion_spec", None),
        )
        if scene.assets:
            scene.assets[0].path = str(output_path)
        else:
            scene.assets.append(
                TimelineAsset(
                    asset_id=f"{scene.scene_id}-remotion",
                    path=str(output_path),
                    source="remotion",
                    start_s=scene.start_s,
                    end_s=scene.end_s,
                    role="primary_visual",
                )
        )
        scene.remotion_source_file = str(output_path)
        return output_path

    def _ordered_assets(self, assets: list[TimelineAsset]) -> list[TimelineAsset]:
        return sorted(
            assets,
            key=lambda asset: (
                self._asset_start(asset),
                self._asset_end(asset),
                asset.asset_id,
            ),
        )

    def _asset_start(self, asset: TimelineAsset) -> float:
        if asset.scene_start_s is not None:
            return asset.scene_start_s
        return asset.start_s

    def _asset_end(self, asset: TimelineAsset) -> float:
        if asset.scene_end_s is not None:
            return asset.scene_end_s
        return asset.end_s

    def _asset_duration(self, asset: TimelineAsset) -> float:
        return max(self._asset_end(asset) - self._asset_start(asset), 0.1)

    def _scene_duration(self, scene) -> float:
        return max(scene.end_s - scene.start_s, 0.1)
