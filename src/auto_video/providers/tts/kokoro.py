"""
Kokoro TTS provider with GPU acceleration support.

GPU Requirements:
- Install onnxruntime-gpu: pip install onnxruntime-gpu
- CUDA drivers must be installed on your system (CUDA 12+ recommended)
- cuDNN libraries must be available

GPU Configuration:
- Automatic: onnxruntime-gpu will auto-detect CUDA and use it if available
- The provider automatically configures LD_LIBRARY_PATH for cuDNN if found at
  /usr/local/lib/ollama/mlx_cuda_v13
- Manual override: Set ONNX_PROVIDER=CUDAExecutionProvider environment variable
- Check GPU status: Provider will log "GPU enabled (CUDAExecutionProvider)" or
  "Using CPU only"

Performance:
- CPU: ~90x real-time speed (limited by CPU)
- GPU: Significantly faster, especially for long texts
- VRAM: Kokoro model is ~300MB, so works well with other GPU workloads

Troubleshooting:
- If GPU is not detected, check that cuDNN libraries are in LD_LIBRARY_PATH
- On systems with CUDA 13.0, ensure cuDNN 9.x is available
- The provider will automatically fall back to CPU if GPU is unavailable
"""

import logging
import os
from pathlib import Path

from auto_video.config.schema import TTSConfig
from auto_video.core.tts import TTSProvider

logger = logging.getLogger(__name__)

# Configure LD_LIBRARY_PATH for CUDA/cuDNN if available
_cudnn_path = "/usr/local/lib/ollama/mlx_cuda_v13"
if os.path.exists(_cudnn_path) and _cudnn_path not in os.environ.get("LD_LIBRARY_PATH", ""):
    current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = f"{_cudnn_path}:{current_ld_path}"

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

        # GPU Provider Configuration
        self._onnx_providers = self._get_onnx_providers()

        # Check for ONNX_PROVIDER environment variable override
        env_provider = os.getenv("ONNX_PROVIDER")
        if env_provider:
            self._onnx_providers = [env_provider]
            logger.info(f"Kokoro TTS: Using provider from ONNX_PROVIDER env var: {env_provider}")

        self._gpu_enabled = "CUDAExecutionProvider" in self._onnx_providers

        if self._gpu_enabled:
            logger.info("Kokoro TTS: GPU enabled (CUDAExecutionProvider - default provider)")
        else:
            logger.info("Kokoro TTS: Using CPU only")

        self._available_voices = [
            # American English (existing)
            "af_bella",
            "af_nicole",
            "af_sarah",
            "af_sky",
            "am_adam",
            "am_michael",
            # British English (existing)
            "bf_emma",
            "bf_isabella",
            "bm_george",
            "bm_lewis",
            # French (NEW)
            "ff_siwis",
            # Spanish (NEW)
            "ef_dora",
            "em_alex",
            "em_santa",
            # Italian (NEW)
            "if_sara",
            "im_nicola",
            # Brazilian Portuguese (NEW)
            "pf_dora",
            "pm_alex",
            "pm_santa",
            # Hindi (NEW)
            "hf_alpha",
            "hf_beta",
            "hm_david",
            "hm_raj",
            # Japanese (NEW)
            "jf_alpha",
            "jf_beta",
            "jm_gamma",
            "jm_kumo",
            # Mandarin Chinese (NEW)
            "zf_alpha",
            "zf_beta",
            "zf_gamma",
            "zm_xu",
        ]
        self._model_path = self._cache_dir / "kokoro-v1.0.onnx"
        self._voices_path = self._cache_dir / "voices.bin"
        self._initialize_model()

    @staticmethod
    def _get_onnx_providers() -> list[str]:
        """Get available ONNX Runtime providers with CUDA as priority, excluding TensorRT."""
        try:
            import onnxruntime as rt  # type: ignore[import-not-found]

            all_providers = rt.get_available_providers()

            # Completely exclude TensorRT to avoid any errors/warnings
            filtered_providers = [p for p in all_providers if "TensorrtExecutionProvider" not in p]

            # Prioritize CUDA if available
            prioritized_providers = []
            cuda_provider = "CUDAExecutionProvider"

            if cuda_provider in filtered_providers:
                prioritized_providers.append(cuda_provider)
                # Add remaining providers (except CUDA) to avoid duplicates
                prioritized_providers.extend([p for p in filtered_providers if p != cuda_provider])
            else:
                # If CUDA not available, use filtered providers (without TensorRT)
                prioritized_providers = filtered_providers

            return prioritized_providers
        except Exception:
            return ["CPUExecutionProvider"]  # Fallback

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
            # Create ONNX Runtime session with GPU providers
            import onnxruntime as rt  # type: ignore[import-not-found]

            session = rt.InferenceSession(
                str(self._model_path),
                providers=self._onnx_providers,
            )

            # Create Kokoro from custom session
            self._model = Kokoro.from_session(session, str(self._voices_path))
            logger.info(
                f"Kokoro model loaded successfully from cache (providers: {self._onnx_providers})"
            )
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
                text, voice=selected_voice, speed=1.0, lang=self.config.lang
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

    def cleanup(self) -> None:
        """Unload Kokoro model and free GPU VRAM."""
        if self._model is not None:
            del self._model
            self._model = None

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        try:
            self.cleanup()
        except Exception:
            pass
