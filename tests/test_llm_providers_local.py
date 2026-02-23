"""Test LLM local providers."""

from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from auto_video.config.schema import LLMProviderConfig
from auto_video.providers.llm.llamacpp import (
    LlamaCppConnectionError,
    LlamaCppProvider,
    LlamaCppResponseError,
)
from auto_video.providers.llm.ollama import (
    OllamaConnectionError,
    OllamaProvider,
    OllamaResponseError,
)


@pytest.fixture
def ollama_config() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="ollama",
        model="llama2",
        api_key=None,
        temperature=0.7,
    )


@pytest.fixture
def ollama_config_custom_host() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="ollama",
        model="llama2",
        api_key=None,
        temperature=0.7,
        host="http://custom-host:11434",
    )


@pytest.fixture
def llamacpp_config() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="llamacpp",
        model="mistral-7b",
        api_key=None,
        temperature=0.7,
    )


@pytest.fixture
def llamacpp_config_custom_host() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="llamacpp",
        model="mistral-7b",
        api_key=None,
        temperature=0.7,
        host="http://custom-host:8080",
    )


class TestOllamaProvider:
    def test_init_with_default_host(self, ollama_config: LLMProviderConfig) -> None:
        provider = OllamaProvider(ollama_config)

        assert provider.config == ollama_config
        assert provider._base_url == "http://localhost:11434"
        assert provider._model == "llama2"

    def test_init_with_custom_host(self, ollama_config_custom_host: LLMProviderConfig) -> None:
        provider = OllamaProvider(ollama_config_custom_host)

        assert provider._base_url == "http://custom-host:11434"

    def test_generate_returns_response(self, ollama_config: LLMProviderConfig) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Ollama generated response"}}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(ollama_config)
            result = provider.generate("Test prompt")

        assert result == "Ollama generated response"

    def test_generate_with_system_prompt(self, ollama_config: LLMProviderConfig) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Response with system prompt"}}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(ollama_config)
            result = provider.generate("User prompt", system_prompt="System prompt")

        assert result == "Response with system prompt"

    def test_generate_with_tokens_returns_response_and_count(
        self, ollama_config: LLMProviderConfig
    ) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Token response"},
            "prompt_eval_count": 50,
            "eval_count": 100,
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(ollama_config)
            result, tokens = provider.generate_with_tokens("Test prompt")

        assert result == "Token response"
        assert tokens == 150

    def test_health_check_returns_true_when_server_and_model_available(
        self, ollama_config: LLMProviderConfig
    ) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama2"}, {"name": "mistral"}]}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(ollama_config)
            result = provider.health_check()

        assert result is True

    def test_health_check_returns_false_when_server_not_reachable(
        self, ollama_config: LLMProviderConfig
    ) -> None:
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(ollama_config)
            result = provider.health_check()

        assert result is False

    def test_health_check_returns_false_when_model_not_found(
        self, ollama_config: LLMProviderConfig
    ) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "mistral"}, {"name": "codellama"}]}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(ollama_config)
            result = provider.health_check()

        assert result is False

    def test_get_model_name_returns_correct_name(self, ollama_config: LLMProviderConfig) -> None:
        provider = OllamaProvider(ollama_config)

        result = provider.get_model_name()

        assert result == "ollama/llama2"

    def test_connection_error_handling(self, ollama_config: LLMProviderConfig) -> None:
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(ollama_config)
            with pytest.raises(OllamaConnectionError):
                provider.generate("Test prompt")

    def test_invalid_response_raises_error(self, ollama_config: LLMProviderConfig) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid_key": "no message field"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(ollama_config)
            with pytest.raises(OllamaResponseError):
                provider.generate("Test prompt")

    def test_empty_response_raises_error(self, ollama_config: LLMProviderConfig) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": ""}}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(ollama_config)
            with pytest.raises(OllamaResponseError):
                provider.generate("Test prompt")


class TestLlamaCppProvider:
    def test_init_with_default_host(self, llamacpp_config: LLMProviderConfig) -> None:
        provider = LlamaCppProvider(llamacpp_config)

        assert provider.config == llamacpp_config
        assert provider._base_url == "http://localhost:8080"
        assert provider._model == "mistral-7b"

    def test_init_with_custom_host(self, llamacpp_config_custom_host: LLMProviderConfig) -> None:
        provider = LlamaCppProvider(llamacpp_config_custom_host)

        assert provider._base_url == "http://custom-host:8080"

    def test_generate_returns_response(self, llamacpp_config: LLMProviderConfig) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": "Llama.cpp generated response"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = LlamaCppProvider(llamacpp_config)
            result = provider.generate("Test prompt")

        assert result == "Llama.cpp generated response"

    def test_generate_with_system_prompt(self, llamacpp_config: LLMProviderConfig) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": "Response with system"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = LlamaCppProvider(llamacpp_config)
            result = provider.generate("User prompt", system_prompt="System prompt")

        assert result == "Response with system"

    def test_generate_with_tokens_works(self, llamacpp_config: LLMProviderConfig) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "Token response",
            "tokens_evaluated": 30,
            "tokens_generated": 70,
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = LlamaCppProvider(llamacpp_config)
            result, tokens = provider.generate_with_tokens("Test prompt")

        assert result == "Token response"
        assert tokens == 100

    def test_health_check_returns_true_on_success(self, llamacpp_config: LLMProviderConfig) -> None:
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = LlamaCppProvider(llamacpp_config)
            result = provider.health_check()

        assert result is True

    def test_health_check_returns_false_on_failure(
        self, llamacpp_config: LLMProviderConfig
    ) -> None:
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            provider = LlamaCppProvider(llamacpp_config)
            result = provider.health_check()

        assert result is False

    def test_get_model_name_returns_correct_name(self, llamacpp_config: LLMProviderConfig) -> None:
        provider = LlamaCppProvider(llamacpp_config)

        result = provider.get_model_name()

        assert result == "llamacpp/mistral-7b"

    def test_connection_error_handling(self, llamacpp_config: LLMProviderConfig) -> None:
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            provider = LlamaCppProvider(llamacpp_config)
            with pytest.raises(LlamaCppConnectionError):
                provider.generate("Test prompt")

    def test_empty_response_raises_error(self, llamacpp_config: LLMProviderConfig) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": ""}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = LlamaCppProvider(llamacpp_config)
            with pytest.raises(LlamaCppResponseError):
                provider.generate("Test prompt")

    def test_health_check_returns_false_on_non_200_status(
        self, llamacpp_config: LLMProviderConfig
    ) -> None:
        mock_response = Mock()
        mock_response.status_code = 500

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = LlamaCppProvider(llamacpp_config)
            result = provider.health_check()

        assert result is False
