"""
Auto-Video Agents Module.

Multi-agent system for video generation using CrewAI.
"""

__version__ = "1.0.0"

from auto_video.agents.base import BaseAgent
from auto_video.agents.contracts import (
    AssetRequest,
    ResearchBundle,
    ResearchItem,
    ScenePlan,
    ScriptPlan,
    ScriptScene,
    VideoBrief,
)
from auto_video.agents.director import DirectorAgent
from auto_video.agents.orchestrator import AgentOrchestrator
from auto_video.agents.researcher import ResearchAgent
from auto_video.agents.reviewer import ReviewResult, ReviewerAgent
from auto_video.agents.scriptwriter import ScriptwriterAgent
from auto_video.agents.visual_curator import VisualCuratorAgent

__all__ = [
    "AssetRequest",
    "BaseAgent",
    "AgentOrchestrator",
    "DirectorAgent",
    "ResearchAgent",
    "ResearchBundle",
    "ResearchItem",
    "ReviewResult",
    "ScenePlan",
    "ScriptPlan",
    "ScriptScene",
    "ScriptwriterAgent",
    "VideoBrief",
    "VisualCuratorAgent",
    "ReviewerAgent",
]
