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
        target_duration = max(manifest.total_duration_s, audio_duration or 0.0)

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
            target_duration,
        )
        raw_duration = self._safe_duration(workspace.video_raw_path)
        if raw_duration is not None and raw_duration > target_duration:
            self.composer.trim_video_to_duration(
                workspace.video_raw_path,
                workspace.video_raw_path,
                target_duration,
            )
        elif raw_duration is not None and raw_duration < target_duration and hasattr(self.composer, "extend_video_to_duration"):
            self.composer.extend_video_to_duration(
                workspace.video_raw_path,
                workspace.video_raw_path,
                target_duration,
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

        manifest.output_video = str(output_path)
        manifest.total_duration_s = max(target_duration, 0.1)
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
            return None
        try:
            duration = get_duration(media_path)
        except Exception:
            return None
        return float(duration) if isinstance(duration, (int, float)) else None

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
