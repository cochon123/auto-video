"""Kokoro TTS provider implementation using kokoro-onnx."""

import logging
from pathlib import Path

from auto_video.config.schema import TTSConfig
from auto_video.core.tts import TTSProvider

logger = logging.getLogger(__name__)

KOKORO_AVAILABLE = False

try:
    from kokoro_onnx import Kokoro  # type: ignore[import-not-found]

    KOKORO_AVAILABLE = True
except ImportError:
    pass


class KokoroTTSProvider(TTSProvider):
    def __init__(self, config: TTSConfig) -> None:
        self.config = config
        self._cache_dir = Path.home() / ".cache" / "auto-video" / "kokoro"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._available_voices = [
            "af_bella",
            "af_nicole",
            "af_sarah",
            "af_sky",
            "am_adam",
            "am_michael",
            "bf_emma",
            "bf_isabella",
            "bm_george",
            "bm_lewis",
        ]
        self._model_path = self._cache_dir / "kokoro-v1.0.onnx"
        self._voices_path = self._cache_dir / "voices.bin"
        self._initialize_model()

    def _download_model(self) -> bool:
        """Download the Kokoro ONNX model and voices file."""
        try:
            import urllib.request

            # Download model - using model-files release (more stable)
            model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
            voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"

            logger.info("Downloading Kokoro model...")
            urllib.request.urlretrieve(model_url, str(self._model_path))
            logger.info("Downloading voices file...")
            urllib.request.urlretrieve(voices_url, str(self._voices_path))
            return True
        except Exception as e:
            logger.error("Failed to download Kokoro model: %s", str(e))
            return False

    def _initialize_model(self) -> None:
        if not KOKORO_AVAILABLE:
            logger.warning("Kokoro library not available, using mock implementation")
            return

        # Download model if not exists
        if not self._model_path.exists() or not self._voices_path.exists():
            logger.info("Downloading Kokoro model files...")
            if not self._download_model():
                logger.warning("Failed to download Kokoro model, using mock implementation")
                return

        try:
            # Set the model and voices paths
            self._model = Kokoro(str(self._model_path), str(self._voices_path))
            logger.info("Kokoro model loaded successfully from cache")
        except Exception as e:
            logger.error("Failed to load Kokoro model: %s", str(e))
            self._model = None

    def synthesize(self, text: str, output_path: Path, voice: str) -> float:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not KOKORO_AVAILABLE or self._model is None:
            output_path.write_bytes(b"MOCK_KOKORO_AUDIO_DATA")
            words = len(text.split())
            duration = words * 0.35
            logger.info(
                "Mock synthesis for Kokoro: %s chars, estimated duration: %.2fs",
                len(text),
                duration,
            )
            return duration

        selected_voice = voice if voice in self._available_voices else "af_sarah"

        try:
            import soundfile as sf

            audio_samples, sample_rate = self._model.create(
                text, voice=selected_voice, speed=1.0, lang="en-us"
            )

            sf.write(str(output_path), audio_samples, sample_rate)

            duration = len(audio_samples) / sample_rate
            logger.info(
                "Kokoro synthesis complete: %s chars, voice=%s, duration=%.2fs",
                len(text),
                selected_voice,
                duration,
            )
            return duration
        except Exception as e:
            logger.error("Kokoro synthesis failed: %s", str(e))
            output_path.write_bytes(b"MOCK_KOKORO_AUDIO_DATA")
            words = len(text.split())
            duration = words * 0.35
            return duration

    def health_check(self) -> bool:
        if not KOKORO_AVAILABLE:
            return False

        try:
            from kokoro_onnx import Kokoro  # type: ignore[import-not-found]

            _ = Kokoro
            return True
        except Exception:
            return False

    def get_available_voices(self) -> list[str]:
        return self._available_voices
