"""Shared multi-agent contracts for auto-video.

This module is now a thin compatibility wrapper around the domain models.
All models are now defined in auto_video.domain.models.

For new code, prefer importing from auto_video.domain:
    from auto_video.domain import VideoBrief, ScriptPlan, ResearchBundle

DEPRECATED: This module will be removed in a future version.
Please update your imports to use auto_video.domain instead.
"""

from __future__ import annotations

# Import all models from the domain module
from auto_video.domain.models import (
    # Type aliases
    AssetKind,
    AssetRequest,
    AssetSource,
    DurationHintSource,
    LanguageCode,
    ResearchConfidence,
    RiskLevel,
    SceneComplexity,
    VideoFormat,
    # Domain models
    ContractBaseModel,
    CompositionRenderSettings,
    ResearchBundle,
    ResearchItem,
    RemotionAsset,
    RemotionSpec,
    ScriptScene,
    ScriptPlan,
    AssetRequest as _AssetRequest,
    ScenePlan,
    TimelineAsset,
    TimelineScene,
    VideoManifest,
    VideoBrief,
    ReviewResult,
    OrchestrationResult,
    # Re-export AssetRequest for backwards compatibility
)

# Re-export everything for backwards compatibility
__all__ = [
    "AssetKind",
    "AssetRequest",
    "AssetSource",
    "ContractBaseModel",
    "CompositionRenderSettings",
    "DurationHintSource",
    "LanguageCode",
    "ResearchBundle",
    "ResearchConfidence",
    "ResearchItem",
    "RemotionAsset",
    "RemotionSpec",
    "RenderMode",
    "RiskLevel",
    "OrchestrationResult",
    "ReviewResult",
    "SceneComplexity",
    "ScenePlan",
    "ScriptPlan",
    "ScriptScene",
    "TimelineAsset",
    "TimelineScene",
    "VideoBrief",
    "VideoFormat",
    "VideoManifest",
]

# Note: RenderMode is also in domain.models, add it
from auto_video.domain.models import RenderMode
__all__.append("RenderMode")
