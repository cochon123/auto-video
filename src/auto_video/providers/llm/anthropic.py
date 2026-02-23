"""Anthropic LLM provider implementation."""

import hashlib
import json
import logging
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.provider_base import LLMProvider

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicAPIError(Exception):
    pass


class AnthropicRateLimitError(Exception):
    pass


class AnthropicProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._model = config.model
        self._api_key = config.api_key
        self._cache_dir = Path.home() / ".cache" / "auto-video" / "anthropic"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    def _get_cache_key(self, prompt: str, system_prompt: str | None = None) -> str:
        content = f"{self._model}:{prompt}:{system_prompt or ''}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> str | None:
        cache_path = self._cache_dir / f"{cache_key}.json"
        if cache_path.exists():
            logger.debug("Cache hit for key: %s", cache_key[:8])
            try:
                data = json.loads(cache_path.read_text())
                content = data.get("content")
                if isinstance(content, str):
                    return content
            except Exception:
                pass
        return None

    def _cache_response(self, cache_key: str, content: str) -> None:
        cache_path = self._cache_dir / f"{cache_key}.json"
        try:
            cache_path.write_text(json.dumps({"content": content}))
        except Exception as e:
            logger.warning("Failed to cache response: %s", str(e))

    def _get_headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ValueError("Anthropic API key is required")
        return {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _parse_error(self, status_code: int, response_data: dict[str, object]) -> None:
        if status_code == 429:
            raise AnthropicRateLimitError(f"Rate limit: {response_data}")
        raise AnthropicAPIError(f"API error {status_code}: {response_data}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(AnthropicRateLimitError),
        reraise=True,
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        cache_key = self._get_cache_key(prompt, system_prompt)
        cached_content = self._get_cached_response(cache_key)
        if cached_content is not None:
            logger.info("Using cached Anthropic response: model=%s", self._model)
            return cached_content

        logger.info("Anthropic API call: model=%s", self._model)

        payload: dict[str, object] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = self._http_client.post(
                ANTHROPIC_API_URL,
                headers=self._get_headers(),
                json=payload,
            )

            if response.status_code != 200:
                self._parse_error(response.status_code, response.json())

            data = response.json()
            content_blocks = data.get("content", [])
            if not content_blocks:
                raise AnthropicAPIError("Empty response from Anthropic")

            text_content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text_content += block.get("text", "")
            self._cache_response(cache_key, text_content)
            return text_content
        except AnthropicRateLimitError:
            logger.warning("Anthropic rate limit exceeded, retrying...")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Anthropic HTTP error: %s", str(e))
            raise AnthropicAPIError(str(e))
        except Exception as e:
            logger.error("Anthropic API error: %s", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(AnthropicRateLimitError),
        reraise=True,
    )
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]:
        cache_key = self._get_cache_key(prompt)
        cached_content = self._get_cached_response(cache_key)
        if cached_content is not None:
            logger.info("Using cached Anthropic response with tokens: model=%s", self._model)
            return cached_content, 0

        logger.info("Anthropic API call with token count: model=%s", self._model)

        payload: dict[str, object] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = self._http_client.post(
                ANTHROPIC_API_URL,
                headers=self._get_headers(),
                json=payload,
            )

            if response.status_code != 200:
                self._parse_error(response.status_code, response.json())

            data = response.json()
            content_blocks = data.get("content", [])
            if not content_blocks:
                raise AnthropicAPIError("Empty response from Anthropic")

            text_content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text_content += block.get("text", "")

            usage = data.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            self._cache_response(cache_key, text_content)
            return text_content, tokens
        except AnthropicRateLimitError:
            logger.warning("Anthropic rate limit exceeded, retrying...")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Anthropic HTTP error: %s", str(e))
            raise AnthropicAPIError(str(e))
        except Exception as e:
            logger.error("Anthropic API error: %s", str(e))
            raise

    def health_check(self) -> bool:
        try:
            response = self._http_client.get("https://status.anthropic.com/")
            return response.status_code == 200
        except Exception as e:
            logger.error("Anthropic health check failed: %s", str(e))
            return False

    def get_model_name(self) -> str:
        return f"anthropic/{self._model}"
