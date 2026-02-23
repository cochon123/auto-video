"""LLM provider implementations."""

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.provider_base import LLMProvider, MockLLMProvider


def create_provider(config: LLMProviderConfig) -> LLMProvider:
    provider_name = config.provider.lower()
    if provider_name == "mock":
        return MockLLMProvider(config)
    if provider_name == "openai":
        from auto_video.providers.llm.openai import OpenAIProvider

        return OpenAIProvider(config)
    if provider_name == "anthropic":
        from auto_video.providers.llm.anthropic import AnthropicProvider

        return AnthropicProvider(config)
    if provider_name == "groq":
        from auto_video.providers.llm.groq import GroqProvider

        return GroqProvider(config)
    if provider_name == "google":
        from auto_video.providers.llm.google import GoogleProvider

        return GoogleProvider(config)
    if provider_name == "zhipuai":
        from auto_video.providers.llm.zhipuai import ZhipuAIProvider

        return ZhipuAIProvider(config)
    if provider_name == "ollama":
        from auto_video.providers.llm.ollama import OllamaProvider

        return OllamaProvider(config)
    if provider_name == "llamacpp":
        from auto_video.providers.llm.llamacpp import LlamaCppProvider

        return LlamaCppProvider(config)
    return MockLLMProvider(config)


__all__ = [
    "create_provider",
]
