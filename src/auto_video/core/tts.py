"""TTS core module."""

import logging
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
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"MOCK_AUDIO_DATA")
        words = len(text.split())
        duration = words * 0.3
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
