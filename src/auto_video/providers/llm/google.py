"""Google (Gemini) LLM provider implementation."""

import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.provider_base import LLMProvider

logger = logging.getLogger(__name__)

GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GoogleAPIError(Exception):
    pass


class GoogleRateLimitError(Exception):
    pass


class GoogleProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._model = config.model
        self._api_key = config.api_key

    def _get_api_key(self) -> str:
        if not self._api_key:
            raise ValueError("Google API key is required")
        return self._api_key

    def _parse_error(self, status_code: int, response_data: dict[str, object]) -> None:
        error_data = response_data.get("error", {})
        if isinstance(error_data, dict):
            error_msg = error_data.get("message", str(response_data))
        else:
            error_msg = str(response_data)
        if status_code == 429:
            raise GoogleRateLimitError(f"Rate limit: {error_msg}")
        raise GoogleAPIError(f"API error {status_code}: {error_msg}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(GoogleRateLimitError),
        reraise=True,
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        logger.info("Google API call: model=%s", self._model)

        url = f"{GOOGLE_API_BASE}/{self._model}:generateContent"
        params = {"key": self._get_api_key()}

        contents: list[dict[str, object]] = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append({"role": "model", "parts": [{"text": "I understand."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": self.config.temperature},
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, params=params, json=payload)

                if response.status_code != 200:
                    self._parse_error(response.status_code, response.json())

                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise GoogleAPIError("Empty response from Google")

                parts = candidates[0].get("content", {}).get("parts", [])
                text_content = ""
                for part in parts:
                    if "text" in part:
                        text_content += part["text"]

                if not text_content:
                    raise GoogleAPIError("Empty content in response")
                return text_content
        except GoogleRateLimitError:
            logger.warning("Google rate limit exceeded, retrying...")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Google HTTP error: %s", str(e))
            raise GoogleAPIError(str(e))
        except Exception as e:
            logger.error("Google API error: %s", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(GoogleRateLimitError),
        reraise=True,
    )
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]:
        logger.info("Google API call with token count: model=%s", self._model)

        url = f"{GOOGLE_API_BASE}/{self._model}:generateContent"
        params = {"key": self._get_api_key()}

        contents: list[dict[str, object]] = [{"role": "user", "parts": [{"text": prompt}]}]

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": self.config.temperature},
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, params=params, json=payload)

                if response.status_code != 200:
                    self._parse_error(response.status_code, response.json())

                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise GoogleAPIError("Empty response from Google")

                parts = candidates[0].get("content", {}).get("parts", [])
                text_content = ""
                for part in parts:
                    if "text" in part:
                        text_content += part["text"]

                if not text_content:
                    raise GoogleAPIError("Empty content in response")

                usage = data.get("usageMetadata", {})
                tokens = usage.get("totalTokenCount", 0)
                return text_content, tokens
        except GoogleRateLimitError:
            logger.warning("Google rate limit exceeded, retrying...")
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Google HTTP error: %s", str(e))
            raise GoogleAPIError(str(e))
        except Exception as e:
            logger.error("Google API error: %s", str(e))
            raise

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=10.0) as client:
                url = f"{GOOGLE_API_BASE}?key={self._get_api_key()}"
                response = client.get(url)
                return response.status_code == 200
        except Exception as e:
            logger.error("Google health check failed: %s", str(e))
            return False

    def get_model_name(self) -> str:
        return f"google/{self._model}"
