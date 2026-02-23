"""Test LLM API providers."""

from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from openai import APIError

from auto_video.config.schema import LLMProviderConfig
from auto_video.providers.llm.anthropic import (
    AnthropicAPIError,
    AnthropicProvider,
    AnthropicRateLimitError,
)
from auto_video.providers.llm.google import (
    GoogleAPIError,
    GoogleProvider,
    GoogleRateLimitError,
)
from auto_video.providers.llm.groq import GroqAPIError, GroqProvider, GroqRateLimitError
from auto_video.providers.llm.openai import OpenAIProvider, OpenAIResponseError


@pytest.fixture
def openai_config() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="openai",
        model="gpt-4",
        api_key="test-api-key",
        temperature=0.7,
    )


@pytest.fixture
def anthropic_config() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="anthropic",
        model="claude-3-opus-20240229",
        api_key="test-api-key",
        temperature=0.7,
    )


@pytest.fixture
def groq_config() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="groq",
        model="llama2-70b-4096",
        api_key="test-api-key",
        temperature=0.7,
    )


@pytest.fixture
def google_config() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="google",
        model="gemini-pro",
        api_key="test-api-key",
        temperature=0.7,
    )


class TestOpenAIProvider:
    def test_init_with_valid_config(self, openai_config: LLMProviderConfig) -> None:
        provider = OpenAIProvider(openai_config)

        assert provider.config == openai_config
        assert provider._model == "gpt-4"
        assert provider._client is None

    def test_generate_returns_response(self, openai_config: LLMProviderConfig) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response text"

        with patch("auto_video.providers.llm.openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(openai_config)
            result = provider.generate("Test prompt")

        assert result == "Generated response text"

    def test_generate_with_system_prompt(self, openai_config: LLMProviderConfig) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response with system"

        with patch("auto_video.providers.llm.openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(openai_config)
            result = provider.generate("User prompt", system_prompt="System prompt")

        assert result == "Response with system"

    def test_generate_with_tokens_returns_response_and_count(
        self, openai_config: LLMProviderConfig
    ) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Token response"
        mock_response.usage.total_tokens = 150

        with patch("auto_video.providers.llm.openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(openai_config)
            result, tokens = provider.generate_with_tokens("Test prompt")

        assert result == "Token response"
        assert tokens == 150

    def test_health_check_returns_true_on_success(self, openai_config: LLMProviderConfig) -> None:
        provider = OpenAIProvider(openai_config)
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.health_check()

        assert result is True

    def test_health_check_returns_false_on_failure(self, openai_config: LLMProviderConfig) -> None:
        provider = OpenAIProvider(openai_config)

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.side_effect = httpx.RequestError("Connection failed")
            mock_client_class.return_value = mock_client

            result = provider.health_check()

        assert result is False

    def test_get_model_name_returns_correct_name(self, openai_config: LLMProviderConfig) -> None:
        provider = OpenAIProvider(openai_config)

        result = provider.get_model_name()

        assert result == "openai/gpt-4"

    def test_generate_raises_on_empty_response(self, openai_config: LLMProviderConfig) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        with patch("auto_video.providers.llm.openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(openai_config)
            with pytest.raises(OpenAIResponseError):
                provider.generate("Test prompt")


class TestAnthropicProvider:
    def test_init_with_valid_config(self, anthropic_config: LLMProviderConfig) -> None:
        provider = AnthropicProvider(anthropic_config)

        assert provider.config == anthropic_config
        assert provider._model == "claude-3-opus-20240229"

    def test_generate_with_api_response(self, anthropic_config: LLMProviderConfig) -> None:
        provider = AnthropicProvider(anthropic_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Anthropic response"}]
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.generate("Test prompt")

        assert result == "Anthropic response"

    def test_generate_with_system_prompt(self, anthropic_config: LLMProviderConfig) -> None:
        provider = AnthropicProvider(anthropic_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Response with system"}]
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.generate("User prompt", system_prompt="System prompt")

        assert result == "Response with system"

    def test_generate_with_tokens_works(self, anthropic_config: LLMProviderConfig) -> None:
        provider = AnthropicProvider(anthropic_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Token response"}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result, tokens = provider.generate_with_tokens("Test prompt")

        assert result == "Token response"
        assert tokens == 150

    def test_health_check_works(self, anthropic_config: LLMProviderConfig) -> None:
        provider = AnthropicProvider(anthropic_config)
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.health_check()

        assert result is True

    def test_get_model_name_returns_correct_name(self, anthropic_config: LLMProviderConfig) -> None:
        provider = AnthropicProvider(anthropic_config)

        result = provider.get_model_name()

        assert result == "anthropic/claude-3-opus-20240229"


class TestGroqProvider:
    def test_init_with_valid_config(self, groq_config: LLMProviderConfig) -> None:
        provider = GroqProvider(groq_config)

        assert provider.config == groq_config
        assert provider._model == "llama2-70b-4096"

    def test_generate_works(self, groq_config: LLMProviderConfig) -> None:
        provider = GroqProvider(groq_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "Groq response"}}]}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.generate("Test prompt")

        assert result == "Groq response"

    def test_generate_with_system_prompt(self, groq_config: LLMProviderConfig) -> None:
        provider = GroqProvider(groq_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response with system"}}]
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.generate("User prompt", system_prompt="System prompt")

        assert result == "Response with system"

    def test_generate_with_tokens_works(self, groq_config: LLMProviderConfig) -> None:
        provider = GroqProvider(groq_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Token response"}}],
            "usage": {"total_tokens": 200},
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result, tokens = provider.generate_with_tokens("Test prompt")

        assert result == "Token response"
        assert tokens == 200

    def test_health_check_works(self, groq_config: LLMProviderConfig) -> None:
        provider = GroqProvider(groq_config)
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.health_check()

        assert result is True

    def test_get_model_name_returns_correct_name(self, groq_config: LLMProviderConfig) -> None:
        provider = GroqProvider(groq_config)

        result = provider.get_model_name()

        assert result == "groq/llama2-70b-4096"


class TestGoogleProvider:
    def test_init_with_valid_config(self, google_config: LLMProviderConfig) -> None:
        provider = GoogleProvider(google_config)

        assert provider.config == google_config
        assert provider._model == "gemini-pro"

    def test_generate_works(self, google_config: LLMProviderConfig) -> None:
        provider = GoogleProvider(google_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Google response"}]}}]
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.generate("Test prompt")

        assert result == "Google response"

    def test_generate_with_system_prompt(self, google_config: LLMProviderConfig) -> None:
        provider = GoogleProvider(google_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Response with system"}]}}]
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.generate("User prompt", system_prompt="System prompt")

        assert result == "Response with system"

    def test_generate_with_tokens_works(self, google_config: LLMProviderConfig) -> None:
        provider = GoogleProvider(google_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Token response"}]}}],
            "usageMetadata": {"totalTokenCount": 250},
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result, tokens = provider.generate_with_tokens("Test prompt")

        assert result == "Token response"
        assert tokens == 250

    def test_health_check_works(self, google_config: LLMProviderConfig) -> None:
        provider = GoogleProvider(google_config)
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = provider.health_check()

        assert result is True

    def test_get_model_name_returns_correct_name(self, google_config: LLMProviderConfig) -> None:
        provider = GoogleProvider(google_config)

        result = provider.get_model_name()

        assert result == "google/gemini-pro"


class TestErrorHandling:
    def test_openai_api_error(self, openai_config: LLMProviderConfig) -> None:
        mock_request = MagicMock()
        mock_request.url = "https://api.openai.com/v1/chat/completions"

        with patch("auto_video.providers.llm.openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = APIError(
                message="API error",
                request=mock_request,
                body=None,
            )
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(openai_config)
            with pytest.raises(APIError):
                provider.generate("Test prompt")

    def test_anthropic_rate_limit_error(self, anthropic_config: LLMProviderConfig) -> None:
        provider = AnthropicProvider(anthropic_config)
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(AnthropicRateLimitError):
                provider.generate("Test prompt")

    def test_anthropic_api_error(self, anthropic_config: LLMProviderConfig) -> None:
        provider = AnthropicProvider(anthropic_config)
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(AnthropicAPIError):
                provider.generate("Test prompt")

    def test_groq_rate_limit_error(self, groq_config: LLMProviderConfig) -> None:
        provider = GroqProvider(groq_config)
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(GroqRateLimitError):
                provider.generate("Test prompt")

    def test_groq_api_error(self, groq_config: LLMProviderConfig) -> None:
        provider = GroqProvider(groq_config)
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal error"}}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(GroqAPIError):
                provider.generate("Test prompt")

    def test_google_rate_limit_error(self, google_config: LLMProviderConfig) -> None:
        provider = GoogleProvider(google_config)
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(GoogleRateLimitError):
                provider.generate("Test prompt")

    def test_google_api_error(self, google_config: LLMProviderConfig) -> None:
        provider = GoogleProvider(google_config)
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal error"}}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(GoogleAPIError):
                provider.generate("Test prompt")

    def test_groq_empty_response_error(self, groq_config: LLMProviderConfig) -> None:
        provider = GroqProvider(groq_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(GroqAPIError):
                provider.generate("Test prompt")

    def test_google_empty_response_error(self, google_config: LLMProviderConfig) -> None:
        provider = GoogleProvider(google_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"candidates": []}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(GoogleAPIError):
                provider.generate("Test prompt")

    def test_anthropic_empty_response_error(self, anthropic_config: LLMProviderConfig) -> None:
        provider = AnthropicProvider(anthropic_config)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": []}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(AnthropicAPIError):
                provider.generate("Test prompt")

    def test_openai_missing_api_key(self) -> None:
        config = LLMProviderConfig(
            provider="openai",
            model="gpt-4",
            api_key=None,
        )
        provider = OpenAIProvider(config)

        with pytest.raises(ValueError, match="OpenAI API key is required"):
            _ = provider.client

    def test_anthropic_missing_api_key(self) -> None:
        config = LLMProviderConfig(
            provider="anthropic",
            model="claude-3-opus-20240229",
            api_key=None,
        )
        provider = AnthropicProvider(config)

        with pytest.raises(ValueError, match="Anthropic API key is required"):
            provider.generate("Test prompt")

    def test_groq_missing_api_key(self) -> None:
        config = LLMProviderConfig(
            provider="groq",
            model="llama2-70b-4096",
            api_key=None,
        )
        provider = GroqProvider(config)

        with pytest.raises(ValueError, match="Groq API key is required"):
            provider.generate("Test prompt")

    def test_google_missing_api_key(self) -> None:
        config = LLMProviderConfig(
            provider="google",
            model="gemini-pro",
            api_key=None,
        )
        provider = GoogleProvider(config)

        with pytest.raises(ValueError, match="Google API key is required"):
            provider.generate("Test prompt")
