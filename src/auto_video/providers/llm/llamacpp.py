"""Llama.cpp LLM provider implementation."""

import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.provider_base import LLMProvider

logger = logging.getLogger(__name__)


class LlamaCppNotImplementedError(Exception):
    pass


class LlamaCppConnectionError(Exception):
    pass


class LlamaCppResponseError(Exception):
    pass


class LlamaCppProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._base_url = config.host or "http://localhost:8080"
        self._model = config.model
        self._timeout = 120.0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.ConnectError),
        reraise=True,
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        logger.info("Llama.cpp API call: model=%s", self._model)

        payload = {
            "prompt": full_prompt,
            "n_predict": 512,
            "temperature": self.config.temperature,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/completion",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            content: str = data.get("content", "")
            if not content:
                raise LlamaCppResponseError("Empty response from Llama.cpp")
            return content
        except httpx.ConnectError as e:
            logger.error("Llama.cpp connection error: %s", str(e))
            raise LlamaCppConnectionError(
                f"Cannot connect to Llama.cpp server at {self._base_url}"
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error("Llama.cpp HTTP error: %s", str(e))
            raise
        except Exception as e:
            logger.error("Llama.cpp API error: %s", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.ConnectError),
        reraise=True,
    )
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]:
        logger.info("Llama.cpp API call with token count: model=%s", self._model)

        payload = {
            "prompt": prompt,
            "n_predict": 512,
            "temperature": self.config.temperature,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/completion",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            content: str = data.get("content", "")
            if not content:
                raise LlamaCppResponseError("Empty response from Llama.cpp")

            tokens_evaluated = data.get("tokens_evaluated", 0)
            tokens_generated = data.get("tokens_generated", 0)
            total_tokens = tokens_evaluated + tokens_generated

            return content, total_tokens
        except httpx.ConnectError as e:
            logger.error("Llama.cpp connection error: %s", str(e))
            raise LlamaCppConnectionError(
                f"Cannot connect to Llama.cpp server at {self._base_url}"
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error("Llama.cpp HTTP error: %s", str(e))
            raise
        except Exception as e:
            logger.error("Llama.cpp API error: %s", str(e))
            raise

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self._base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error("Llama.cpp health check failed: %s", str(e))
            return False

    def get_model_name(self) -> str:
        return f"llamacpp/{self._model}"

    def unload_model(self) -> None:
        """Unload model from GPU memory to free VRAM."""
        try:
            # Llama.cpp server doesn't have a direct unload endpoint,
            # but we can try to send a completion with minimal context
            endpoint = f"{self._base_url}/completion"
            payload = {
                "prompt": "",
                "n_predict": 0,
                "stream": False,
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()

            logger.info(f"Llama.cpp model context cleared: {self._model}")
        except httpx.ConnectError as e:
            logger.warning(f"Failed to clear Llama.cpp model context (connection error): {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"Failed to clear Llama.cpp model context (HTTP {e.response.status_code}): {str(e)}"
            )
        except Exception as e:
            logger.warning(f"Failed to clear Llama.cpp model context: {str(e)}")
