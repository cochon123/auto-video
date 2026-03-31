"""Director agent for high-level video planning."""

from __future__ import annotations

import math
import re
from typing import Any

from auto_video.agents.base import BaseAgent
from auto_video.agents.contracts import VideoBrief
from auto_video.core.llm import load_prompt


class DirectorAgent(BaseAgent):
    @property
    def role(self) -> str:
        return load_prompt("agents/director_role.txt")

    @property
    def goal(self) -> str:
        return load_prompt("agents/director_goal.txt")

    def backstory(self) -> str:
        return load_prompt("agents/director_backstory.txt")

    def create_crewai_agent(self) -> Any:
        try:
            from crewai import Agent

            return Agent(
                role=self.role,
                goal=self.goal,
                backstory=self.backstory(),
                verbose=True,
                allow_delegation=True,
                llm=self.llm.provider if hasattr(self.llm, "provider") else self.llm,
            )
        except ImportError:
            return None

    def prepare_brief(
        self,
        topic: str,
        duration: int,
        language: str,
        video_format: str,
    ) -> VideoBrief:
        factual_risk = self._assess_factual_risk(topic)
        requires_research = factual_risk in {"medium", "high"} or self._contains_rare_entity(topic)
        if video_format == "short":
            creative_direction = (
                "Plan for a vertical, mobile-first video with a strong hook, faster pacing, "
                "clean visual beats, and concise narration."
            )
        else:
            creative_direction = (
                "Plan for a landscape editorial video with a documentary pace, stronger scene "
                "build-up, and broader visual variety."
            )
        return VideoBrief(
            title=topic.strip(),
            language=language,
            format="long" if video_format == "long" else "short",
            target_duration_s=max(duration, 30),
            audience="general",
            tone="informative",
            requires_research=requires_research,
            creative_direction=creative_direction,
            factual_risk=factual_risk,
        )

    def plan_video_structure(self, topic: str, duration: float, format: str) -> dict[str, Any]:
        num_scenes = max(3, math.ceil(duration / 45))
        segments = []
        for i in range(num_scenes):
            if i == 0:
                seg_type = "intro"
            elif i == num_scenes - 1:
                seg_type = "outro"
            else:
                seg_type = "content"
            segments.append(
                {
                    "index": i,
                    "estimated_duration": duration / num_scenes,
                    "type": seg_type,
                }
            )
        return {
            "segments": segments,
            "tone": "informative",
            "target_audience": "general",
            "style": "documentary",
            "required_complex_segments": ["intro", "outro"] if format == "long" else ["intro"],
        }

    def analyze_complexity_requirements(self, script_scene: dict[str, Any], context: dict[str, Any]) -> bool:
        visual_cues = script_scene.get("visual_cues", "").lower()
        scene_type = script_scene.get("type", "")
        return any(
            [
                scene_type in ["intro", "outro"],
                script_scene.get("requires_complex_motion", False),
                "data viz" in visual_cues,
                "graph" in visual_cues,
                "chart" in visual_cues,
                "animated text" in visual_cues,
                "kinetic typography" in visual_cues,
            ]
        )

    def _assess_factual_risk(self, topic: str) -> str:
        lowered = topic.lower()
        high_markers = ["today", "actualité", "news", "latest", "breaking", "202", "president", "war"]
        medium_markers = [
            "biodiversité",
            "history",
            "science",
            "climate",
            "himalaya",
            "biologie",
            "earthquake",
        ]
        if any(marker in lowered for marker in high_markers):
            return "high"
        if any(marker in lowered for marker in medium_markers):
            return "medium"
        return "low"

    def _contains_rare_entity(self, topic: str) -> bool:
        tokens = re.findall(r"[A-Z][a-zA-ZÀ-ÿ-]+", topic)
        return len(tokens) >= 2 or any(len(token) > 10 for token in topic.split())
