"""CrewAI-backed orchestration layer for auto-video."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from auto_video.agents.contracts import (
    OrchestrationResult,
    ResearchBundle,
    ReviewResult,
    ScenePlan,
    ScriptPlan,
    VideoBrief,
)
from auto_video.agents.director import DirectorAgent
from auto_video.agents.researcher import ResearchAgent
from auto_video.agents.reviewer import ReviewerAgent
from auto_video.agents.scriptwriter import ScriptwriterAgent
from auto_video.agents.visual_curator import VisualCuratorAgent
from auto_video.core.llm import LLM
from auto_video.manifest.schema import TimelineAsset, TimelineScene, VideoManifest
from auto_video.utils.workspace import Workspace

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinate agent outputs and expose typed orchestration helpers."""

    def __init__(self, llm: LLM, progress_display: Any = None, verbose: bool = False) -> None:
        self.llm = llm
        self.progress_display = progress_display
        self.verbose = verbose
        self.director = DirectorAgent(llm)
        self.researcher = ResearchAgent(llm)
        self.scriptwriter = ScriptwriterAgent(llm)
        self.reviewer = ReviewerAgent(llm)
        self.visual_curator = VisualCuratorAgent(llm)
        self.backend = "crewai" if self._crewai_available() else "local"

    def prepare_brief(self, title: str, duration: int, language: str, video_format: str) -> VideoBrief:
        brief = self.director.prepare_brief(title, duration, language, video_format)
        self._log_agent("director", f"Brief ready: research={brief.requires_research}, risk={brief.factual_risk}")
        return brief

    def run_research_if_needed(self, brief: VideoBrief) -> ResearchBundle | None:
        if not brief.requires_research:
            self._log_agent("researcher", "Research skipped for low-risk topic")
            return None
        research = self.researcher.research(brief)
        self._log_agent("researcher", f"Research bundle ready with {len(research.items)} items")
        return research

    def generate_script(self, brief: VideoBrief, research: ResearchBundle | None = None) -> ScriptPlan:
        script = self.scriptwriter.write_script_plan(brief, research)
        self._log_agent("scriptwriter", f"Script plan ready with {len(script.scenes)} scenes")
        return script

    def review_script(self, script: ScriptPlan) -> tuple[ScriptPlan, ReviewResult]:
        review = self.reviewer.review_script(script)
        self._log_agent("reviewer", f"Review score={review.score:.2f}, approved={review.approved}")
        if review.approved:
            return script, review
        revised = self.scriptwriter.revise_script(script, review.model_dump())
        final_review = self.reviewer.review_script(revised)
        self._log_agent("reviewer", f"Re-review score={final_review.score:.2f}, approved={final_review.approved}")
        return revised, final_review

    def plan_visuals(self, brief: VideoBrief, script: ScriptPlan) -> list[ScenePlan]:
        plans = self.visual_curator.plan_visuals(brief, script)
        remotion_count = sum(1 for plan in plans if plan.render_mode == "remotion")
        self._log_agent("visual_curator", f"Scene plans ready: {len(plans)} scenes, {remotion_count} remotion")
        return plans

    def orchestrate(
        self,
        title: str,
        duration: int,
        language: str,
        video_format: str,
        workspace: Workspace | None = None,
        resolved_assets: dict[str, list[Any]] | None = None,
    ) -> OrchestrationResult:
        brief = self.prepare_brief(title, duration, language, video_format)
        research = self.run_research_if_needed(brief)
        script = self.generate_script(brief, research)
        script, review = self.review_script(script)
        scene_plans = self.plan_visuals(brief, script)

        if workspace is None:
            workspace_stub = type(
                "WorkspaceStub",
                (),
                {
                    "video_id": f"agents-{title[:16].lower().replace(' ', '-') or 'video'}",
                    "workspace_path": Path.cwd() / ".auto-video-agents",
                },
            )()
        else:
            workspace_stub = workspace

        manifest = self.build_manifest(
            video_id=workspace_stub.video_id,
            brief=brief,
            script=script,
            scene_plans=scene_plans,
            workspace=workspace_stub,
            resolved_assets=resolved_assets or {},
        )
        return OrchestrationResult(
            brief=brief,
            research=research,
            script=script,
            review=review,
            scene_plans=scene_plans,
            manifest=manifest,
            manifest_path=None,
            backend=self.backend,
        )

    def build_manifest(
        self,
        video_id: str,
        brief: VideoBrief,
        script: ScriptPlan,
        scene_plans: list[ScenePlan],
        workspace: Workspace,
        resolved_assets: dict[str, list[Any]],
    ) -> VideoManifest:
        timeline_scenes: list[TimelineScene] = []
        current_time = 0.0

        scene_plan_map = {scene.scene_id: scene for scene in scene_plans}
        for script_scene in script.scenes:
            end_time = current_time + script_scene.duration_s
            scene_plan = scene_plan_map[script_scene.scene_id]
            resolved_scene_assets: list[dict[str, Any]] = []
            for asset in resolved_assets.get(script_scene.scene_id, []):
                normalized_asset = (
                    asset if isinstance(asset, TimelineAsset) else TimelineAsset.model_validate(asset)
                )
                scene_relative_start = normalized_asset.start_s
                scene_relative_end = normalized_asset.end_s
                absolute_asset = normalized_asset.model_copy(
                    update={
                        "start_s": round(current_time + scene_relative_start, 2),
                        "end_s": round(
                            min(current_time + scene_relative_end, end_time),
                            2,
                        ),
                        "scene_start_s": round(scene_relative_start, 2),
                        "scene_end_s": round(
                            min(scene_relative_end, script_scene.duration_s),
                            2,
                        ),
                    }
                )
                resolved_scene_assets.append(absolute_asset.model_dump(mode="json"))
            timeline_scenes.append(
                TimelineScene(
                    scene_id=script_scene.scene_id,
                    start_s=round(current_time, 2),
                    end_s=round(end_time, 2),
                    narration=script_scene.narration,
                    subtitles=scene_plan.subtitle_text or script_scene.narration,
                    render_mode=scene_plan.render_mode,
                    assets=resolved_scene_assets,
                    effects=list(scene_plan.ffmpeg_effects),
                    remotion_source_file=None,
                    remotion_composition=scene_plan.remotion_composition,
                    remotion_props=scene_plan.remotion_props,
                    remotion_spec=scene_plan.remotion_spec,
                    editable_notes=scene_plan.notes,
                )
            )
            current_time = end_time

        manifest = VideoManifest(
            video_id=video_id,
            title=brief.title,
            language=brief.language,
            total_duration_s=max(current_time, 0.1),
            scenes=timeline_scenes,
            workspace_dir=str(workspace.workspace_path),
            output_video=None,
            metadata={"orchestration_backend": self.backend},
        )
        self._log_agent("assembly", f"Manifest built with {len(manifest.scenes)} scenes")
        return manifest

    def _crewai_available(self) -> bool:
        try:
            import crewai  # noqa: F401
        except ImportError:
            return False
        return True

    def _log_agent(self, agent_name: str, message: str) -> None:
        logger.info("[Agent:%s][backend=%s] %s", agent_name, self.backend, message)
        if self.progress_display is not None and hasattr(self.progress_display, "update_step_details"):
            self.progress_display.update_step_details(
                max(getattr(self.progress_display, "_current_step_index", 0), 0),
                f"[{agent_name}] {message}",
            )
