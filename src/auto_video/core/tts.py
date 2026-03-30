"""TTS core module."""

import logging
import struct
from abc import ABC, abstractmethod
from pathlib import Path

from auto_video.config.schema import TTSConfig

logger = logging.getLogger(__name__)

__all__ = ["TTS", "TTSProvider", "MockTTSProvider"]


class TTSProvider(ABC):
    @abstractmethod
    def __init__(self, config: TTSConfig) -> None: ...

    @abstractmethod
    def synthesize(self, text: str, output_path: Path, voice: str) -> float: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    @abstractmethod
    def get_available_voices(self) -> list[str]: ...

    def cleanup(self) -> None:
        """Cleanup TTS resources and free GPU VRAM."""
        # Subclasses should override this if needed
        pass


class MockTTSProvider(TTSProvider):
    def __init__(self, config: TTSConfig) -> None:
        self.config = config

    def synthesize(self, text: str, output_path: Path, voice: str) -> float:
        """Create a minimal valid WAV file for testing."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate duration (0.3 seconds per word)
        words = len(text.split())
        duration = words * 0.3

        # Create a minimal valid WAV file (PCM 16-bit, mono, 22050 Hz)
        sample_rate = 22050
        num_samples = int(duration * sample_rate)

        # WAV header (44 bytes)
        # RIFF header
        riff = b"RIFF"
        chunk_size = struct.pack("<I", 36 + num_samples * 2)
        wave = b"WAVE"

        # fmt subchunk
        fmt = b"fmt "
        fmt_chunk_size = struct.pack("<I", 16)
        audio_format = struct.pack("<H", 1)  # PCM
        num_channels = struct.pack("<H", 1)  # Mono
        byte_rate = struct.pack("<I", sample_rate * 2)
        block_align = struct.pack("<H", 2)
        bits_per_sample = struct.pack("<H", 16)

        # data subchunk
        data = b"data"
        data_size = struct.pack("<I", num_samples * 2)

        # Generate silence (zeros)
        audio_data = b"\x00\x00" * num_samples

        # Write WAV file
        with open(output_path, "wb") as f:
            f.write(riff + chunk_size + wave)
            f.write(fmt + fmt_chunk_size + audio_format + num_channels)
            f.write(struct.pack("<I", sample_rate) + byte_rate + block_align + bits_per_sample)
            f.write(data + data_size)
            f.write(audio_data)

        return duration

    def health_check(self) -> bool:
        return True

    def get_available_voices(self) -> list[str]:
        return ["default", "male", "female"]

    def cleanup(self) -> None:
        """Cleanup mock TTS resources."""
        pass


class TTS:
    def __init__(self, config: TTSConfig) -> None:
        self.config = config
        self._provider = self._create_provider()
        logger.info("[TTS] Initialized with provider: %s", self._provider.__class__.__name__)

    def _create_provider(self) -> TTSProvider:
        from auto_video.providers.tts import create_provider

        provider = create_provider(self.config)
        logger.debug("[TTS] Created provider: %s", provider.__class__.__name__)
        return provider

    @property
    def provider(self) -> TTSProvider:
        return self._provider

    def _segment_text(self, text: str, max_chars: int = 1000) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        segments: list[str] = []
        paragraphs = text.split("\n\n")
        current_segment = ""
        for paragraph in paragraphs:
            if len(current_segment) + len(paragraph) + 2 <= max_chars:
                current_segment += ("\n\n" if current_segment else "") + paragraph
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                if len(paragraph) > max_chars:
                    sentences = paragraph.replace(". ", ".\n").split("\n")
                    current_segment = ""
                    for sentence in sentences:
                        if len(current_segment) + len(sentence) + 1 <= max_chars:
                            current_segment += (" " if current_segment else "") + sentence
                        else:
                            if current_segment:
                                segments.append(current_segment.strip())
                            current_segment = sentence
                else:
                    current_segment = paragraph
        if current_segment:
            segments.append(current_segment.strip())
        return segments

    def synthesize_script(self, script: str, output_path: Path) -> float:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        voice = self.config.voice or "default"

        script_len = len(script)
        word_count = len(script.split())
        logger.info("[TTS] Synthesizing script: %d chars, %d words, voice=%s", script_len, word_count, voice)
        logger.debug("[TTS] Script preview: %r", script[:100])

        segments = self._segment_text(script)
        logger.info("[TTS] Script segmented into %d part(s)", len(segments))

        if len(segments) == 1:
            logger.debug("[TTS] Single segment synthesis")
            duration = self._provider.synthesize(segments[0], output_path, voice)
            logger.info("[TTS] ✓ Synthesis complete: duration=%.2fs", duration)
            return duration

        total_duration = 0.0
        segment_paths: list[Path] = []
        for i, segment in enumerate(segments):
            segment_path = output_path.parent / f"{output_path.stem}_part{i}.wav"
            logger.debug("[TTS] Synthesizing segment %d/%d: %d chars", i + 1, len(segments), len(segment))
            duration = self._provider.synthesize(segment, segment_path, voice)
            total_duration += duration
            segment_paths.append(segment_path)
            logger.debug("[TTS] Segment %d complete: %.2fs", i + 1, duration)

        if segment_paths:
            import subprocess

            logger.debug("[TTS] Combining %d audio segments with ffmpeg", len(segment_paths))
            manifest = output_path.parent / "audio_concat_manifest.txt"
            with manifest.open("w") as f:
                for sp in segment_paths:
                    f.write(f"file '{sp.absolute()}'\n")
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(manifest),
                    "-c",
                    "copy",
                    str(output_path),
                ],
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.error("[TTS] FFmpeg concatenation failed: %s", result.stderr.decode())
                raise RuntimeError(f"Failed to combine audio segments: {result.stderr.decode()}")

            logger.debug("[TTS] Cleaning up temporary segment files")
            for sp in segment_paths:
                sp.unlink(missing_ok=True)
            manifest.unlink(missing_ok=True)

        logger.info("[TTS] ✓ Multi-segment synthesis complete: total_duration=%.2fs", total_duration)
        return total_duration

    def get_available_voices(self) -> list[str]:
        return self._provider.get_available_voices()
