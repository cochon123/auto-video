"""OpenRouter LLM provider implementation."""

import hashlib
import json
import logging
from pathlib import Path

import httpx
from openai import APIError, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.provider_base import LLMProvider

logger = logging.getLogger(__name__)


class OpenRouterResponseError(Exception):
    pass


class OpenRouterProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._client: httpx.Client | None = None
        self._model = config.model
        self._cache_dir = Path.home() / ".cache" / "auto-video" / "openrouter"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    def _get_cache_key(self, prompt: str, system_prompt: str | None = None) -> str:
        content = f"{self._model}:{self.config.temperature}:{prompt}:{system_prompt or ''}"
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

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            api_key = self.config.api_key
            if not api_key:
                raise ValueError("OpenRouter API key is required")

            headers = {
                "HTTP-Referer": "https://github.com/made2591/auto-video",
                "X-Title": "Auto-Video",
                "Authorization": f"Bearer {api_key}",
            }

            if self.config.host:
                headers["OpenAI-Base-URL"] = self.config.host

            self._client = httpx.Client(
                headers=headers,
                timeout=httpx.Timeout(60.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        cache_key = self._get_cache_key(prompt, system_prompt)
        cached_content = self._get_cached_response(cache_key)
        if cached_content is not None:
            logger.info("Using cached OpenRouter response: model=%s", self._model)
            return cached_content

        messages: list[ChatCompletionMessageParam] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.info("OpenRouter API call: model=%s", self._model)

        try:
            response = self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                },
            )

            if response.status_code != 200:
                logger.error("OpenRouter API error: HTTP %d - %s", response.status_code, response.text)
                raise OpenRouterResponseError(f"HTTP {response.status_code}: {response.text}")

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")

            if content is None:
                raise OpenRouterResponseError("Empty response from OpenRouter")

            self._cache_response(cache_key, content)
            return content
        except RateLimitError:
            logger.warning("OpenRouter rate limit exceeded, retrying...")
            raise
        except Exception as e:
            logger.error("OpenRouter API error: %s", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]:
        cache_key = self._get_cache_key(prompt)
        cached_content = self._get_cached_response(cache_key)
        if cached_content is not None:
            logger.info("Using cached OpenRouter response with tokens: model=%s", self._model)
            return cached_content, 0

        messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": prompt}]

        logger.info("OpenRouter API call with token count: model=%s", self._model)

        try:
            response = self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                },
            )

            if response.status_code != 200:
                logger.error("OpenRouter API error: HTTP %d - %s", response.status_code, response.text)
                raise OpenRouterResponseError(f"HTTP {response.status_code}: {response.text}")

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            usage = data.get("usage", {})

            if content is None:
                raise OpenRouterResponseError("Empty response from OpenRouter")

            tokens = usage.get("total_tokens", 0)
            self._cache_response(cache_key, content)
            return content, tokens
        except RateLimitError:
            logger.warning("OpenRouter rate limit exceeded, retrying...")
            raise
        except Exception as e:
            logger.error("OpenRouter API error: %s", str(e))
            raise

    def health_check(self) -> bool:
        try:
            response = self._http_client.get("https://openrouter.ai/api/v1/health")
            return response.status_code == 200
        except Exception as e:
            logger.error("OpenRouter health check failed: %s", str(e))
            return False

    def get_model_name(self) -> str:
        return f"openrouter/{self._model}"