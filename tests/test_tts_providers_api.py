"""Test TTS API providers."""

from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest

from auto_video.config.schema import TTSConfig
from auto_video.providers.tts.elevenlabs import ElevenLabsError, ElevenLabsProvider
from auto_video.providers.tts.openai_tts import OpenAITTSError, OpenAITTSProvider


def test_elevenlabs_provider_initialization_with_valid_config():
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)

    assert provider.config == config
    assert provider._api_key == "test_key"


def test_elevenlabs_provider_initialization_without_api_key_raises_error():
    config = TTSConfig(mode="api", provider="elevenlabs")

    with pytest.raises(ValueError, match="ElevenLabs API key is required"):
        ElevenLabsProvider(config)


def test_elevenlabs_provider_synthesize_returns_response(tmp_path: Path):
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.elevenlabs.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        with patch.object(provider, "_fetch_available_voices") as mock_fetch:
            mock_fetch.return_value = ["21m00Tcm4TlvDq8ikWAM"]

            output_path = tmp_path / "output.mp3"
            duration = provider.synthesize("Test text", output_path, "21m00Tcm4TlvDq8ikWAM")

            assert output_path.exists()
            assert output_path.read_bytes() == b"MOCK_AUDIO_DATA"
            assert duration > 0


def test_elevenlabs_provider_synthesize_with_different_voice(tmp_path: Path):
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.elevenlabs.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        with patch.object(provider, "_get_cached_audio", return_value=None):
            with patch.object(provider, "_fetch_available_voices") as mock_fetch:
                mock_fetch.return_value = ["21m00Tcm4TlvDq8ikWAM", "voice_id_2"]

                output_path = tmp_path / "output.mp3"
                duration = provider.synthesize("Test text", output_path, "voice_id_2")

                assert output_path.exists()
                assert duration > 0
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert "voice_id_2" in call_args[0][0]


def test_elevenlabs_provider_health_check_returns_true():
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200

    with patch("auto_video.providers.tts.elevenlabs.httpx.get") as mock_get:
        mock_get.return_value = mock_response

        result = provider.health_check()

        assert result is True


def test_elevenlabs_provider_health_check_returns_false_on_failure():
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)

    with patch("auto_video.providers.tts.elevenlabs.httpx.get") as mock_get:
        mock_get.side_effect = Exception("Network error")

        result = provider.health_check()

        assert result is False


def test_elevenlabs_provider_get_available_voices_returns_voice_list():
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "voices": [
            {"voice_id": "voice1", "name": "Voice 1"},
            {"voice_id": "voice2", "name": "Voice 2"},
        ]
    }

    with patch("auto_video.providers.tts.elevenlabs.httpx.get") as mock_get:
        mock_get.return_value = mock_response

        voices = provider.get_available_voices()

        assert isinstance(voices, list)
        assert len(voices) == 2
        assert "voice1" in voices
        assert "voice2" in voices


def test_elevenlabs_provider_caching_prevents_duplicate_api_calls(tmp_path: Path):
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.elevenlabs.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        with patch.object(provider, "_get_cached_audio", return_value=None) as mock_cache:
            with patch.object(provider, "_fetch_available_voices") as mock_fetch:
                mock_fetch.return_value = ["21m00Tcm4TlvDq8ikWAM"]

                output_path1 = tmp_path / "output1.mp3"
                output_path2 = tmp_path / "output2.mp3"

                provider.synthesize("Test text", output_path1, "21m00Tcm4TlvDq8ikWAM")

                mock_cache.return_value = b"CACHED_AUDIO_DATA"
                provider.synthesize("Test text", output_path2, "21m00Tcm4TlvDq8ikWAM")

                assert mock_post.call_count == 1


def test_elevenlabs_provider_retry_on_rate_limit(tmp_path: Path):
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)
    mock_response_429 = Mock()
    mock_response_429.status_code = 429
    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.elevenlabs.httpx.post") as mock_post:
        mock_post.side_effect = [
            httpx.HTTPStatusError("Rate limit", request=Mock(), response=mock_response_429),
            mock_response_200,
        ]

        with patch.object(provider, "_fetch_available_voices") as mock_fetch:
            mock_fetch.return_value = ["21m00Tcm4TlvDq8ikWAM"]

            output_path = tmp_path / "output.mp3"
            duration = provider.synthesize("Test text", output_path, "21m00Tcm4TlvDq8ikWAM")

            assert output_path.exists()
            assert duration > 0


def test_elevenlabs_provider_synthesize_with_invalid_voice_raises_error(tmp_path: Path):
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=Mock(), response=mock_response
    )

    with patch("auto_video.providers.tts.elevenlabs.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        with patch.object(provider, "_fetch_available_voices") as mock_fetch:
            mock_fetch.return_value = ["21m00Tcm4TlvDq8ikWAM"]

            with patch.object(provider, "_get_cached_audio", return_value=None):
                output_path = tmp_path / "output.mp3"

                with pytest.raises(ElevenLabsError):
                    provider.synthesize("Test text", output_path, "21m00Tcm4TlvDq8ikWAM")


def test_openai_tts_provider_initialization_with_valid_config():
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)

    assert provider.config == config
    assert provider._api_key == "test_key"
    assert provider._model == "tts-1"


def test_openai_tts_provider_initialization_with_custom_model():
    config = TTSConfig(mode="api", provider="openai", api_key="test_key", model="tts-1-hd")
    provider = OpenAITTSProvider(config)

    assert provider._model == "tts-1-hd"


