"""Groq LLM provider implementation."""

import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.provider_base import LLMProvider

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqAPIError(Exception):
    pass


class GroqRateLimitError(Exception):
    pass


class GroqProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._model = config.model
        self._api_key = config.api_key

    def _get_headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ValueError("Groq API key is required")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _parse_error(self, status_code: int, response_data: dict[str, object]) -> None:
        error_data = response_data.get("error", {})
        if isinstance(error_data, dict):
            error_msg = error_data.get("message", str(response_data))
        else:
            error_msg = str(response_data)
        if status_code == 429:
            raise GroqRateLimitError(f"Rate limit: {error_msg}")
        raise GroqAPIError(f"API error {status_code}: {error_msg}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(GroqRateLimitError),
        reraise=True,
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.info("Groq API call: model=%s", self._model)

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    GROQ_API_URL,
                    headers=self._get_headers(),
                    json=payload,
                )

                if response.status_code != 200:
                    self._parse_error(response.status_code, response.json())

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise GroqAPIError("Empty response from Groq")

                message = choices[0].get("message", {})
                content = message.get("content", "") if isinstance(message, dict) else ""
                if not isinstance(content, str) or not content:
                    raise GroqAPIError("Empty content in response")
                return content
        except GroqRateLimitError:
            logger.warning("Groq rate limit exceeded, retrying...")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Groq HTTP error: %s", str(e))
            raise GroqAPIError(str(e))
        except Exception as e:
            logger.error("Groq API error: %s", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(GroqRateLimitError),
        reraise=True,
    )
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]:
        messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]

        logger.info("Groq API call with token count: model=%s", self._model)

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    GROQ_API_URL,
                    headers=self._get_headers(),
                    json=payload,
                )

                if response.status_code != 200:
                    self._parse_error(response.status_code, response.json())

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise GroqAPIError("Empty response from Groq")

                message = choices[0].get("message", {})
                content = message.get("content", "") if isinstance(message, dict) else ""
                if not isinstance(content, str) or not content:
                    raise GroqAPIError("Empty content in response")

                usage = data.get("usage", {})
                tokens = usage.get("total_tokens", 0) if isinstance(usage, dict) else 0
                return content, tokens
        except GroqRateLimitError:
            logger.warning("Groq rate limit exceeded, retrying...")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Groq HTTP error: %s", str(e))
            raise GroqAPIError(str(e))
        except Exception as e:
            logger.error("Groq API error: %s", str(e))
            raise

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get("https://api.groq.com/openai/v1/models")
                return response.status_code == 200
        except Exception as e:
            logger.error("Groq health check failed: %s", str(e))
            return False

    def get_model_name(self) -> str:
        return f"groq/{self._model}"
