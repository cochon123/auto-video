"""Configuration schema using Pydantic models."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class LLMProviderConfig(BaseModel):
    """LLM provider configuration."""

    provider: str
    model: str
    api_key: str | None = None
    host: str | None = None
    temperature: float = 0.7


class TTSConfig(BaseModel):
    """TTS configuration."""

    mode: Literal["local", "api", "hybrid"]
    model: str | None = None
    voice: str = "default"
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

    llm: LLMProviderConfig
    tts: TTSConfig
    visuals: VisualsConfig
    image_gen: ImageGenConfig
    storage: StorageConfig
    youtube: YouTubeConfig
    video: VideoConfig = VideoConfig()
    default_format: Literal["short", "long"] = "long"
    default_lang: str = "fr"
