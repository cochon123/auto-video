"""Base helpers for multi-agent orchestration."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseAgent(ABC):
    """Abstract base class for all auto-video agents."""

    def __init__(self, llm_provider: Any):
        self.llm = llm_provider

    @abstractmethod
    def create_crewai_agent(self) -> Any:
        """Create a CrewAI agent instance when CrewAI is available."""

    @property
    @abstractmethod
    def role(self) -> str:
        """Return the role of this agent."""

    @property
    @abstractmethod
    def goal(self) -> str:
        """Return the goal of this agent."""

    @abstractmethod
    def backstory(self) -> str:
        """Return the backstory of this agent."""

    def _generate(self, prompt: str) -> str:
        if hasattr(self.llm, "provider"):
            return self.llm.provider.generate(prompt)
        if hasattr(self.llm, "generate"):
            return self.llm.generate(prompt)
        raise TypeError("Unsupported LLM provider for agent generation")

    def _parse_json(self, response: str) -> dict[str, Any]:
        match = re.search(r"\{[\s\S]*\}", response)
        if not match:
            raise ValueError("No JSON object found in response")
        return json.loads(match.group(0))

    def _validate_model(self, model: type[ModelT], payload: dict[str, Any]) -> ModelT:
        return model.model_validate(payload)
