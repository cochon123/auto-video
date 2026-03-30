"""Tests for asset collection and assembly behavior."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

from auto_video.agents.contracts import AssetRequest, ScenePlan, ScriptPlan
from auto_video.config.schema import VisualsConfig
from auto_video.core.assembly import AssemblyEngine
from auto_video.core.assets import AssetPlanner
from auto_video.manifest.schema import TimelineAsset, TimelineScene, VideoManifest
from auto_video.utils.workspace import Workspace


class DummyStockManager:
    def __init__(self, config: VisualsConfig) -> None:
        self.config = config

    def get_media_for_segments(
        self,
        segments,
        output_dir: Path,
        global_keywords=None,
        preserve_source_dir: Path | None = None,
        clip_index_start: int = 0,
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        if preserve_source_dir is not None:
            preserve_source_dir.mkdir(parents=True, exist_ok=True)

        clip_paths: list[Path] = []
        for index, segment in enumerate(segments):
            clip_path = output_dir / f"clip_{clip_index_start + index:03d}.mp4"
            clip_path.write_bytes(f"{segment.keywords[0]}".encode("utf-8"))
            if segment.media_type == "image" and preserve_source_dir is not None:
                source_path = preserve_source_dir / f"source_{clip_index_start + index:03d}.jpg"
                source_path.write_bytes(b"image-bytes")
            clip_paths.append(clip_path)
        return clip_paths


class DummyComposer:
    def __init__(self) -> None:
        self.concat_calls: list[list[Path]] = []

    def concatenate_with_transitions(self, clip_paths, output_path, total_duration, **kwargs):
        self.concat_calls.append(list(clip_paths))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"raw-video")

    def trim_video_to_duration(self, input_path, output_path, duration):
        return output_path

    def add_audio(self, input_path, audio_path, output_path):
        shutil.copy2(input_path, output_path)
        return output_path

    def apply_format_with_temp(self, input_path, output_path, video_format):
        return output_path


def test_collect_scene_assets_resolves_all_requests_and_preserves_sources(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, video_id="video_001")
    config = VisualsConfig(mode="stock", providers=["duckduckgo"])

    script_plan = ScriptPlan(
        title="Test",
        hook="Hook",
        scenes=[
            {
                "scene_id": "scene-1",
                "order": 1,
                "purpose": "intro",
                "narration": "First narration.",
                "duration_s": 9.0,
                "visual_intent": "Three visual beats.",
                "keywords": ["alpha", "beta", "gamma"],
            }
        ],
    )
    scene_plans = [
        ScenePlan(
            scene_id="scene-1",
            render_mode="image_motion",
            asset_requests=[
                AssetRequest(kind="image", query="alpha", preferred_source="duckduckgo"),
                AssetRequest(kind="image", query="beta", preferred_source="duckduckgo"),
                AssetRequest(kind="image", query="gamma", preferred_source="duckduckgo"),
            ],
            subtitle_text="First narration.",
            notes="",
        )
    ]

    with patch("auto_video.core.assets.StockManager", DummyStockManager):
        planner = AssetPlanner(config)
        assets = planner.collect_scene_assets(script_plan, scene_plans, workspace)

    scene_assets = assets["scene-1"]
    assert len(scene_assets) == 3
    assert [Path(asset.path).name for asset in scene_assets] == [
        "clip_000.mp4",
        "clip_001.mp4",
        "clip_002.mp4",
    ]
    assert [asset.start_s for asset in scene_assets] == [0.0, 3.0, 6.0]
    assert [asset.end_s for asset in scene_assets] == [3.0, 6.0, 9.0]

    assert workspace.visual_asset_log_path.exists()
    records = [
        json.loads(line)
        for line in workspace.visual_asset_log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 3
    assert records[0]["status"] == "downloaded"
    assert records[0]["output_path"].endswith("clip_000.mp4")
    assert records[0]["source_image_path"].endswith("source_000.jpg")
    assert workspace.assets_image_dir.joinpath("source_000.jpg").exists()
    assert workspace.assets_image_dir.joinpath("source_001.jpg").exists()
    assert workspace.assets_image_dir.joinpath("source_002.jpg").exists()


def test_assembly_engine_flattens_multiple_assets_per_scene(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, video_id="video_002")
    workspace.create()

    clip1 = workspace.assets_video_dir / "clip_000.mp4"
    clip2 = workspace.assets_video_dir / "clip_001.mp4"
    clip1.write_bytes(b"one")
    clip2.write_bytes(b"two")
    audio_path = workspace.audio_path
    audio_path.write_bytes(b"audio")

    manifest = VideoManifest(
        video_id="video_002",
        title="Test",
        language="en",
        total_duration_s=6.0,
        scenes=[
            TimelineScene(
                scene_id="scene-1",
                start_s=0.0,
                end_s=6.0,
                narration="Narration",
                subtitles="Narration",
                render_mode="stock_video",
                assets=[
                    TimelineAsset(
                        asset_id="scene-1-asset-01",
                        path=str(clip1),
                        source="duckduckgo",
                        start_s=0.0,
                        end_s=3.0,
                        role="primary_visual",
                    ),
                    TimelineAsset(
                        asset_id="scene-1-asset-02",
                        path=str(clip2),
                        source="duckduckgo",
                        start_s=3.0,
                        end_s=6.0,
                        role="supporting_visual",
                    ),
                ],
                effects=[],
                editable_notes="",
            )
        ],
        workspace_dir=str(workspace.workspace_path),
    )

    composer = DummyComposer()
    engine = AssemblyEngine(composer=composer)
    output_path = workspace.final_path
    result = engine.render_from_manifest(
        manifest=manifest,
        workspace=workspace,
        audio_path=audio_path,
        output_path=output_path,
        video_format="long",
    )

    assert result == output_path
    assert output_path.exists()
    assert len(composer.concat_calls) == 2
    assert [path.name for path in composer.concat_calls[0]] == [
        "00_scene-1-asset-01.mp4",
        "01_scene-1-asset-02.mp4",
    ]
