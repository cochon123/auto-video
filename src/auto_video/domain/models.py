"""Shared domain models for auto-video.

These models define the core data structures exchanged between components.
This is the single source of truth for domain entities.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Type aliases
LanguageCode = str
VideoFormat = Literal["short", "long"]
ResearchConfidence = float
SceneComplexity = Literal["standard", "motion", "data_viz"]
RenderMode = Literal["stock_video", "image_motion", "remotion"]
AssetKind = Literal["video", "image", "music", "sfx", "remotion_component"]
AssetSource = Literal["pexels", "duckduckgo", "local", "generated"]
RiskLevel = Literal["low", "medium", "high"]
RemotionCompositionId = Literal[
    "Intro",
    "LowerThird",
    "CustomTransition",
    "DataViz",
    "ListReveal",
    "ComparisonCard",
]


class ContractBaseModel(BaseModel):
    """Base model for domain contracts."""

    model_config = ConfigDict(validate_assignment=True)


class VideoBrief(ContractBaseModel):
    """Brief describing the video to be created."""

    title: str
    language: LanguageCode
    format: VideoFormat
    target_duration_s: int
    audience: str
    tone: str
    requires_research: bool
    creative_direction: str
    factual_risk: RiskLevel

    @field_validator("title", "language", "audience", "tone", "creative_direction")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("target_duration_s")
    @classmethod
    def _validate_duration(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("target_duration_s must be positive")
        return value


class ResearchItem(ContractBaseModel):
    """Single research item with claim and supporting evidence."""

    claim: str
    supporting_note: str
    source_hint: str | None = None
    confidence: ResearchConfidence = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("claim", "supporting_note")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("source_hint")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ResearchBundle(ContractBaseModel):
    """Collection of research items on a topic."""

    topic: str
    summary: str
    items: list[ResearchItem] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @field_validator("topic", "summary")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("open_questions", mode="before")
    @classmethod
    def _normalize_questions(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return [str(item).strip() for item in value if str(item).strip()]


class ScriptScene(ContractBaseModel):
    """Single scene in a video script."""

    scene_id: str
    order: int
    purpose: str
    narration: str
    duration_s: float
    visual_intent: str
    sound_intent: str | None = None
    complexity: SceneComplexity = "standard"
    keywords: list[str] = Field(default_factory=list)

    @field_validator("scene_id", "purpose", "narration", "visual_intent")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("duration_s")
    @classmethod
    def _validate_duration(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("duration_s must be positive")
        return value

    @field_validator("order")
    @classmethod
    def _validate_order(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("order must be positive")
        return value

    @field_validator("sound_intent")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("keywords", mode="before")
    @classmethod
    def _normalize_keywords(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return [str(item).strip() for item in value if str(item).strip()]


class ScriptPlan(ContractBaseModel):
    """Complete script plan with all scenes."""

    title: str
    hook: str
    scenes: list[ScriptScene]
    closing_cta: str | None = None

    @field_validator("title", "hook")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("closing_cta")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("scenes")
    @classmethod
    def _validate_scenes(cls, value: list[ScriptScene]) -> list[ScriptScene]:
        if not value:
            raise ValueError("scenes must not be empty")
        return sorted(value, key=lambda scene: scene.order)


class AssetRequest(ContractBaseModel):
    """Request for a visual asset."""

    kind: AssetKind
    query: str
    preferred_source: AssetSource | None = None
    required: bool = True

    @field_validator("query")
    @classmethod
    def _strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be empty")
        return value


class ScenePlan(ContractBaseModel):
    """Plan for rendering a single scene."""

    scene_id: str
    render_mode: RenderMode
    asset_requests: list[AssetRequest] = Field(default_factory=list)
    ffmpeg_effects: list[str] = Field(default_factory=list)
    remotion_composition: str | None = None
    remotion_props: dict[str, Any] = Field(default_factory=dict)
    remotion_spec: "RemotionSpec | None" = None
    subtitle_text: str = ""
    notes: str = ""

    @field_validator("scene_id")
    @classmethod
    def _strip_scene_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("scene_id must not be empty")
        return value

    @field_validator("subtitle_text", "notes")
    @classmethod
    def _strip_optional_text(cls, value: str) -> str:
        return value.strip()


class TimelineAsset(ContractBaseModel):
    """Asset placed on the timeline."""

    asset_id: str
    path: str
    source: str
    start_s: float
    end_s: float
    role: str
    scene_start_s: float | None = None
    scene_end_s: float | None = None


class CompositionRenderSettings(ContractBaseModel):
    """Render settings for a Remotion composition."""

    fps: int = 30
    width: int = 1920
    height: int = 1080
    duration_in_frames: int | None = None


class RemotionAsset(ContractBaseModel):
    """Asset consumed by a Remotion composition."""

    asset_id: str
    kind: Literal["image", "video", "audio", "data"]
    path: str
    role: str


class RemotionSpec(ContractBaseModel):
    """Typed specification for rendering a Remotion composition."""

    composition_id: RemotionCompositionId
    props: dict[str, Any] = Field(default_factory=dict)
    assets: list[RemotionAsset] = Field(default_factory=list)
    render_settings: CompositionRenderSettings = Field(default_factory=CompositionRenderSettings)


class TimelineScene(ContractBaseModel):
    """Scene placed on the timeline."""

    scene_id: str
    start_s: float
    end_s: float
    narration: str
    subtitles: str
    render_mode: str
    assets: list[TimelineAsset] = Field(default_factory=list)
    effects: list[str] = Field(default_factory=list)
    remotion_source_file: str | None = None
    remotion_composition: str | None = None
    remotion_props: dict[str, Any] = Field(default_factory=dict)
    remotion_spec: RemotionSpec | None = None
    editable_notes: str = ""


class VideoManifest(ContractBaseModel):
    """Complete manifest for video generation."""

    video_id: str
    title: str
    language: str
    total_duration_s: float
    scenes: list[TimelineScene] = Field(default_factory=list)
    workspace_dir: str
    output_video: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewResult(ContractBaseModel):
    """Result of script review."""

    approved: bool
    score: float
    feedback: str
    revision_requests: list[str] = Field(default_factory=list)
    criteria_scores: dict[str, float] = Field(default_factory=dict)


class OrchestrationResult(ContractBaseModel):
    """Result of agent orchestration."""

    brief: VideoBrief
    research: ResearchBundle | None = None
    script: ScriptPlan
    review: ReviewResult
    scene_plans: list[ScenePlan] = Field(default_factory=list)
    manifest: VideoManifest
    manifest_path: str | None = None
    backend: Literal["crewai", "local"] = "local"


__all__ = [
    # Type aliases
    "AssetKind",
    "AssetRequest",
    "AssetSource",
    "CompositionRenderSettings",
    "LanguageCode",
    "ResearchBundle",
    "ResearchConfidence",
    "ResearchItem",
    "RemotionAsset",
    "RemotionCompositionId",
    "RemotionSpec",
    "RenderMode",
    "RiskLevel",
    "SceneComplexity",
    "ScriptPlan",
    "ScriptScene",
    "TimelineAsset",
    "TimelineScene",
    "VideoBrief",
    "VideoFormat",
    "VideoManifest",
    "OrchestrationResult",
    "ReviewResult",
    "ContractBaseModel",
]
