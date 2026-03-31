"""Configuration schema using Pydantic models."""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class LLMProviderConfig(BaseModel):
    """LLM provider configuration (legacy, for backward compatibility)."""

    provider: str
    model: str
    api_key: str | None = None
    host: str | None = None
    temperature: float = 0.7


class ProviderCredentials(BaseModel):
    """API credentials for a provider (no model specified)."""

    provider: str  # Provider type: openai, anthropic, openrouter, google, etc.
    api_key: str | None = None
    host: str | None = None  # For Ollama or custom endpoints


class AgentModelConfig(BaseModel):
    """Model configuration for a single agent."""

    provider: str  # Key from llm_providers dict
    model: str  # Model name/ID
    temperature: float | None = None  # Optional: override default temperature


class LLMConfig(BaseModel):
    """Multi-provider LLM configuration with per-agent model selection."""

    # Provider credentials (provider -> credentials mapping)
    providers: dict[str, ProviderCredentials] = Field(default_factory=dict)

    # Per-agent model configuration
    agent_models: dict[str, AgentModelConfig] = Field(default_factory=dict)

    # Legacy fields for backward compatibility
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    host: str | None = None
    temperature: float = 0.7

    def get_agent_config(self, agent_name: str) -> LLMProviderConfig:
        """Get LLMProviderConfig for a specific agent."""
        if agent_name in self.agent_models:
            agent_config = self.agent_models[agent_name]
            creds = self.providers.get(agent_config.provider)
            if creds:
                return LLMProviderConfig(
                    provider=creds.provider,
                    model=agent_config.model,
                    api_key=creds.api_key,
                    host=creds.host,
                    temperature=agent_config.temperature or 0.7,
                )

        # Fallback: legacy config or first available provider
        if self.provider and self.model:
            return LLMProviderConfig(
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                host=self.host,
                temperature=self.temperature,
            )

        # Try to use first available provider with a default model
        if self.providers:
            first_provider_name = next(iter(self.providers))
            first_provider = self.providers[first_provider_name]
            return LLMProviderConfig(
                provider=first_provider.provider,
                model="gpt-4o",  # Default fallback model
                api_key=first_provider.api_key,
                host=first_provider.host,
                temperature=0.7,
            )

        raise ValueError(f"No configuration found for agent '{agent_name}'")


class TTSConfig(BaseModel):
    """TTS configuration."""

    mode: Literal["local", "api", "hybrid"]
    model: str | None = None
    voice: str = "default"
    lang: str = "en-us"  # Language for multi-lingual TTS (en-us, fr-fr, es, it, pt-br, hi, ja, zh)
    api_key: str | None = None
    provider: str | None = None


class ImageGenConfig(BaseModel):
    """Image generation configuration."""

    enabled: bool = False
    mode: Literal["local", "api"] = "local"
    model: str = "Z-Image/Z-Image-Turbo"
    lora: str | None = None
    steps: int = 6
    api_key: str | None = None
    provider: str | None = None


class VisualsConfig(BaseModel):
    """Visuals source configuration."""

    mode: Literal["stock", "local", "generated", "hybrid"] = "stock"
    providers: list[str] = []
    local_path: str | None = None
    pexels_api_key: str | None = None
    pixabay_api_key: str | None = None
    visual_llm: LLMProviderConfig | None = None
    # New fields for enhanced visual system
    enable_images: bool = True  # Allow using images in addition to videos
    image_ratio: float = 0.3  # Target ratio of images to total media (0.0 = all videos, 1.0 = all images)
    structured_output: bool = True  # Use structured JSON output from LLM for better parsing


class StorageConfig(BaseModel):
    """Storage configuration."""

    videos_path: Path
    temp_path: Path
    keep_temp: bool = True


class YouTubeConfig(BaseModel):
    """YouTube upload configuration."""

    enabled: bool = False
    credentials_path: Path | None = None
    default_privacy: Literal["public", "unlisted", "private"] = "unlisted"
    default_category: str = "22"
    auto_tags: bool = True


class VideoConfig(BaseModel):
    """Video encoding configuration."""

    gpu_acceleration: Literal["auto", "nvenc", "amf", "qsv", "cpu", "none"] = "auto"
    preset: Literal["slow", "medium", "fast", "veryfast", "ultrafast"] = "fast"
    quality: int = 22


class AppConfig(BaseModel):
    """Main application configuration."""

    llm: LLMConfig
    tts: TTSConfig
    visuals: VisualsConfig
    image_gen: ImageGenConfig
    storage: StorageConfig
    youtube: YouTubeConfig
    video: VideoConfig = VideoConfig()
    default_format: Literal["short", "long"] = "long"
    default_lang: str = "fr"

    @field_validator("llm", mode="before")
    @classmethod
    def coerce_llm_config(cls, v: Any) -> Any:
        """Coerce legacy LLMProviderConfig to LLMConfig."""
        if isinstance(v, LLMProviderConfig):
            # Legacy single-provider config
            return LLMConfig(
                providers={"default": ProviderCredentials(
                    provider=v.provider,
                    api_key=v.api_key,
                    host=v.host,
                )},
                agent_models={
                    "default": AgentModelConfig(
                        provider="default",
                        model=v.model,
                        temperature=v.temperature,
                    )
                },
                provider=v.provider,
                model=v.model,
                api_key=v.api_key,
                host=v.host,
                temperature=v.temperature,
            )
        return v
