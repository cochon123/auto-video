"""LLM provider base classes."""

from abc import ABC, abstractmethod

from auto_video.config.schema import LLMProviderConfig


class LLMProvider(ABC):
    @abstractmethod
    def __init__(self, config: LLMProviderConfig) -> None: ...

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> str: ...

    @abstractmethod
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    @abstractmethod
    def get_model_name(self) -> str: ...


class MockLLMProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return f"[Mock response for prompt: {prompt[:50]}...]"

    def generate_with_tokens(self, prompt: str) -> tuple[str, int]:
        response = self.generate(prompt)
        return response, len(response.split())

    def health_check(self) -> bool:
        return True

    def get_model_name(self) -> str:
        return f"mock/{self.config.model}"
