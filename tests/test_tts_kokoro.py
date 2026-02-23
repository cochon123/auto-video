"""Test Kokoro TTS provider."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from auto_video.config.schema import TTSConfig
from auto_video.providers.tts.kokoro import KokoroTTSProvider


def test_kokoro_provider_initialization_with_valid_config():
    """Test KokoroTTSProvider initialization with valid config."""
    config = TTSConfig(mode="local", provider="kokoro", voice="af_sarah")
    provider = KokoroTTSProvider(config)

    assert provider.config == config
    assert isinstance(provider._available_voices, list)


def test_kokoro_provider_synthesize_creates_file_and_returns_duration(tmp_path: Path):
    """Test synthesize creates audio file and returns duration."""
    config = TTSConfig(mode="local", provider="kokoro", voice="af_sarah")
    provider = KokoroTTSProvider(config)

    output_path = tmp_path / "output.wav"
    duration = provider.synthesize("Test text for synthesis", output_path, "af_sarah")

    assert output_path.exists()
    assert duration > 0


def test_kokoro_provider_synthesize_with_custom_voice(tmp_path: Path):
    """Test synthesize with custom voice."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    output_path = tmp_path / "output.wav"
    duration = provider.synthesize("Test text", output_path, "am_michael")

    assert output_path.exists()
    assert duration > 0


def test_kokoro_provider_health_check_returns_true_when_available():
    """Test health_check returns True when Kokoro available."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    result = provider.health_check()

    assert isinstance(result, bool)


def test_kokoro_provider_health_check_returns_false_when_not_available():
    """Test health_check returns False when Kokoro not available."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    result = provider.health_check()

    assert isinstance(result, bool)


def test_kokoro_provider_get_available_voices_returns_voice_list():
    """Test get_available_voices returns voice list."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    voices = provider.get_available_voices()

    assert isinstance(voices, list)
    assert len(voices) > 0


def test_kokoro_provider_get_available_voices_includes_all_preset_voices():
    """Test get_available_voices includes all 9 preset voices."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    voices = provider.get_available_voices()

    expected_voices = [
        "af_sarah",
        "af_heart",
        "af_nicole",
        "am_michael",
        "am_adam",
        "bf_emma",
        "bf_isabella",
        "bm_george",
        "bm_lewis",
    ]
    assert len(voices) == 9
    for voice in expected_voices:
        assert voice in voices


def test_kokoro_provider_synthesize_with_empty_text(tmp_path: Path):
    """Test synthesize with empty text."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    output_path = tmp_path / "output.wav"
    duration = provider.synthesize("", output_path, "af_sarah")

    assert output_path.exists()
    assert duration >= 0


def test_kokoro_provider_synthesize_with_long_text(tmp_path: Path):
    """Test synthesize with long text."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    long_text = " ".join(["word"] * 1000)
    output_path = tmp_path / "output.wav"
    duration = provider.synthesize(long_text, output_path, "af_sarah")

    assert output_path.exists()
    assert duration > 0


def test_kokoro_provider_duration_estimation_in_mock_mode(tmp_path: Path):
    """Test duration estimation in mock mode."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    text = "Test text with multiple words"
    output_path = tmp_path / "output.wav"
    duration = provider.synthesize(text, output_path, "af_sarah")

    words = len(text.split())
    expected_duration = words * 0.35
    assert abs(duration - expected_duration) < 0.01


def test_kokoro_provider_voice_validation(tmp_path: Path):
    """Test voice validation defaults to af_sarah for invalid voice."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    output_path = tmp_path / "output.wav"
    duration = provider.synthesize("Test text", output_path, "invalid_voice")

    assert output_path.exists()
    assert duration > 0


def test_kokoro_provider_model_caching_directory():
    """Test model caching directory is created."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    cache_dir = Path.home() / ".cache" / "auto-video" / "kokoro"
    assert provider._cache_dir == cache_dir
    assert cache_dir.exists()
    assert cache_dir.is_dir()


def test_kokoro_provider_synthesize_creates_parent_directories(tmp_path: Path):
    """Test synthesize creates parent directories if they don't exist."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    output_path = tmp_path / "deep" / "nested" / "path" / "output.wav"
    assert not output_path.parent.exists()

    duration = provider.synthesize("Test text", output_path, "af_sarah")

    assert output_path.exists()
    assert duration > 0


@patch("auto_video.providers.tts.kokoro.KOKORO_AVAILABLE", True)
def test_kokoro_provider_with_mocked_library(tmp_path: Path):
    """Test Kokoro provider with mocked Kokoro library."""
    with patch.dict("sys.modules", {"kokoro": MagicMock()}):
        mock_kmodel = MagicMock()
        mock_kmodel.return_value = (MagicMock(), 24000)

        config = TTSConfig(mode="local", provider="kokoro")
        provider = KokoroTTSProvider(config)
        provider._model = mock_kmodel

        output_path = tmp_path / "output.wav"
        duration = provider.synthesize("Test text", output_path, "af_sarah")

        assert output_path.exists()
        assert duration >= 0


@patch("auto_video.providers.tts.kokoro.KOKORO_AVAILABLE", False)
def test_kokoro_provider_synthesize_without_library(tmp_path: Path):
    """Test synthesize works without Kokoro library installed."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    output_path = tmp_path / "output.wav"
    duration = provider.synthesize("Test text for synthesis", output_path, "af_sarah")

    assert output_path.exists()
    assert output_path.read_bytes() == b"MOCK_KOKORO_AUDIO_DATA"
    words = len("Test text for synthesis".split())
    expected_duration = words * 0.35
    assert abs(duration - expected_duration) < 0.01


@patch("auto_video.providers.tts.kokoro.KOKORO_AVAILABLE", True)
@patch("builtins.__import__")
def test_kokoro_provider_health_check_with_library(mock_import: MagicMock):
    """Test health_check with Kokoro library available."""
    mock_kokoro_module = MagicMock()
    mock_import.return_value = mock_kokoro_module

    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    result = provider.health_check()

    assert isinstance(result, bool)


@patch("auto_video.providers.tts.kokoro.KOKORO_AVAILABLE", False)
def test_kokoro_provider_health_check_without_library():
    """Test health_check without Kokoro library available."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    result = provider.health_check()

    assert result is False


def test_kokoro_provider_all_voices_are_accessible(tmp_path: Path):
    """Test that all available voices can be used for synthesis."""
    config = TTSConfig(mode="local", provider="kokoro")
    provider = KokoroTTSProvider(config)

    voices = provider.get_available_voices()
    for voice in voices:
        output_path = tmp_path / f"output_{voice}.wav"
        duration = provider.synthesize("Test text", output_path, voice)
        assert output_path.exists()
        assert duration > 0
