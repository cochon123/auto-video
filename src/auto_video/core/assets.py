"""Asset planning and retrieval for multi-agent video generation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

from auto_video.agents.contracts import AssetRequest, ScenePlan, ScriptPlan
from auto_video.config.schema import VisualsConfig
from auto_video.core.visual_keywords import MediaSegment
from auto_video.manifest.schema import TimelineAsset
from auto_video.providers.stock import StockManager
from auto_video.utils.workspace import Workspace

logger = logging.getLogger(__name__)


@dataclass
class PlannedAsset:
    """Resolved asset attached to a scene."""

    scene_id: str
    asset: TimelineAsset


@dataclass
class AssetCollectionRecord:
    """Audit record for one visual asset request."""

    scene_id: str
    request_index: int
    query: str
    kind: str
    preferred_source: str | None
    resolved_source: str | None
    status: str
    output_path: str | None
    source_image_path: str | None
    asset_id: str | None
    duration_s: float
    error: str | None = None


class AssetPlanner:
    """Retrieve scene assets and normalize them for the manifest."""

    def __init__(self, config: VisualsConfig) -> None:
        self.config = config

    def collect_scene_assets(
        self,
        script_plan: ScriptPlan,
        scene_plans: list[ScenePlan],
        workspace: Workspace,
    ) -> dict[str, list[TimelineAsset]]:
        workspace.create()
        stock_manager = StockManager(self.config)
        assets: dict[str, list[TimelineAsset]] = {scene.scene_id: [] for scene in script_plan.scenes}
        global_keywords = self._global_keywords(script_plan)
        visual_log_records: list[AssetCollectionRecord] = []
        next_clip_index = 0

        for script_scene in script_plan.scenes:
            scene_plan = self._get_scene_plan(scene_plans, script_scene.scene_id)
            if scene_plan.render_mode == "remotion":
                visual_log_records.append(
                    AssetCollectionRecord(
                        scene_id=script_scene.scene_id,
                        request_index=0,
                        query="",
                        kind="remotion_component",
                        preferred_source=None,
                        resolved_source="remotion",
                        status="skipped",
                        output_path=None,
                        source_image_path=None,
                        asset_id=None,
                        duration_s=0.0,
                        error="remotion_scene",
                    )
                )
                continue

            asset_requests = [
                request for request in scene_plan.asset_requests if request.kind in {"video", "image"}
            ]
            if not asset_requests:
                asset_requests = self._fallback_asset_requests(script_scene, scene_plan)

            slot_duration = max(script_scene.duration_s / max(len(asset_requests), 1), 1.0)
            media_segments: list[MediaSegment] = []
            for asset_request in asset_requests:
                media_segments.append(
                    MediaSegment(
                        text=script_scene.narration,
                        keywords=[asset_request.query] if asset_request.query else list(script_scene.keywords),
                        duration=slot_duration,
                        media_type="image" if asset_request.kind == "image" else "video",
                        source=asset_request.preferred_source,
                    )
                )

            clip_paths = stock_manager.get_media_for_segments(
                media_segments,
                workspace.assets_video_dir,
                global_keywords=global_keywords,
                preserve_source_dir=workspace.assets_image_dir,
                clip_index_start=next_clip_index,
            )

            if len(clip_paths) < len(media_segments):
                logger.warning(
                    "[AssetPlanner] Scene %s resolved %d/%d assets",
                    script_scene.scene_id,
                    len(clip_paths),
                    len(media_segments),
                )

            for request_index, (asset_request, clip_path) in enumerate(zip(asset_requests, clip_paths)):
                resolved_source = asset_request.preferred_source or self._infer_source(clip_path)
                asset = TimelineAsset(
                    asset_id=f"{script_scene.scene_id}-asset-{request_index + 1:02d}",
                    path=str(clip_path),
                    source=resolved_source,
                    start_s=round(request_index * slot_duration, 2),
                    end_s=round((request_index + 1) * slot_duration, 2),
                    scene_start_s=round(request_index * slot_duration, 2),
                    scene_end_s=round((request_index + 1) * slot_duration, 2),
                    role="primary_visual" if request_index == 0 else "supporting_visual",
                )
                assets[script_scene.scene_id].append(asset)
                source_image_path = workspace.assets_image_dir / f"source_{next_clip_index + request_index:03d}.jpg"
                visual_log_records.append(
                    AssetCollectionRecord(
                        scene_id=script_scene.scene_id,
                        request_index=request_index,
                        query=asset_request.query,
                        kind=asset_request.kind,
                        preferred_source=asset_request.preferred_source,
                        resolved_source=resolved_source,
                        status="downloaded",
                        output_path=str(clip_path),
                        source_image_path=str(source_image_path) if source_image_path.exists() else None,
                        asset_id=asset.asset_id,
                        duration_s=slot_duration,
                    )
                )
                logger.info(
                    "[AssetPlanner] scene=%s request=%d query=%r source=%s output=%s",
                    script_scene.scene_id,
                    request_index + 1,
                    asset_request.query,
                    resolved_source,
                    clip_path,
                )

            if len(clip_paths) < len(asset_requests):
                for request_index in range(len(clip_paths), len(asset_requests)):
                    asset_request = asset_requests[request_index]
                    visual_log_records.append(
                        AssetCollectionRecord(
                            scene_id=script_scene.scene_id,
                            request_index=request_index,
                            query=asset_request.query,
                            kind=asset_request.kind,
                            preferred_source=asset_request.preferred_source,
                            resolved_source=asset_request.preferred_source,
                            status="failed",
                            output_path=None,
                            source_image_path=None,
                            asset_id=None,
                            duration_s=slot_duration,
                            error="No media was returned for this request",
                        )
                    )
                    logger.warning(
                        "[AssetPlanner] scene=%s request=%d query=%r failed",
                        script_scene.scene_id,
                        request_index + 1,
                        asset_request.query,
                    )

            next_clip_index += len(clip_paths)

        self._write_visual_asset_log(workspace, visual_log_records)
        return assets

    def _write_visual_asset_log(
        self, workspace: Workspace, records: list[AssetCollectionRecord]
    ) -> None:
        if not records:
            return

        workspace.visual_asset_log_path.write_text(
            "\n".join(json.dumps(asdict(record), ensure_ascii=False) for record in records) + "\n",
            encoding="utf-8",
        )

    def _fallback_asset_requests(self, script_scene, scene_plan: ScenePlan) -> list[AssetRequest]:
        media_kind = "image" if scene_plan.render_mode == "image_motion" else "video"
        keywords = list(script_scene.keywords) or [script_scene.visual_intent or script_scene.narration]
        return [
            AssetRequest(
                kind=media_kind,
                query=str(keyword),
                preferred_source="duckduckgo" if media_kind == "image" else None,
                required=True,
            )
            for keyword in keywords[:3]
        ]

    def _get_scene_plan(self, scene_plans: list[ScenePlan], scene_id: str) -> ScenePlan:
        for scene_plan in scene_plans:
            if scene_plan.scene_id == scene_id:
                return scene_plan
        raise KeyError(f"Missing scene plan for {scene_id}")

    def _global_keywords(self, script_plan: ScriptPlan) -> list[str]:
        seen: list[str] = []
        for scene in script_plan.scenes:
            for keyword in scene.keywords:
                if keyword not in seen:
                    seen.append(keyword)
        return seen[:10]

    def _infer_source(self, asset_path: Path) -> str:
        name = asset_path.name.lower()
        if "duck" in name:
            return "duckduckgo"
        if "pexels" in name:
            return "pexels"
        return "stock"
