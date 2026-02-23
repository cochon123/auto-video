"""Test TTS interface."""

from pathlib import Path

import pytest

from auto_video.config.schema import TTSConfig
from auto_video.core.tts import (
    TTS,
    MockTTSProvider,
    TTSProvider,
)


def test_tts_provider_is_abstract():
    """Test TTSProvider is abstract and cannot be instantiated."""
    config = TTSConfig(mode="local", provider="mock")
    with pytest.raises(TypeError):
        TTSProvider(config)


def test_mock_tts_provider_instantiation():
    """Test MockTTSProvider can be instantiated."""
    config = TTSConfig(mode="local", provider="mock", voice="default")
    provider = MockTTSProvider(config)

    assert provider.config == config


def test_mock_tts_provider_synthesize_creates_file_and_returns_duration(tmp_path: Path):
    """Test MockTTSProvider.synthesize creates file and returns duration."""
    config = TTSConfig(mode="local", provider="mock", voice="male")
    provider = MockTTSProvider(config)

    output_path = tmp_path / "output.wav"
    duration = provider.synthesize("Test text for synthesis", output_path, "male")

    assert output_path.exists()
    assert output_path.read_bytes() == b"MOCK_AUDIO_DATA"
    assert duration > 0
    assert duration == len("Test text for synthesis".split()) * 0.3


def test_mock_tts_provider_health_check():
    """Test MockTTSProvider.health_check returns True."""
    config = TTSConfig(mode="local", provider="mock")
    provider = MockTTSProvider(config)

    result = provider.health_check()

    assert result is True


def test_mock_tts_provider_get_available_voices():
    """Test MockTTSProvider.get_available_voices returns voice list."""
    config = TTSConfig(mode="local", provider="mock")
    provider = MockTTSProvider(config)

    voices = provider.get_available_voices()

    assert isinstance(voices, list)
    assert len(voices) > 0
    assert "default" in voices
    assert "male" in voices
    assert "female" in voices


def test_tts_initialization():
    """Test TTS class initialization with MockTTSProvider."""
    config = TTSConfig(mode="local", provider="mock", voice="female")
    tts = TTS(config)

    assert tts.config == config
    assert isinstance(tts.provider, MockTTSProvider)


def test_tts_provider_property():
    """Test TTS provider property returns the provider instance."""
    config = TTSConfig(mode="local", provider="mock", voice="default")
    tts = TTS(config)

    provider = tts.provider

    assert isinstance(provider, MockTTSProvider)
    assert provider.config == config


def test_tts_synthesize_script(tmp_path: Path):
    """Test TTS.synthesize_script works with temporary directory."""
    config = TTSConfig(mode="local", provider="mock", voice="male")
    tts = TTS(config)

    output_path = tmp_path / "audio.wav"
    duration = tts.synthesize_script("This is a test script for synthesis", output_path)

    assert output_path.exists()
    assert output_path.read_bytes() == b"MOCK_AUDIO_DATA"
    assert duration > 0


def test_tts_synthesize_script_long_text(tmp_path: Path):
    """Test TTS.synthesize_script with long text creates multiple segments."""
    config = TTSConfig(mode="local", provider="mock", voice="female")
    tts = TTS(config)

    long_text = " ".join(["word"] * 1500)
    output_path = tmp_path / "long_audio.wav"
    duration = tts.synthesize_script(long_text, output_path)

    assert output_path.exists()
    assert duration > 0


def test_tts_get_available_voices():
    """Test TTS.get_available_voices returns voices."""
    config = TTSConfig(mode="local", provider="mock")
    tts = TTS(config)

    voices = tts.get_available_voices()

    assert isinstance(voices, list)
    assert len(voices) > 0
    assert "default" in voices


def test_segment_text_splits_long_text():
    """Test _segment_text splits long text into chunks."""
    config = TTSConfig(mode="local", provider="mock")
    tts = TTS(config)

    long_text = ". ".join(["sentence"] * 60)
    segments = tts._segment_text(long_text, max_chars=500)

    assert len(segments) > 1
    assert all(len(segment) <= 500 for segment in segments)


def test_segment_text_handles_short_text():
    """Test _segment_text handles short text (no splitting)."""
    config = TTSConfig(mode="local", provider="mock")
    tts = TTS(config)

    short_text = "This is a short text."
    segments = tts._segment_text(short_text, max_chars=1000)

    assert len(segments) == 1
    assert segments[0] == short_text


def test_segment_text_handles_multiple_paragraphs():
    """Test _segment_text handles multiple paragraphs."""
    config = TTSConfig(mode="local", provider="mock")
    tts = TTS(config)

    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    segments = tts._segment_text(text, max_chars=50)

    assert len(segments) > 1
    assert all(len(segment) <= 50 for segment in segments)


def test_tts_uses_fallback_provider():
    """Test TTS creates MockTTSProvider for unknown providers."""
    config = TTSConfig(mode="api", provider="unknown")
    tts = TTS(config)

    assert isinstance(tts.provider, MockTTSProvider)


def test_tts_synthesize_script_with_config_voice(tmp_path: Path):
    """Test TTS.synthesize_script uses config voice when specified."""
    config = TTSConfig(mode="local", provider="mock", voice="female")
    tts = TTS(config)

    output_path = tmp_path / "audio.wav"
    duration = tts.synthesize_script("Test script", output_path)

    assert output_path.exists()
    assert duration > 0
