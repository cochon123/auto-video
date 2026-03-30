"""
Visual Curator Agent for auto-video multi-agent system.

The Visual Curator decides how each scene should be rendered.
"""

from __future__ import annotations

import ast
import logging
import random
import re
from typing import Any

from auto_video.agents.base import BaseAgent
from auto_video.agents.contracts import (
    AssetRequest,
    CompositionRenderSettings,
    RemotionSpec,
    ResearchBundle,
    ScenePlan,
    ScriptScene,
    VideoBrief,
)
from auto_video.remotion import get_registry, get_renderer

logger = logging.getLogger(__name__)


class VisualCuratorAgent(BaseAgent):
    @property
    def role(self) -> str:
        return "Visual Content Curator"

    @property
    def goal(self) -> str:
        return (
            "Choose the most suitable visual treatment for each scene, balancing "
            "stock footage, image motion, and Remotion."
        )

    def backstory(self) -> str:
        return (
            "You are a visual producer who can tell when stock media is enough "
            "and when motion graphics are worth the extra effort."
        )

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

    def build_scene_plan(
        self,
        scene: ScriptScene | dict[str, Any],
        previous_context: dict[str, Any],
        research: ResearchBundle | None = None,
    ) -> ScenePlan:
        raw_scene = scene.model_dump() if isinstance(scene, ScriptScene) else scene
        visual_plan = self.plan_scene_visuals(raw_scene, previous_context)
        return self._coerce_scene_plan(raw_scene, visual_plan, research)

    def plan_visuals(self, brief: VideoBrief, script: Any) -> list[ScenePlan]:
        plans: list[ScenePlan] = []
        previous_context = {
            "video_title": brief.title,
            "subtitle": "",
            "accent_color": "#4ecdc4",
            "remotion_available": self._remotion_available(),
        }
        for scene in getattr(script, "scenes", []):
            plans.append(self.build_scene_plan(scene, previous_context))
            previous_context["last_scene_id"] = getattr(scene, "scene_id", "")
        return plans

    def plan_scene_visuals(
        self,
        scene: dict[str, Any],
        previous_context: dict[str, Any],
    ) -> dict[str, Any]:
        if self._requires_complex_motion(scene, previous_context):
            return self._plan_remotion_scene(scene, previous_context)
        return self._plan_ffmpeg_scene(scene, previous_context)

    def _requires_complex_motion(self, scene: dict[str, Any], context: dict[str, Any]) -> bool:
        if not context.get("remotion_available", True):
            return False
        text = " ".join(
            str(scene.get(key, ""))
            for key in ("type", "visual_cues", "visual_intent", "narration")
        ).lower()
        return scene.get("requires_complex_motion", False) or any(
            marker in text for marker in ["intro", "outro", "data viz", "graph", "chart", "animated", "kinetic", "lower third"]
        ) or self._should_use_remotion_structured_layout(scene)

    def _plan_remotion_scene(self, scene: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if not context.get("remotion_available", True):
            logger.info("Remotion unavailable, falling back to FFmpeg for scene %s", scene.get("scene_id"))
            return {
                "rendering_method": "ffmpeg",
                "assets_needed": scene.get("keywords", []) or [scene.get("visual_cues", "video")],
                "ffmpeg_instructions": {
                    "ken_burns_type": self._select_ken_burns_type(scene),
                    "duration": self._scene_duration_s(scene),
                    "transition_next": self._select_transition_type(),
                },
            }

        visual_cues = str(scene.get("visual_cues", "")).lower()
        if scene.get("type") == "intro":
            composition = "Intro"
            remotion_spec = {
                "title": context.get("video_title", scene.get("narration", "")[:50]),
                "subtitle": context.get("subtitle", ""),
                "logoPath": context.get("logo_path"),
                "accentColor": context.get("accent_color", "#4ecdc4"),
            }
        elif any(marker in visual_cues for marker in ["data viz", "graph", "chart"]):
            composition = "DataViz"
            remotion_spec = {
                "data": scene.get("chart_data", []),
                "chartType": scene.get("chart_type", "bar"),
                "title": scene.get("chart_title", "Data Visualization"),
            }
        elif self._should_use_remotion_comparison(scene):
            composition = "ComparisonCard"
            remotion_spec = self._build_comparison_props(scene, context)
        elif self._should_use_remotion_list_reveal(scene):
            composition = "ListReveal"
            remotion_spec = self._build_list_reveal_props(scene, context)
        elif "lower third" in visual_cues:
            composition = "LowerThird"
            remotion_spec = {
                "name": scene.get("name", "Guest Name"),
                "title": scene.get("guest_title", "Expert"),
                "accentColor": context.get("accent_color", "#4ecdc4"),
                "position": scene.get("position", "left"),
            }
        else:
            composition = "CustomTransition"
            remotion_spec = {
                "type": random.choice(["wipe", "circle", "zoom"]),
                "direction": "left",
                "color": context.get("accent_color", "#000000"),
            }

        return {
            "rendering_method": "remotion",
            "composition": composition,
            "assets_needed": [],
            "remotion_spec": remotion_spec,
            "estimated_duration": int(self._scene_duration_s(scene) * 30),
        }

    def _plan_ffmpeg_scene(self, scene: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        keywords = scene.get("keywords", [])
        duration = self._scene_duration_s(scene)
        return {
            "rendering_method": "ffmpeg",
            "assets_needed": keywords,
            "ffmpeg_instructions": {
                "ken_burns_type": self._select_ken_burns_type(scene),
                "duration": duration,
                "transition_next": self._select_transition_type(),
                },
            }

    def _scene_duration_s(self, scene: dict[str, Any]) -> float:
        value = scene.get("duration_s", scene.get("duration", 60))
        try:
            duration = float(value)
        except (TypeError, ValueError):
            return 60.0
        return duration if duration > 0 else 60.0

    def _select_ken_burns_type(self, scene: dict[str, Any]) -> str:
        visual_cues = str(scene.get("visual_cues", "")).lower()
        if "zoom in" in visual_cues:
            return "zoom_in"
        if "zoom out" in visual_cues:
            return "zoom_out"
        if "pan" in visual_cues and "left" in visual_cues:
            return "pan_left"
        if "pan" in visual_cues and "right" in visual_cues:
            return "pan_right"
        return random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right", "diagonal"])

    def _select_transition_type(self) -> str:
        return random.choice(["fade", "fade", "dissolve", "wiperight"])

    def _coerce_scene_plan(
        self,
        scene: dict[str, Any],
        visual_plan: dict[str, Any],
        research: ResearchBundle | None,
    ) -> ScenePlan:
        rendering_method = visual_plan.get("rendering_method", "ffmpeg")
        if rendering_method == "remotion":
            render_mode = "remotion"
        elif self._should_prefer_images(scene):
            render_mode = "image_motion"
        else:
            render_mode = "stock_video"

        asset_requests: list[AssetRequest] = []
        if render_mode != "remotion":
            for keyword in self._build_asset_queries(scene, render_mode):
                asset_requests.append(
                    AssetRequest(
                        kind="image" if render_mode == "image_motion" else "video",
                        query=str(keyword),
                        preferred_source="duckduckgo" if render_mode == "image_motion" else "pexels",
                        required=True,
                    )
                )

        ffmpeg_effects: list[str] = []
        if rendering_method == "ffmpeg":
            instructions = visual_plan.get("ffmpeg_instructions", {})
            ffmpeg_effects = [
                str(instructions.get("ken_burns_type", "zoom_in")),
                str(instructions.get("transition_next", "fade")),
            ]

        notes = str(scene.get("visual_cues", scene.get("narration", "")))
        if research is not None:
            notes = f"{notes} | Research: {research.summary}"

        remotion_spec = None
        if rendering_method == "remotion":
            composition_id = str(visual_plan.get("composition", "CustomTransition"))
            remotion_spec = get_registry().normalize_spec(
                RemotionSpec(
                    composition_id=composition_id,
                    props=visual_plan.get("remotion_spec", {}),
                    render_settings=CompositionRenderSettings(
                        duration_in_frames=int(visual_plan.get("estimated_duration", 90)),
                    ),
                )
            )

        return ScenePlan(
            scene_id=str(scene.get("scene_id") or f"scene-{scene.get('scene_number', 1)}"),
            render_mode=render_mode,
            asset_requests=asset_requests,
            ffmpeg_effects=ffmpeg_effects,
            remotion_composition=visual_plan.get("composition") if rendering_method == "remotion" else None,
            remotion_props=visual_plan.get("remotion_spec", {}) if rendering_method == "remotion" else {},
            remotion_spec=remotion_spec,
            subtitle_text=str(scene.get("narration", "")),
            notes=notes,
        )

    def _remotion_available(self) -> bool:
        try:
            return get_renderer().check_available()
        except Exception as exc:
            logger.warning("Remotion availability check failed, falling back to FFmpeg: %s", exc)
            return False

    def _should_prefer_images(self, scene: dict[str, Any]) -> bool:
        if self._requires_complex_motion(scene, {}):
            return True
        narration = str(scene.get("narration", ""))
        visual_intent = str(scene.get("visual_intent") or scene.get("visual_cues") or "")
        text = f"{narration} {visual_intent}".lower()
        if any(marker in text for marker in ["for example", "such as", "types of", "kinds of", "different", "compare"]):
            return True
        enumeration_items = self._extract_enumeration_items(text)
        return len(enumeration_items) >= 2

    def _build_asset_queries(self, scene: dict[str, Any], render_mode: str) -> list[str]:
        subject_variants = self._extract_subject_variants(scene)
        if subject_variants:
            queries = list(subject_variants[:4])
            for keyword in scene.get("keywords", []):
                normalized = self._normalize_visual_phrase(str(keyword))
                if normalized and normalized not in queries and len(queries) < 4:
                    queries.append(normalized)
            return queries

        visual_items = self._extract_visual_items(scene)
        if visual_items:
            return visual_items[:4] if render_mode == "image_motion" else visual_items[:3]
        keywords = scene.get("keywords", []) or [scene.get("visual_cues", scene.get("narration", "video"))]
        cleaned = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
        return cleaned[:4] if render_mode == "image_motion" else cleaned[:3]

    def _extract_visual_items(self, scene: dict[str, Any]) -> list[str]:
        items: list[str] = []
        subject_variants = self._extract_subject_variants(scene)
        for candidate in subject_variants:
            normalized = self._normalize_visual_phrase(candidate)
            if normalized and normalized not in items:
                items.append(normalized)

        for candidate in self._coerce_visual_list(scene.get("visual_intent")):
            normalized = self._normalize_visual_phrase(candidate)
            if normalized and normalized not in items:
                items.append(normalized)

        narration = str(scene.get("narration", ""))
        for candidate in self._extract_enumeration_items(narration):
            normalized = self._normalize_visual_phrase(candidate)
            if normalized and normalized not in items:
                items.append(normalized)

        for keyword in scene.get("keywords", []):
            normalized = self._normalize_visual_phrase(str(keyword))
            if normalized and normalized not in items:
                items.append(normalized)

        return items

    def _coerce_visual_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        text = str(value or "").strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed if str(item).strip()]
            except (SyntaxError, ValueError):
                pass
        parts = re.split(r"[.;]|,\s+(?=(?:a|an|the|[A-Z]))", text)
        return [part.strip() for part in parts if part.strip()]

    def _extract_enumeration_items(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", str(text or "")).strip(" .")
        if ":" in normalized:
            normalized = normalized.split(":", 1)[1]
        if not normalized:
            return []
        parts = re.split(r",| and | or ", normalized, flags=re.IGNORECASE)
        items: list[str] = []
        for part in parts:
            candidate = self._normalize_visual_phrase(part)
            if candidate and 1 < len(candidate.split()) <= 5 and candidate not in items:
                items.append(candidate)
        return items[:6]

    def _normalize_visual_phrase(self, value: str) -> str:
        text = re.sub(r"[\[\]\"']", "", str(value or "")).strip()
        text = re.split(r"Display text:|Text overlay:|Compare |Think |Cut ", text, maxsplit=1, flags=re.IGNORECASE)[0]
        text = text.split(".")[0]
        text = re.sub(r"^(show|image of|photo of|footage of|animation of|graphic of)\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^(a|an|the)\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip(" .")
        return text

    def _should_use_remotion_structured_layout(self, scene: dict[str, Any]) -> bool:
        if self._has_photo_cues(scene):
            return False
        return self._should_use_remotion_comparison(scene) or self._should_use_remotion_list_reveal(scene)

    def _should_use_remotion_comparison(self, scene: dict[str, Any]) -> bool:
        text = " ".join(str(scene.get(key, "")) for key in ("narration", "visual_intent", "visual_cues")).lower()
        markers = [
            " vs ",
            "versus",
            "compared to",
            "on the other hand",
            "split screen",
            "side by side",
            "one side",
            "other side",
        ]
        return any(marker in text for marker in markers)

    def _should_use_remotion_list_reveal(self, scene: dict[str, Any]) -> bool:
        text = " ".join(str(scene.get(key, "")) for key in ("narration", "visual_intent", "visual_cues")).lower()
        if not any(marker in text for marker in ["first", "second", "third", "finally", "steps", "reasons", "key points"]):
            return False
        return len(self._extract_enumeration_items(text)) >= 2

    def _has_photo_cues(self, scene: dict[str, Any]) -> bool:
        text = " ".join(str(scene.get(key, "")) for key in ("narration", "visual_intent", "visual_cues")).lower()
        return any(
            marker in text
            for marker in [
                "photo",
                "image",
                "footage",
                "duckduckgo",
                "pexels",
                "close-up",
                "close up",
                "portrait",
            ]
        )

    def _build_list_reveal_props(self, scene: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        items = self._extract_enumeration_items(
            " ".join(str(scene.get(key, "")) for key in ("narration", "visual_intent", "visual_cues"))
        )
        list_items = [{"title": item.title(), "subtitle": None} for item in items[:5]]
        return {
            "title": str(scene.get("purpose", "Key Points")).replace("_", " ").title(),
            "items": list_items or [{"title": str(scene.get("narration", ""))[:40], "subtitle": None}],
            "accentColor": context.get("accent_color", "#4ecdc4"),
            "backgroundColor": "#0f172a",
        }

    def _build_comparison_props(self, scene: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        left_title, right_title = self._extract_comparison_sides(scene)
        return {
            "headline": str(scene.get("purpose", "Comparison")).replace("_", " ").title(),
            "leftTitle": left_title,
            "leftBody": str(scene.get("narration", ""))[:120],
            "rightTitle": right_title,
            "rightBody": str(scene.get("visual_intent", ""))[:120] or str(scene.get("narration", ""))[:120],
            "accentColor": context.get("accent_color", "#4ecdc4"),
            "backgroundColor": "#111827",
        }

    def _extract_comparison_sides(self, scene: dict[str, Any]) -> tuple[str, str]:
        text = " ".join(str(scene.get(key, "")) for key in ("visual_intent", "narration", "visual_cues"))

        one_side_match = re.search(
            r"one side shows?\s+(.+?)(?:\.|,|\band\b|\bwhile\b|\bthe other side\b)",
            text,
            flags=re.IGNORECASE,
        )
        other_side_match = re.search(
            r"(?:the\s+)?other side shows?\s+(.+?)(?:\.|,|\band\b|\bwhile\b|$)",
            text,
            flags=re.IGNORECASE,
        )

        if one_side_match and other_side_match:
            left_title = self._normalize_visual_phrase(one_side_match.group(1)).title()
            right_title = self._normalize_visual_phrase(other_side_match.group(1)).title()
            if left_title and right_title:
                return left_title[:42], right_title[:42]

        items = self._extract_enumeration_items(text)
        left_title = items[0].title() if len(items) >= 1 else "Option A"
        right_title = items[1].title() if len(items) >= 2 else "Option B"
        return left_title, right_title

    def _extract_subject_variants(self, scene: dict[str, Any]) -> list[str]:
        text = " ".join(
            str(scene.get(key, "")) for key in ("narration", "visual_intent", "visual_cues")
        )
        variants: list[str] = []
        banned_modifiers = {"of", "type", "types", "kind", "kinds", "different"}
        for match in re.findall(r"\b([A-Za-z-]+\s+tomatoes?)\b", text, flags=re.IGNORECASE):
            candidate = match.strip()
            modifier = candidate.split()[0].lower()
            if modifier in banned_modifiers:
                continue
            if candidate.lower() not in {item.lower() for item in variants}:
                variants.append(candidate)
        return variants[:4]
