"""GPU acceleration detection and management for FFmpeg."""

import logging
import subprocess
from typing import Literal

logger = logging.getLogger(__name__)


class GPUDetector:
    """Detect available GPU acceleration for FFmpeg."""

    @staticmethod
    def detect_available_acceleration() -> Literal["nvenc", "amf", "qsv", "none"]:
        """Detect available GPU acceleration.

        Returns:
            "nvenc" for NVIDIA GPUs
            "amf" for AMD GPUs
            "qsv" for Intel Quick Sync
            "none" if no GPU acceleration available
        """
        # Check for NVENC (NVIDIA)
        if GPUDetector._has_nvenc():
            logger.info("Detected NVIDIA NVENC support")
            return "nvenc"

        # Check for AMF (AMD)
        if GPUDetector._has_amf():
            logger.info("Detected AMD AMF support")
            return "amf"

        # Check for QSV (Intel Quick Sync)
        if GPUDetector._has_qsv():
            logger.info("Detected Intel Quick Sync support")
            return "qsv"

        logger.info("No GPU acceleration detected, using CPU")
        return "none"

    @staticmethod
    def _has_nvenc() -> bool:
        """Check if FFmpeg has NVENC support (NVIDIA)."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders", "-hide_banner"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "h264_nvenc" in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def _has_amf() -> bool:
        """Check if FFmpeg has AMF support (AMD)."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders", "-hide_banner"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "h264_amf" in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def _has_qsv() -> bool:
        """Check if FFmpeg has Quick Sync support (Intel)."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders", "-hide_banner"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "h264_qsv" in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def get_codec_name(gpu_acceleration: str) -> str:
        """Get FFmpeg codec name for GPU acceleration.

        Args:
            gpu_acceleration: Type of GPU acceleration (nvenc, amf, qsv, none, cpu)

        Returns:
            FFmpeg codec name (e.g., "h264_nvenc", "libx264")
        """
        codecs = {
            "nvenc": "h264_nvenc",
            "amf": "h264_amf",
            "qsv": "h264_qsv",
            "none": "libx264",
            "cpu": "libx264",
            "auto": "libx264",
        }
        return codecs.get(gpu_acceleration.lower(), "libx264")

    @staticmethod
    def get_nvenc_preset(preset: str) -> str:
        """Map generic preset names to NVENC presets.

        Args:
            preset: Generic preset name (slow, medium, fast, veryfast)

        Returns:
            NVENC preset (p1-p7)
        """
        preset_map = {
            "slow": "p1",
            "medium": "p4",
            "fast": "p5",
            "veryfast": "p6",
            "ultrafast": "p7",
        }
        return preset_map.get(preset.lower(), "p5")

    @staticmethod
    def get_amf_preset(preset: str) -> str:
        """Map generic preset names to AMF presets.

        Args:
            preset: Generic preset name (slow, medium, fast, veryfast)

        Returns:
            AMF preset (speed, balanced, quality)
        """
        preset_map = {
            "slow": "quality",
            "medium": "balanced",
            "fast": "speed",
            "veryfast": "speed",
            "ultrafast": "speed",
        }
        return preset_map.get(preset.lower(), "speed")


__all__ = ["GPUDetector"]
