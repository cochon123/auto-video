"""TTS provider implementations."""

import logging

from auto_video.config.schema import TTSConfig
from auto_video.core.tts import MockTTSProvider, TTSProvider

logger = logging.getLogger(__name__)


def _load_kokoro_provider():
    try:
        from auto_video.providers.tts.kokoro import KokoroTTSProvider

        return KokoroTTSProvider
    except ImportError as exc:
        logger.warning("Kokoro TTS is unavailable, falling back to MockTTSProvider: %s", exc)
        return None


def create_provider(config: TTSConfig) -> TTSProvider:
    provider_name = (config.provider or "mock").lower()
    if provider_name == "mock":
        return MockTTSProvider(config)
    if provider_name == "kokoro":
        kokoro_provider = _load_kokoro_provider()
        return kokoro_provider(config) if kokoro_provider else MockTTSProvider(config)
    if provider_name == "elevenlabs":
        from auto_video.providers.tts.elevenlabs import ElevenLabsProvider

        return ElevenLabsProvider(config)
    if provider_name == "openai":
        from auto_video.providers.tts.openai_tts import OpenAITTSProvider

        return OpenAITTSProvider(config)
    if config.mode in {"local", "hybrid"}:
        kokoro_provider = _load_kokoro_provider()
        if kokoro_provider is not None:
            return kokoro_provider(config)
        return MockTTSProvider(config)
    return MockTTSProvider(config)


__all__ = [
    "create_provider",
]
