"""
Scriptwriter Agent for auto-video multi-agent system.

The Scriptwriter agent turns a brief and optional research bundle into a
structured script plan.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from auto_video.agents.base import BaseAgent
from auto_video.agents.contracts import ResearchBundle, ScriptPlan, ScriptScene, VideoBrief
from auto_video.core.llm import load_prompt

logger = logging.getLogger(__name__)

MIN_SCENES = 3
MAX_SCENES = 20
SCENE_TARGET_SECONDS = 30.0
RUNTIME_TOLERANCE_PCT = 15


class ScriptwriterAgent(BaseAgent):
    @property
    def role(self) -> str:
        return load_prompt("agents/scriptwriter_role.txt")

    @property
    def goal(self) -> str:
        return load_prompt("agents/scriptwriter_goal.txt")

    def backstory(self) -> str:
        return load_prompt("agents/scriptwriter_backstory.txt")

    def create_crewai_agent(self) -> Any:
        try:
            from crewai import Agent

            return Agent(
                role=self.role,
                goal=self.goal,
                backstory=self.backstory(),
                verbose=True,
                llm=self.llm,
            )
        except ImportError:
            return None

    def write_script(
        self,
        topic: str,
        structure: dict[str, Any],
        tone: str = "informative",
        language: str = "fr",
        research_bundle: ResearchBundle | None = None,
    ) -> dict[str, Any]:
        prompt = self._build_script_prompt(topic, structure, tone, language, research_bundle)
        try:
            response = self._generate(prompt)
            return self._parse_script_response(response, topic, structure, research_bundle)
        except Exception as exc:
            logger.warning("Script generation failed for %r: %s", topic, exc)
            return self._generate_fallback_script(topic, structure, tone)

    def build_script_plan(
        self,
        topic: str,
        structure: dict[str, Any],
        tone: str = "informative",
        language: str = "fr",
        research_bundle: ResearchBundle | None = None,
    ) -> ScriptPlan:
        raw_script = self.write_script(
            topic=topic,
            structure=structure,
            tone=tone,
            language=language,
            research_bundle=research_bundle,
        )
        return self._coerce_script_plan(raw_script, topic, structure, research_bundle)

    def write_script_plan(self, brief: VideoBrief, research_bundle: ResearchBundle | None = None) -> ScriptPlan:
        scene_count = self._estimate_scene_count(brief.target_duration_s)
        estimated_scene_duration = max(brief.target_duration_s / scene_count, 10.0)
        segments: list[dict[str, Any]] = []
        for index in range(scene_count):
            if index == 0:
                segment_type = "intro"
            elif index == scene_count - 1:
                segment_type = "outro"
            else:
                segment_type = "content"
            segments.append(
                {
                    "type": segment_type,
                    "estimated_duration": estimated_scene_duration,
                }
            )
        structure = {
            "target_duration_s": brief.target_duration_s,
            "runtime_tolerance_pct": RUNTIME_TOLERANCE_PCT,
            "segments": segments,
        }
        return self.build_script_plan(
            topic=brief.title,
            structure=structure,
            tone=brief.tone,
            language=brief.language,
            research_bundle=research_bundle,
        )

    def revise_script(
        self,
        script: dict[str, Any],
        feedback: dict[str, Any],
    ) -> dict[str, Any]:
        revision_requests = feedback.get("revision_requests", [])
        if not script.get("scenes"):
            return script
        for request in revision_requests:
            lowered = request.lower()
            if "hook" in lowered:
                script["scenes"][0]["narration"] = "Did you know that " + str(
                    script["scenes"][0].get("narration", "")
                )
            elif any(keyword in lowered for keyword in ["runtime", "duration", "expand", "shorten"]):
                if "shorten" in lowered:
                    for scene in script["scenes"]:
                        scene["narration"] = self._shorten_narration(str(scene.get("narration", "")))
                else:
                    script["scenes"][-1]["narration"] = self._expand_narration(
                        str(script["scenes"][-1].get("narration", ""))
                    )
        return script

    def _build_script_prompt(
        self,
        topic: str,
        structure: dict[str, Any],
        tone: str,
        language: str,
        research_bundle: ResearchBundle | None,
    ) -> str:
        segments = structure.get("segments", [])
        num_scenes = len(segments)
        avg_duration = segments[0].get("estimated_duration", SCENE_TARGET_SECONDS) if segments else SCENE_TARGET_SECONDS
        research_block = ""
        if research_bundle is not None:
            research_block = json.dumps(research_bundle.model_dump(), ensure_ascii=False, indent=2)
        research_section = f"Research context:\n{research_block}\n" if research_block else ""
        return load_prompt(
            "agents/scriptwriter_prompt.txt",
            topic=topic,
            num_scenes=str(num_scenes),
            avg_duration=f"{avg_duration:.0f}",
            target_duration_s=str(structure.get("target_duration_s", int(avg_duration * max(num_scenes, 1)))),
            runtime_tolerance_pct=str(structure.get("runtime_tolerance_pct", RUNTIME_TOLERANCE_PCT)),
            tone=tone,
            language=language,
            research_section=research_section,
        )

    def _parse_script_response(
        self,
        response: str,
        fallback_title: str,
        structure: dict[str, Any],
        research_bundle: ResearchBundle | None,
    ) -> dict[str, Any]:
        try:
            match = re.search(r"\{[\s\S]*\}", response)
            payload = json.loads(match.group() if match else response)
        except Exception:
            return self._generate_fallback_script(fallback_title, structure, "informative")

        if not isinstance(payload, dict) or "scenes" not in payload:
            return self._generate_fallback_script(fallback_title, structure, "informative")
        payload.setdefault("title", fallback_title)
        if research_bundle is not None and "hook" not in payload:
            payload["hook"] = research_bundle.summary.split(".")[0].strip()
        return payload

    def _generate_fallback_script(
        self,
        topic: str,
        structure: dict[str, Any],
        tone: str,
    ) -> dict[str, Any]:
        segments = structure.get("segments", []) or [{"type": "content", "estimated_duration": 60}]
        return {
            "title": topic,
            "hook": f"Discover {topic}.",
            "scenes": [
                {
                    "scene_id": f"scene-{index + 1}",
                    "scene_number": index + 1,
                    "type": segment.get("type", "content"),
                    "purpose": segment.get("type", "content"),
                    "narration": f"This is scene {index + 1} about {topic}.",
                    "visual_cues": f"Show visuals related to {topic}",
                    "duration": segment.get("estimated_duration", 60),
                    "keywords": [topic.lower(), f"scene {index + 1}"],
                    "requires_complex_motion": segment.get("type") in ["intro", "outro"],
                }
                for index, segment in enumerate(segments)
            ],
        }

    def _coerce_script_plan(
        self,
        script: dict[str, Any],
        topic: str,
        structure: dict[str, Any],
        research_bundle: ResearchBundle | None,
    ) -> ScriptPlan:
        scenes: list[ScriptScene] = []
        raw_scenes = script.get("scenes", []) if isinstance(script, dict) else []
        for index, scene in enumerate(raw_scenes):
            if not isinstance(scene, dict):
                continue
            scenes.append(
                ScriptScene(
                    scene_id=str(scene.get("scene_id") or f"scene-{index + 1}"),
                    order=int(scene.get("order") or scene.get("scene_number") or index + 1),
                    purpose=str(scene.get("purpose") or scene.get("type") or "content"),
                    narration=str(scene.get("narration", "")).strip() or f"Scene {index + 1} about {topic}.",
                    duration_s=float(scene.get("duration_s") or scene.get("duration") or 60.0),
                    visual_intent=str(scene.get("visual_intent") or scene.get("visual_cues") or topic),
                    sound_intent=(str(scene.get("sound_intent") or "").strip() or None),
                    complexity=self._infer_complexity(scene),
                    keywords=self._normalize_keywords(scene.get("keywords"), topic),
                )
            )

        if not scenes:
            scenes = [
                ScriptScene(
                    scene_id="scene-1",
                    order=1,
                    purpose="intro",
                    narration=f"Welcome to {topic}.",
                    duration_s=max(float(structure.get("segments", [{}])[0].get("estimated_duration", 60)), 10.0),
                    visual_intent=f"Introduce {topic}",
                    sound_intent="gentle intro music",
                    complexity="motion",
                    keywords=self._normalize_keywords(None, topic),
                )
            ]

        hook = script.get("hook") if isinstance(script, dict) else None
        if not isinstance(hook, str) or not hook.strip():
            hook = research_bundle.summary if research_bundle else scenes[0].narration.split(".")[0]

        return ScriptPlan(
            title=str(script.get("title", topic)),
            hook=hook.strip(),
            scenes=scenes,
            closing_cta=script.get("closing_cta") if isinstance(script, dict) else None,
        )

    def _infer_complexity(self, scene: dict[str, Any]) -> str:
        text = " ".join(str(scene.get(key, "")) for key in ("type", "visual_cues", "visual_intent", "narration")).lower()
        if scene.get("requires_complex_motion") or any(keyword in text for keyword in ["data viz", "chart", "graph", "timeline"]):
            return "data_viz"
        if any(keyword in text for keyword in ["intro", "outro", "motion", "animated", "kinetic", "lower third"]):
            return "motion"
        return "standard"

    def _normalize_keywords(self, keywords: Any, fallback_text: str) -> list[str]:
        if isinstance(keywords, list):
            normalized = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
            if normalized:
                return normalized
        tokens = [token.lower() for token in re.findall(r"[A-Za-zÀ-ÿ0-9']+", fallback_text) if len(token) > 3]
        deduped: list[str] = []
        for token in tokens:
            if token not in deduped:
                deduped.append(token)
        return deduped or ["video"]

    def _estimate_scene_count(self, target_duration_s: int) -> int:
        if target_duration_s <= 0:
            return MIN_SCENES
        estimate = int(round(target_duration_s / SCENE_TARGET_SECONDS))
        return max(MIN_SCENES, min(MAX_SCENES, estimate))

    def _expand_narration(self, narration: str) -> str:
        narration = narration.strip()
        if not narration:
            return narration
        addition = " This lets us unpack the idea in a little more detail."
        if narration.endswith("."):
            return narration + addition
        return narration + "." + addition

    def _shorten_narration(self, narration: str) -> str:
        narration = narration.strip()
        if not narration:
            return narration
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", narration)
            if sentence.strip()
        ]
        return " ".join(sentences[:2]) if sentences else narration
