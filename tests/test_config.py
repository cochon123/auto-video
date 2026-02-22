"""Test configuration schema."""

from pathlib import Path

import pytest

from auto_video.config.schema import (
    AppConfig,
    ImageGenConfig,
    LLMProviderConfig,
    StorageConfig,
    TTSConfig,
    VisualsConfig,
    YouTubeConfig,
)


def test_llm_provider_config():
    """Test LLM provider config."""
    config = LLMProviderConfig(
        provider="openai",
        model="gpt-4",
        api_key="test-key",
        temperature=0.7,
    )
    assert config.provider == "openai"
    assert config.model == "gpt-4"
    assert config.api_key == "test-key"
    assert config.temperature == 0.7


def test_tts_config():
    """Test TTS config."""
    config = TTSConfig(mode="local", voice="test-voice")
    assert config.mode == "local"
    assert config.voice == "test-voice"
    assert config.model is None


def test_tts_config_api():
    """Test TTS config with API."""
    config = TTSConfig(
        mode="api",
        provider="elevenlabs",
        api_key="test-key",
        voice="voice-id",
    )
    assert config.mode == "api"
    assert config.provider == "elevenlabs"
    assert config.api_key == "test-key"


def test_image_gen_config():
    """Test image generation config."""
    config = ImageGenConfig(enabled=True, model="test-model")
    assert config.enabled is True
    assert config.model == "test-model"
    assert config.steps == 6


def test_visuals_config():
    """Test visuals config."""
    config = VisualsConfig(mode="stock", providers=["pexels", "pixabay"])
    assert config.mode == "stock"
    assert "pexels" in config.providers
    assert "pixabay" in config.providers


def test_visuals_config_local():
    """Test visuals config with local path."""
    config = VisualsConfig(mode="local", local_path="/path/to/videos")
    assert config.mode == "local"
    assert config.local_path == "/path/to/videos"


def test_storage_config():
    """Test storage config."""
    config = StorageConfig(
        videos_path=Path("/tmp/videos"),
        temp_path=Path("/tmp/temp"),
        keep_temp=False,
    )
    assert config.videos_path == Path("/tmp/videos")
    assert config.temp_path == Path("/tmp/temp")
    assert config.keep_temp is False


def test_youtube_config():
    """Test YouTube config."""
    config = YouTubeConfig(
        enabled=True,
        credentials_path=Path("/creds.json"),
        default_privacy="public",
    )
    assert config.enabled is True
    assert config.credentials_path == Path("/creds.json")
    assert config.default_privacy == "public"


def test_app_config_full():
    """Test complete app config."""
    config = AppConfig(
        llm={"provider": "openai", "model": "gpt-4", "api_key": "test"},
        tts={"mode": "local", "voice": "default"},
        visuals={"mode": "stock", "providers": ["pexels"]},
        image_gen={"enabled": False},
        storage={
            "videos_path": Path("/tmp/videos"),
            "temp_path": Path("/tmp/temp"),
        },
        youtube={"enabled": False},
        default_format="long",
        default_lang="fr",
    )
    assert config.llm.provider == "openai"
    assert config.tts.mode == "local"
    assert config.visuals.mode == "stock"
    assert config.image_gen.enabled is False
    assert config.default_format == "long"
    assert config.default_lang == "fr"


def test_app_config_defaults():
    """Test app config with defaults."""
    config = AppConfig(
        llm={"provider": "openai", "model": "gpt-4", "api_key": "test"},
        tts={"mode": "local", "voice": "default"},
        visuals={"mode": "stock"},
        image_gen={"enabled": False},
        storage={
            "videos_path": Path("/tmp/videos"),
            "temp_path": Path("/tmp/temp"),
        },
        youtube={"enabled": False},
    )
    assert config.default_format == "long"
    assert config.default_lang == "fr"
    assert config.visuals.providers == []


def test_app_config_validation():
    """Test that invalid values raise validation errors."""
    with pytest.raises(Exception):
        AppConfig(
            llm={"provider": "openai", "model": "gpt-4", "api_key": "test"},
            tts={"mode": "invalid", "voice": "default"},
            visuals={"mode": "stock"},
            image_gen={"enabled": False},
            storage={
                "videos_path": Path("/tmp/videos"),
                "temp_path": Path("/tmp/temp"),
            },
            youtube={"enabled": False},
        )
