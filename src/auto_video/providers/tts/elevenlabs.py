"""ElevenLabs TTS provider implementation."""

import hashlib
import logging
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.config.schema import TTSConfig
from auto_video.core.tts import TTSProvider

logger = logging.getLogger(__name__)


class ElevenLabsError(Exception):
    pass


class ElevenLabsProvider(TTSProvider):
    def __init__(self, config: TTSConfig) -> None:
        self.config = config
        self._api_key = config.api_key
        if not self._api_key:
            raise ValueError("ElevenLabs API key is required")
        self._cache_dir = Path.home() / ".cache" / "auto-video" / "elevenlabs"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._available_voices: list[str] = []
        self._voices_fetched = False
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    def _get_cache_key(self, text: str, voice: str) -> str:
        content = f"{text}:{voice}"
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

    def _fetch_available_voices(self) -> list[str]:
        if self._voices_fetched and self._available_voices:
            return self._available_voices

        try:
            assert self._api_key is not None
            response = self._http_client.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": self._api_key},
            )
            response.raise_for_status()
            data = response.json()
            voices = data.get("voices", [])
            self._available_voices = [voice["voice_id"] for voice in voices]
            self._voices_fetched = True
            logger.info("Fetched %d voices from ElevenLabs", len(self._available_voices))
            return self._available_voices
        except Exception as e:
            logger.error("Failed to fetch voices from ElevenLabs: %s", str(e))
            return ["21m00Tcm4TlvDq8ikWAM"]

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
            words = len(text.split())
            duration = words * 0.4
            logger.info(
                "Using cached audio: %s chars, estimated duration: %.2fs", len(text), duration
            )
            return duration

        voices = self._fetch_available_voices()
        selected_voice = (
            voice if voice in voices else voices[0] if voices else "21m00Tcm4TlvDq8ikWAM"
        )

        assert self._api_key is not None
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice}"
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }

        try:
            response = self._http_client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()

            audio_data = response.content
            self._cache_audio(cache_key, audio_data)
            output_path.write_bytes(audio_data)

            words = len(text.split())
            duration = words * 0.4

            logger.info(
                "ElevenLabs synthesis complete: %s chars, voice=%s, duration=%.2fs",
                len(text),
                selected_voice,
                duration,
            )
            return duration
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("ElevenLabs rate limit exceeded, retrying...")
                raise
            logger.error("ElevenLabs API error: %s", str(e))
            raise ElevenLabsError(f"ElevenLabs API error: {e}")
        except Exception as e:
            logger.error("ElevenLabs synthesis failed: %s", str(e))
            raise ElevenLabsError(f"ElevenLabs synthesis failed: {e}")

    def health_check(self) -> bool:
        try:
            assert self._api_key is not None
            response = self._http_client.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": self._api_key},
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("ElevenLabs health check failed: %s", str(e))
            return False

    def get_available_voices(self) -> list[str]:
        return self._fetch_available_voices()
