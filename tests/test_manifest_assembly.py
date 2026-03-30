"""Tests for multi-asset manifests and assembly."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from auto_video.agents.contracts import AssetRequest, ScenePlan, ScriptPlan
from auto_video.config.schema import VisualsConfig
from auto_video.core.assets import AssetPlanner
from auto_video.core.assembly import AssemblyEngine
from auto_video.manifest.schema import TimelineAsset, TimelineScene, VideoManifest
from auto_video.utils.workspace import Workspace


def _write_dummy_clip(path: Path, content: bytes = b"clip") -> Path:
    path.write_bytes(content)
    return path


def test_timeline_scene_sorts_scene_relative_assets() -> None:
    scene = TimelineScene(
        scene_id="scene-1",
        start_s=0,
        end_s=20,
        narration="Narration",
        subtitles="Narration",
        render_mode="stock_video",
        assets=[
            TimelineAsset(
                asset_id="asset-2",
                path="/tmp/asset-2.mp4",
                source="stock",
                start_s=10,
                end_s=20,
                scene_start_s=10,
                scene_end_s=20,
                role="secondary_visual",
            ),
            TimelineAsset(
                asset_id="asset-1",
                path="/tmp/asset-1.mp4",
                source="stock",
                start_s=0,
                end_s=10,
                scene_start_s=0,
                scene_end_s=10,
                role="primary_visual",
            ),
        ],
        effects=[],
        editable_notes="",
    )

    assert [asset.asset_id for asset in scene.assets] == ["asset-1", "asset-2"]


def test_asset_planner_collects_multiple_assets_per_scene(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, "multi-asset")
    workspace.create()

    config = VisualsConfig(mode="stock", providers=["pexels"])
    planner = AssetPlanner(config)

    script_plan = ScriptPlan(
        title="Multi asset test",
        hook="Hook",
        scenes=[
            {
                "scene_id": "scene-1",
                "order": 1,
                "purpose": "body",
                "narration": "First part.",
                "duration_s": 30.0,
                "visual_intent": "Split visuals",
                "sound_intent": "Bed",
                "complexity": "standard",
                "keywords": ["space", "stars"],
            }
        ],
        closing_cta=None,
    )
    scene_plan = ScenePlan(
        scene_id="scene-1",
        render_mode="stock_video",
        asset_requests=[
            AssetRequest(kind="video", query="space", preferred_source="pexels"),
            AssetRequest(kind="video", query="stars", preferred_source="pexels"),
        ],
        ffmpeg_effects=["fade"],
        subtitle_text="First part.",
        notes="",
    )

    clip_1 = _write_dummy_clip(workspace.workspace_path / "clip_1.mp4", b"clip-1")
    clip_2 = _write_dummy_clip(workspace.workspace_path / "clip_2.mp4", b"clip-2")

    with patch("auto_video.core.assets.StockManager") as mock_stock_manager:
        mock_instance = MagicMock()
        mock_instance.get_media_for_segments.return_value = [clip_1, clip_2]
        mock_stock_manager.return_value = mock_instance

        assets = planner.collect_scene_assets(script_plan, [scene_plan], workspace)

    assert mock_instance.get_media_for_segments.call_count == 1
    assert len(mock_instance.get_media_for_segments.call_args.args[0]) == 2
    assert len(assets["scene-1"]) == 2
    assert assets["scene-1"][0].scene_start_s == pytest.approx(0.0)
    assert assets["scene-1"][1].scene_start_s == pytest.approx(15.0)
    assert workspace.visual_asset_log_path.exists()
    assert len(workspace.visual_asset_log_path.read_text(encoding="utf-8").splitlines()) == 2


def test_assembly_engine_consumes_multiple_assets_per_scene(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, "assembly-test")
    workspace.create()

    asset_1 = _write_dummy_clip(workspace.assets_video_dir / "asset_1.mp4", b"asset-1")
    asset_2 = _write_dummy_clip(workspace.assets_video_dir / "asset_2.mp4", b"asset-2")
    audio_path = _write_dummy_clip(workspace.audio_path, b"audio")

    manifest = VideoManifest(
        video_id="assembly-test",
        title="Assembly Test",
        language="en",
        total_duration_s=20.0,
        scenes=[
            TimelineScene(
                scene_id="scene-1",
                start_s=0,
                end_s=20,
                narration="Narration",
                subtitles="Narration",
                render_mode="stock_video",
                assets=[
                    TimelineAsset(
                        asset_id="asset-1",
                        path=str(asset_1),
                        source="stock",
                        start_s=0,
                        end_s=10,
                        scene_start_s=0,
                        scene_end_s=10,
                        role="primary_visual",
                    ),
                    TimelineAsset(
                        asset_id="asset-2",
                        path=str(asset_2),
                        source="stock",
                        start_s=10,
                        end_s=20,
                        scene_start_s=10,
                        scene_end_s=20,
                        role="supporting_visual",
                    ),
                ],
                effects=["fade"],
                editable_notes="",
            )
        ],
        workspace_dir=str(workspace.workspace_path),
    )

    composer = MagicMock()

    def _copy_input_to_output(input_path: Path, output_path: Path, *_args, **_kwargs) -> None:
        if input_path == output_path:
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_path, output_path)

    def _concat(clips: list[Path], output: Path, *_args, **_kwargs) -> None:
        if len(clips) == 1 and clips[0] == output:
            return
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(clips[0], output)

    composer.trim_video_to_duration.side_effect = _copy_input_to_output
    composer.concatenate_with_transitions.side_effect = _concat
    composer.add_audio.side_effect = lambda video_path, _audio_path, output_path: (
        None if video_path == output_path else shutil.copy2(video_path, output_path)
    )
    composer.apply_format_with_temp.side_effect = (
        lambda video_path, output_path, _format: None
        if video_path == output_path
        else shutil.copy2(video_path, output_path)
    )

    engine = AssemblyEngine(composer=composer)
    output_path = engine.render_from_manifest(
        manifest=manifest,
        workspace=workspace,
        audio_path=audio_path,
        output_path=workspace.final_path,
        video_format="long",
    )

    assert output_path.exists()
    assert manifest.output_video == str(workspace.final_path)
    assert workspace.manifest_path.exists()
    assert len(composer.concatenate_with_transitions.call_args_list) == 2
    first_concat_args = composer.concatenate_with_transitions.call_args_list[0].args[0]
    assert len(first_concat_args) == 2
    assert first_concat_args[0].name.startswith("00_")
    assert first_concat_args[1].name.startswith("01_")


def test_assembly_engine_extends_video_when_audio_is_longer(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, "assembly-audio-longer")
    workspace.create()

    asset_1 = _write_dummy_clip(workspace.assets_video_dir / "asset_1.mp4", b"asset-1")
    audio_path = _write_dummy_clip(workspace.audio_path, b"audio")

    manifest = VideoManifest(
        video_id="assembly-audio-longer",
        title="Assembly Audio Longer",
        language="en",
        total_duration_s=8.0,
        scenes=[
            TimelineScene(
                scene_id="scene-1",
                start_s=0,
                end_s=8,
                narration="Narration",
                subtitles="Narration",
                render_mode="stock_video",
                assets=[
                    TimelineAsset(
                        asset_id="asset-1",
                        path=str(asset_1),
                        source="stock",
                        start_s=0,
                        end_s=8,
                        scene_start_s=0,
                        scene_end_s=8,
                        role="primary_visual",
                    )
                ],
                effects=[],
                editable_notes="",
            )
        ],
        workspace_dir=str(workspace.workspace_path),
    )

    composer = MagicMock()
    composer.get_duration.side_effect = lambda path: 12.0 if path == audio_path else 8.0
    composer.concatenate_with_transitions.side_effect = lambda clips, output, *_args, **_kwargs: output.write_bytes(b"raw")
    composer.add_audio.side_effect = lambda video_path, _audio_path, output_path: output_path.write_bytes(b"final")
    composer.apply_format_with_temp.side_effect = lambda *_args, **_kwargs: None

    engine = AssemblyEngine(composer=composer)
    engine.render_from_manifest(
        manifest=manifest,
        workspace=workspace,
        audio_path=audio_path,
        output_path=workspace.final_path,
        video_format="long",
    )

    composer.extend_video_to_duration.assert_called_once()


def test_assembly_engine_falls_back_to_cpu_formatting(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, "assembly-fallback")
    workspace.create()

    asset = _write_dummy_clip(workspace.assets_video_dir / "asset.mp4", b"asset")
    audio_path = _write_dummy_clip(workspace.audio_path, b"audio")

    manifest = VideoManifest(
        video_id="assembly-fallback",
        title="Assembly Fallback",
        language="en",
        total_duration_s=10.0,
        scenes=[
            TimelineScene(
                scene_id="scene-1",
                start_s=0,
                end_s=10,
                narration="Narration",
                subtitles="Narration",
                render_mode="stock_video",
                assets=[
                    TimelineAsset(
                        asset_id="asset-1",
                        path=str(asset),
                        source="stock",
                        start_s=0,
                        end_s=10,
                        scene_start_s=0,
                        scene_end_s=10,
                        role="primary_visual",
                    )
                ],
                effects=["fade"],
                editable_notes="",
            )
        ],
        workspace_dir=str(workspace.workspace_path),
    )

    composer = MagicMock()
    composer.trim_video_to_duration.side_effect = lambda input_path, output_path, *_args, **_kwargs: (
        None if input_path == output_path else shutil.copy2(input_path, output_path)
    )
    composer.concatenate_with_transitions.side_effect = lambda clips, output, *_args, **_kwargs: shutil.copy2(
        clips[0], output
    )
    composer.add_audio.side_effect = lambda video_path, _audio_path, output_path: shutil.copy2(
        video_path, output_path
    )
    composer.apply_format_with_temp.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["ffmpeg"]
    )

    fallback_composer = MagicMock()
    fallback_composer.apply_format_with_temp.side_effect = lambda video_path, output_path, _format: (
        None if video_path == output_path else shutil.copy2(video_path, output_path)
    )

    with patch("auto_video.core.assembly.VideoComposer", return_value=fallback_composer) as mock_video_composer:
        engine = AssemblyEngine(composer=composer)
        output_path = engine.render_from_manifest(
            manifest=manifest,
            workspace=workspace,
            audio_path=audio_path,
            output_path=workspace.final_path,
            video_format="long",
        )

    assert output_path.exists()
    mock_video_composer.assert_called_once()
    assert mock_video_composer.call_args.kwargs["gpu_acceleration"] == "cpu"
    assert fallback_composer.apply_format_with_temp.called
