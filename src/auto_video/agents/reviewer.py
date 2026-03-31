"""Quality reviewer agent for script validation."""

from __future__ import annotations

from typing import Any

from auto_video.agents.base import BaseAgent
from auto_video.agents.contracts import ReviewResult, ScriptPlan
from auto_video.core.llm import load_prompt

WORDS_PER_SECOND = 2.5
RUNTIME_TOLERANCE_PCT = 15


class ReviewerAgent(BaseAgent):
    @property
    def role(self) -> str:
        return load_prompt("agents/reviewer_role.txt")

    @property
    def goal(self) -> str:
        return load_prompt("agents/reviewer_goal.txt")

    def backstory(self) -> str:
        return load_prompt("agents/reviewer_backstory.txt")

    def create_crewai_agent(self) -> Any:
        try:
            from crewai import Agent

            return Agent(
                role=self.role,
                goal=self.goal,
                backstory=self.backstory(),
                verbose=True,
                llm=self.llm.provider if hasattr(self.llm, "provider") else self.llm,
            )
        except ImportError:
            return None

    def review_script(self, script: ScriptPlan) -> ReviewResult:
        return_dict = isinstance(script, dict)
        if isinstance(script, dict):
            scenes = script.get("scenes", [])
            normalized_scenes = []
            for index, scene in enumerate(scenes, start=1):
                normalized_scenes.append(
                    {
                        "scene_id": scene.get("scene_id", f"scene_{index:02d}"),
                        "order": scene.get("order", scene.get("scene_number", index)),
                        "purpose": scene.get("purpose", scene.get("type", "content")),
                        "narration": scene.get("narration", ""),
                        "duration_s": scene.get("duration_s", scene.get("duration", 30)),
                        "visual_intent": scene.get("visual_intent", scene.get("visual_cues", "")),
                        "sound_intent": scene.get("sound_intent"),
                        "complexity": "standard",
                        "keywords": scene.get("keywords", []),
                    }
                )
            script = ScriptPlan(
                title=script.get("title", "Video"),
                hook=normalized_scenes[0]["narration"][:80] if normalized_scenes else "Hook",
                scenes=normalized_scenes,
                closing_cta=None,
            )
        scenes = script.scenes
        if not scenes:
            result = ReviewResult(
                approved=False,
                score=0.0,
                feedback="Script is empty.",
                revision_requests=["Add structured scenes"],
                criteria_scores={"structure": 0.0},
            )
            return result.model_dump() if return_dict else result

        engagement = 1.0 if "?" in script.hook or len(script.hook.split()) >= 6 else 0.7
        clarity = 1.0 if all(
            len([word for word in scene.narration.split() if word.strip()])
            <= max(int(scene.duration_s * WORDS_PER_SECOND * 1.2), 20)
            for scene in scenes
        ) else 0.7
        structure = 1.0 if len(scenes) >= 3 else 0.4
        declared_duration = sum(scene.duration_s for scene in scenes)
        estimated_duration = sum(self._estimate_spoken_duration(scene.narration) for scene in scenes)
        timing_delta = abs(estimated_duration - declared_duration) / max(declared_duration, 1.0)
        timing = max(0.0, 1.0 - timing_delta)
        visual = 1.0 if all(scene.visual_intent for scene in scenes) else 0.5

        criteria = {
            "engagement": engagement,
            "clarity": clarity,
            "structure": structure,
            "timing": timing,
            "visual_utility": visual,
        }
        score = sum(criteria.values()) / len(criteria)
        revision_requests: list[str] = []
        if engagement < 0.8:
            revision_requests.append("Strengthen the opening hook")
        if clarity < 0.8:
            revision_requests.append("Shorten spoken sentences")
        if timing_delta > (RUNTIME_TOLERANCE_PCT / 100.0):
            if estimated_duration < declared_duration:
                revision_requests.append("Expand narration to better match the requested runtime")
            else:
                revision_requests.append("Shorten narration to better match the requested runtime")

        approved = score >= 0.8 and len(scenes) >= 2 and not revision_requests
        result = ReviewResult(
            approved=approved,
            score=score,
            feedback="Script is approved." if approved else "Script needs one revision pass.",
            revision_requests=revision_requests,
            criteria_scores=criteria,
        )
        return result.model_dump() if return_dict else result

    def review_visuals(self, visual_plan: dict[str, Any]) -> dict[str, Any]:
        scenes = visual_plan.get("scenes", [])
        has_remotion = any(scene.get("render_mode") == "remotion" for scene in scenes)
        has_standard = any(scene.get("render_mode") != "remotion" for scene in scenes)
        balanced = has_standard or not has_remotion
        return {
            "approved": True,
            "score": 0.9 if balanced else 0.75,
            "feedback": "Visual plan is balanced." if balanced else "Visual plan leans too heavily on Remotion.",
            "has_balance": balanced,
        }

    def _estimate_spoken_duration(self, text: str) -> float:
        words = len([word for word in text.split() if word.strip()])
        return max(words / WORDS_PER_SECOND, 0.1)
