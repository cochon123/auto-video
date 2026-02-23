"""OpenAI TTS provider implementation."""

import hashlib
import logging
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.config.schema import TTSConfig
from auto_video.core.tts import TTSProvider

logger = logging.getLogger(__name__)


class OpenAITTSError(Exception):
    pass


class OpenAITTSProvider(TTSProvider):
    def __init__(self, config: TTSConfig) -> None:
        self.config = config
        self._api_key = config.api_key
        if not self._api_key:
            raise ValueError("OpenAI API key is required")
        self._cache_dir = Path.home() / ".cache" / "auto-video" / "openai_tts"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._model = config.model or "tts-1"
        self._available_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    def _get_cache_key(self, text: str, voice: str) -> str:
        content = f"{text}:{voice}:{self._model}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cached_audio(self, cache_key: str) -> bytes | None:
        cache_path = self._cache_dir / f"{cache_key}.mp3"
        if cache_path.exists():
            logger.debug("Cache hit for key: %s", cache_key[:8])
            return cache_path.read_bytes()
        return None

    def _cache_audio(self, cache_key: str, audio_data: bytes) -> None:
        cache_path = self._cache_dir / f"{cache_key}.mp3"
        cache_path.write_bytes(audio_data)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def synthesize(self, text: str, output_path: Path, voice: str) -> float:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cache_key = self._get_cache_key(text, voice)
        cached_audio = self._get_cached_audio(cache_key)
        if cached_audio is not None:
            output_path.write_bytes(cached_audio)
            duration = self._estimate_duration(text)
            logger.info(
                "Using cached audio: %s chars, estimated duration: %.2fs", len(text), duration
            )
            return duration

        selected_voice = voice if voice in self._available_voices else "alloy"

        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": text,
            "voice": selected_voice,
        }

        try:
            response = self._http_client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()

            audio_data = response.content
            self._cache_audio(cache_key, audio_data)
            output_path.write_bytes(audio_data)

            duration = self._estimate_duration(text)

            logger.info(
                "OpenAI TTS synthesis complete: %s chars, voice=%s, duration=%.2fs",
                len(text),
                selected_voice,
                duration,
            )
            return duration
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("OpenAI rate limit exceeded, retrying...")
                raise
            logger.error("OpenAI API error: %s", str(e))
            raise OpenAITTSError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error("OpenAI TTS synthesis failed: %s", str(e))
            raise OpenAITTSError(f"OpenAI TTS synthesis failed: {e}")

    def _estimate_duration(self, text: str) -> float:
        words = len(text.split())
        avg_words_per_second = 2.5
        return max(0.1, words / avg_words_per_second)

    def health_check(self) -> bool:
        try:
            response = self._http_client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("OpenAI health check failed: %s", str(e))
            return False

    def get_available_voices(self) -> list[str]:
        return self._available_voices