def test_openai_tts_provider_initialization_without_api_key_raises_error():
    config = TTSConfig(mode="api", provider="openai")

    with pytest.raises(ValueError, match="OpenAI API key is required"):
        OpenAITTSProvider(config)


def test_openai_tts_provider_synthesize_returns_response(tmp_path: Path):
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.openai_tts.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        output_path = tmp_path / "output.mp3"
        duration = provider.synthesize("Test text", output_path, "alloy")

        assert output_path.exists()
        assert output_path.read_bytes() == b"MOCK_AUDIO_DATA"
        assert duration > 0


def test_openai_tts_provider_synthesize_with_different_model(tmp_path: Path):
    config = TTSConfig(mode="api", provider="openai", api_key="test_key", model="tts-1-hd")
    provider = OpenAITTSProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.openai_tts.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        with patch.object(provider, "_get_cached_audio", return_value=None):
            output_path = tmp_path / "output.mp3"
            provider.synthesize("Test text", output_path, "alloy")

            call_args = mock_post.call_args
            assert call_args[1]["json"]["model"] == "tts-1-hd"


def test_openai_tts_provider_synthesize_with_different_voice(tmp_path: Path):
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.openai_tts.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        with patch.object(provider, "_get_cached_audio", return_value=None):
            output_path = tmp_path / "output.mp3"
            provider.synthesize("Test text", output_path, "onyx")

            call_args = mock_post.call_args
            assert call_args[1]["json"]["voice"] == "onyx"


def test_openai_tts_provider_health_check_returns_true():
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200

    with patch("auto_video.providers.tts.openai_tts.httpx.get") as mock_get:
        mock_get.return_value = mock_response

        result = provider.health_check()

        assert result is True


def test_openai_tts_provider_health_check_returns_false_on_failure():
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)

    with patch("auto_video.providers.tts.openai_tts.httpx.get") as mock_get:
        mock_get.side_effect = Exception("Network error")

        result = provider.health_check()

        assert result is False


def test_openai_tts_provider_get_available_voices_returns_all_6_voices():
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)

    voices = provider.get_available_voices()

    assert len(voices) == 6
    assert "alloy" in voices
    assert "echo" in voices
    assert "fable" in voices
    assert "onyx" in voices
    assert "nova" in voices
    assert "shimmer" in voices


def test_openai_tts_provider_caching_prevents_duplicate_api_calls(tmp_path: Path):
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.openai_tts.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        with patch.object(provider, "_get_cached_audio", return_value=None) as mock_cache:
            output_path1 = tmp_path / "output1.mp3"
            output_path2 = tmp_path / "output2.mp3"

            provider.synthesize("Test text", output_path1, "alloy")

            mock_cache.return_value = b"CACHED_AUDIO_DATA"
            provider.synthesize("Test text", output_path2, "alloy")

            assert mock_post.call_count == 1


def test_openai_tts_provider_retry_on_rate_limit(tmp_path: Path):
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)
    mock_response_429 = Mock()
    mock_response_429.status_code = 429
    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.openai_tts.httpx.post") as mock_post:
        mock_post.side_effect = [
            httpx.HTTPStatusError("Rate limit", request=Mock(), response=mock_response_429),
            mock_response_200,
        ]

        output_path = tmp_path / "output.mp3"
        duration = provider.synthesize("Test text", output_path, "alloy")

        assert output_path.exists()
        assert duration > 0


def test_openai_tts_provider_duration_estimation():
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)

    text = "This is a test text with ten words here now"
    duration = provider._estimate_duration(text)

    assert duration > 0
    words = len(text.split())
    expected_duration = max(0.1, words / 2.5)
    assert duration == expected_duration


def test_openai_tts_provider_duration_estimation_minimum():
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)

    duration = provider._estimate_duration("")

    assert duration == 0.1


def test_openai_tts_provider_synthesize_with_invalid_voice_falls_back(tmp_path: Path):
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"MOCK_AUDIO_DATA"

    with patch("auto_video.providers.tts.openai_tts.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        with patch.object(provider, "_get_cached_audio", return_value=None):
            output_path = tmp_path / "output.mp3"
            provider.synthesize("Test text", output_path, "invalid_voice")

            call_args = mock_post.call_args
            assert call_args[1]["json"]["voice"] == "alloy"


def test_elevenlabs_provider_get_available_voices_returns_fallback_on_error():
    config = TTSConfig(mode="api", provider="elevenlabs", api_key="test_key")
    provider = ElevenLabsProvider(config)

    with patch("auto_video.providers.tts.elevenlabs.httpx.get") as mock_get:
        mock_get.side_effect = Exception("API error")

        voices = provider.get_available_voices()

        assert "21m00Tcm4TlvDq8ikWAM" in voices


def test_openai_tts_provider_synthesize_with_invalid_status_raises_error(tmp_path: Path):
    config = TTSConfig(mode="api", provider="openai", api_key="test_key")
    provider = OpenAITTSProvider(config)
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=Mock(), response=mock_response
    )

    with patch("auto_video.providers.tts.openai_tts.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        with patch.object(provider, "_get_cached_audio", return_value=None):
            output_path = tmp_path / "output.mp3"

            with pytest.raises(OpenAITTSError):
                provider.synthesize("Test text", output_path, "alloy")
