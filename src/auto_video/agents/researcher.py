"""Research agent for optional fact gathering."""

from __future__ import annotations

from typing import Any

from auto_video.agents.base import BaseAgent
from auto_video.agents.contracts import ResearchBundle, ResearchItem, VideoBrief


class ResearchAgent(BaseAgent):
    @property
    def role(self) -> str:
        return "Research Analyst"

    @property
    def goal(self) -> str:
        return "Collect concise factual anchors and angles for the script."

    def backstory(self) -> str:
        return "You produce compact research notes optimized for short-form video writing."

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

    def research(self, brief: VideoBrief) -> ResearchBundle:
        items = [
            ResearchItem(
                claim=f"{brief.title} should be framed through a concrete, visual example.",
                supporting_note="Anchor the topic with one vivid, memorable element early.",
                source_hint="internal-heuristic",
                confidence=0.72,
            ),
            ResearchItem(
                claim=f"{brief.title} benefits from a macro-to-micro explanation arc.",
                supporting_note="Start with the broad context, then narrow down to a striking detail.",
                source_hint="internal-heuristic",
                confidence=0.68,
            ),
        ]
        return ResearchBundle(
            topic=brief.title,
            summary=f"Research bundle for {brief.title} with concise factual and editorial anchors.",
            items=items,
            open_questions=[],
        )
