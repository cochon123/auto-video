"""TTS provider implementations."""

from auto_video.config.schema import TTSConfig
from auto_video.core.tts import MockTTSProvider, TTSProvider


def create_provider(config: TTSConfig) -> TTSProvider:
    # When mode is local, use kokoro by default
    if config.mode == "local" or config.provider == "kokoro":
        from auto_video.providers.tts.kokoro import KokoroTTSProvider

        return KokoroTTSProvider(config)

    provider_name = (config.provider or "mock").lower()
    if provider_name == "mock":
        return MockTTSProvider(config)
    if provider_name == "kokoro":
        from auto_video.providers.tts.kokoro import KokoroTTSProvider

        return KokoroTTSProvider(config)
    if provider_name == "elevenlabs":
        from auto_video.providers.tts.elevenlabs import ElevenLabsProvider

        return ElevenLabsProvider(config)
    if provider_name == "openai":
        from auto_video.providers.tts.openai_tts import OpenAITTSProvider

        return OpenAITTSProvider(config)
    return MockTTSProvider(config)


__all__ = [
    "create_provider",
]
