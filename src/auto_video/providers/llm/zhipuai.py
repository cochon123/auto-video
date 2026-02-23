"""Zhipu AI (z.ai) LLM provider implementation."""

import hashlib
import json
import logging
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.provider_base import LLMProvider

logger = logging.getLogger(__name__)

ZHIPU_API_BASE = "https://open.bigmodel.cn/api/paas/v4"


class ZhipuAIError(Exception):
    pass


class ZhipuAIRateLimitError(Exception):
    pass


class ZhipuAIProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._model = config.model
        self._api_key = config.api_key
        self._cache_dir = Path.home() / ".cache" / "auto-video" / "zhipuai"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    def _get_api_key(self) -> str:
        if not self._api_key:
            raise ValueError("Zhipu AI API key is required")
        return self._api_key

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

    def _parse_error(self, status_code: int, response_data: dict[str, object]) -> None:
        error_data = response_data.get("error", {})
        if isinstance(error_data, dict):
            error_msg = error_data.get("message", str(response_data))
        else:
            error_msg = str(response_data)
        if status_code == 429:
            raise ZhipuAIRateLimitError(f"Rate limit: {error_msg}")
        raise ZhipuAIError(f"API error {status_code}: {error_msg}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ZhipuAIRateLimitError),
        reraise=True,
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        cache_key = self._get_cache_key(prompt, system_prompt)
        cached_content = self._get_cached_response(cache_key)
        if cached_content is not None:
            logger.info("Using cached Zhipu AI response: model=%s", self._model)
            return cached_content

        url = f"{ZHIPU_API_BASE}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        logger.info("Zhipu AI API call: model=%s", self._model)

        try:
            response = self._http_client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                self._parse_error(response.status_code, response.json())

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise ZhipuAIError("Empty response from Zhipu AI")

            content = str(choices[0].get("message", {}).get("content", ""))
            if not content:
                raise ZhipuAIError("Empty content in response")

            self._cache_response(cache_key, content)
            return content
        except ZhipuAIRateLimitError:
            logger.warning("Zhipu AI rate limit exceeded, retrying...")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Zhipu AI HTTP error: %s", str(e))
            raise ZhipuAIError(str(e))
        except Exception as e:
            logger.error("Zhipu AI API error: %s", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ZhipuAIRateLimitError),
        reraise=True,
    )
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]:
        cache_key = self._get_cache_key(prompt)
        cached_content = self._get_cached_response(cache_key)
        if cached_content is not None:
            logger.info("Using cached Zhipu AI response with tokens: model=%s", self._model)
            return cached_content, 0

        url = f"{ZHIPU_API_BASE}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }

        messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        logger.info("Zhipu AI API call with token count: model=%s", self._model)

        try:
            response = self._http_client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                self._parse_error(response.status_code, response.json())

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise ZhipuAIError("Empty response from Zhipu AI")

            content = str(choices[0].get("message", {}).get("content", ""))
            if not content:
                raise ZhipuAIError("Empty content in response")

            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)

            self._cache_response(cache_key, content)
            return content, tokens
        except ZhipuAIRateLimitError:
            logger.warning("Zhipu AI rate limit exceeded, retrying...")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Zhipu AI HTTP error: %s", str(e))
            raise ZhipuAIError(str(e))
        except Exception as e:
            logger.error("Zhipu AI API error: %s", str(e))
            raise

    def health_check(self) -> bool:
        try:
            url = f"{ZHIPU_API_BASE}/models"
            headers = {"Authorization": f"Bearer {self._get_api_key()}"}
            response = self._http_client.get(url, headers=headers)
            return response.status_code == 200
        except Exception as e:
            logger.error("Zhipu AI health check failed: %s", str(e))
            return False

    def get_model_name(self) -> str:
        return f"zhipuai/{self._model}"
