"""Ollama LLM provider implementation."""

import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.provider_base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaConnectionError(Exception):
    pass


class OllamaResponseError(Exception):
    pass


class OllamaProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config
        self._base_url = (config.host or "http://localhost:11434").rstrip("/")
        self._model = config.model
        self._timeout = 120.0
        self._use_openai_compatible = True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.ConnectError),
        reraise=True,
    )
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.info("Ollama API call: model=%s", self._model)

        if self._use_openai_compatible:
            payload = {
                "model": self._model,
                "messages": messages,
                "temperature": self.config.temperature,
            }
            endpoint = f"{self._base_url}/v1/chat/completions"
        else:
            payload = {
                "model": self._model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                },
            }
            endpoint = f"{self._base_url}/api/chat"

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()

            if self._use_openai_compatible:
                choices = data.get("choices", [])
                if not choices:
                    raise OllamaResponseError("Empty response from Ollama")
                content = str(choices[0].get("message", {}).get("content", ""))
            else:
                if "message" not in data:
                    raise OllamaResponseError("Invalid response from Ollama")
                content = str(data["message"].get("content", ""))

            if not content:
                raise OllamaResponseError("Empty response from Ollama")
            return content
        except httpx.ConnectError as e:
            logger.error("Ollama connection error: %s", str(e))
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self._base_url}") from e
        except httpx.HTTPStatusError as e:
            logger.error("Ollama HTTP error: %s", str(e))
            raise
        except Exception as e:
            logger.error("Ollama API error: %s", str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.ConnectError),
        reraise=True,
    )
    def generate_with_tokens(self, prompt: str) -> tuple[str, int]:
        messages = [{"role": "user", "content": prompt}]

        logger.info("Ollama API call with token count: model=%s", self._model)

        if self._use_openai_compatible:
            payload = {
                "model": self._model,
                "messages": messages,
                "temperature": self.config.temperature,
            }
            endpoint = f"{self._base_url}/v1/chat/completions"
        else:
            payload = {
                "model": self._model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                },
            }
            endpoint = f"{self._base_url}/api/chat"

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()

            if self._use_openai_compatible:
                choices = data.get("choices", [])
                if not choices:
                    raise OllamaResponseError("Empty response from Ollama")
                content = str(choices[0].get("message", {}).get("content", ""))
                usage = data.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
            else:
                if "message" not in data:
                    raise OllamaResponseError("Invalid response from Ollama")
                content = str(data["message"].get("content", ""))
                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)
                total_tokens = prompt_tokens + completion_tokens

            if not content:
                raise OllamaResponseError("Empty response from Ollama")

            return content, total_tokens
        except httpx.ConnectError as e:
            logger.error("Ollama connection error: %s", str(e))
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self._base_url}") from e
        except httpx.HTTPStatusError as e:
            logger.error("Ollama HTTP error: %s", str(e))
            raise
        except Exception as e:
            logger.error("Ollama API error: %s", str(e))
            raise

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self._base_url}/api/tags")
                if response.status_code != 200:
                    return False

                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]

                if self._model not in model_names and not any(
                    name.startswith(self._model) for name in model_names
                ):
                    logger.warning(
                        "Model '%s' not found in Ollama. Available: %s",
                        self._model,
                        model_names,
                    )
                    return False

                return True
        except Exception as e:
            logger.error("Ollama health check failed: %s", str(e))
            return False

    def get_model_name(self) -> str:
        return f"ollama/{self._model}"

    def unload_model(self) -> None:
        """Unload model from GPU memory to free VRAM."""
        try:
            endpoint = f"{self._base_url}/api/generate"
            payload = {
                "model": self._model,
                "prompt": "",
                "keep_alive": 0,  # Unload immediately
                "stream": False,
                "options": {
                    "num_keep": 0,  # Don't keep any tokens
                    "num_ctx": 0,  # Minimal context
                },
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()

            logger.info(f"Ollama model unloaded from GPU: {self._model}")
        except httpx.ConnectError as e:
            logger.warning(f"Failed to unload Ollama model (connection error): {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"Failed to unload Ollama model (HTTP {e.response.status_code}): {str(e)}"
            )
        except Exception as e:
            logger.warning(f"Failed to unload Ollama model: {str(e)}")
