"""Visual keyword extraction for segment-based video clips."""

import logging
import random
from dataclasses import dataclass

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.llm import LLM

logger = logging.getLogger(__name__)


@dataclass
class SegmentInfo:
    """Information about a script segment."""

    text: str
    keywords: list[str]
    duration: float


class VisualKeywordExtractor:
    def __init__(self, config: LLMProviderConfig) -> None:
        self._llm = LLM(config)
        self._default_keywords = ["nature", "technology", "business", "abstract", "landscape"]

    def extract_keywords_per_segment(self, script: str) -> list[SegmentInfo]:
        """Extract keywords and duration for each segment of the script.

        Args:
            script: The full video script text.

        Returns:
            List of SegmentInfo with text, keywords, and duration.
        """
        logger.debug(
            "[DEBUG] VisualKeywordExtractor.extract_keywords_per_segment: "
            "script_type=%s, script_is_none=%s, script_len=%s, first_100_chars=%r",
            type(script).__name__,
            script is None,
            len(script) if script is not None else "N/A",
            script[:100] if script else None,
        )
        if script is None:
            logger.warning(
                "[DEBUG] VisualKeywordExtractor received None script! This should not happen."
            )
            script = ""
        segments = self._segment_script(script)
        results = []

        logger.info("Extracting keywords and durations for %d segments", len(segments))

        for i, segment in enumerate(segments):
            try:
                keywords = self._extract_keywords_for_segment(segment, script)
                duration = self._estimate_segment_duration(segment)
                results.append(SegmentInfo(text=segment, keywords=keywords, duration=duration))
                logger.debug(
                    "Segment %d: %s -> %s (%.2fs)",
                    i,
                    segment[:50],
                    keywords,
                    duration,
                )
            except Exception as e:
                logger.warning("Failed to extract keywords for segment %d: %s", i, str(e))
                keywords = random.sample(
                    self._default_keywords, min(2, len(self._default_keywords))
                )
                duration = self._estimate_segment_duration(segment)
                results.append(SegmentInfo(text=segment, keywords=keywords, duration=duration))

        logger.info(
            "Total estimated duration from segments: %.2fs",
            sum(seg.duration for seg in results),
        )

        return results

    def _estimate_segment_duration(self, text: str) -> float:
        """Estimate speech duration for a text segment.

        Based on typical speech rates:
        - English: ~150 words/minute = 2.5 words/second
        - French: ~130 words/minute = 2.17 words/second
        - Average: ~2.3 words/second

        Args:
            text: Segment text.

        Returns:
            Estimated duration in seconds.
        """
        words = len(text.split())
        estimated_seconds = words / 2.3

        minimum_duration = 3.0
        maximum_duration = 30.0

        if estimated_seconds < minimum_duration:
            return minimum_duration
        if estimated_seconds > maximum_duration:
            return maximum_duration

        return estimated_seconds

    def _extract_keywords_for_segment(self, segment: str, full_script: str) -> list[str]:
        logger.debug(
            "[DEBUG] _extract_keywords_for_segment: full_script_type=%s, full_script_is_none=%s",
            type(full_script).__name__,
            full_script is None,
        )
        if full_script is None:
            logger.warning(
                "[DEBUG] _extract_keywords_for_segment received None full_script! Using empty string."
            )
            full_script = ""
        context = full_script[:1000] if len(full_script) > 1000 else full_script

        prompt = (
            "You are a stock video search expert. "
            f"Given this sentence from a video script:\n"
            f'"{segment}"\n'
            f"And this context from the full script:\n"
            f'"{context}"\n\n'
            "Extract 2-3 specific keywords for searching stock video footage. "
            "Return ONLY a comma-separated list of keywords, nothing else. "
            "Example output: nature, technology, office"
        )

        try:
            response = self._llm.provider.generate(prompt)
            response = response.strip()

            if response.lower().startswith("keywords"):
                response = response.split(":", 1)[-1].strip()

            response = response.replace("\n", ",")
            keywords = [k.strip() for k in response.split(",") if k.strip()]

            return keywords[:3] if keywords else random.sample(self._default_keywords, 2)

        except Exception as e:
            logger.error("LLM error: %s", str(e))
            raise

    def _segment_script(self, script: str) -> list[str]:
        """Segment the script by sentence boundaries.

        Args:
            script: The full script text.

        Returns:
            List of script segments (one sentence per segment).
        """
        import re

        segments = []
        lines = script.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Scene markers like [Intro] become their own segments
            if line.startswith("[") and line.endswith("]"):
                segments.append(line)
                continue

            # Split by sentence boundaries: . ! ? followed by space or end of string
            # Handles common sentence endings and respects abbreviations
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', line)

            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and len(sentence) > 1:
                    segments.append(sentence)

        # Fallback: if no segments found, split by period as last resort
        if not segments:
            parts = script.split(". ")
            segments = [s.strip() + "." for s in parts if s.strip()]

        return segments if segments else [script[:200]]

    def cleanup(self) -> None:
        """Cleanup LLM resources and free GPU VRAM."""
        try:
            if self._llm:
                self._llm.cleanup()
                logger.info("Cleaned up VisualKeywordExtractor LLM resources")
        except Exception as e:
            logger.warning(f"Error during VisualKeywordExtractor cleanup: {str(e)}")

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during garbage collection


__all__ = ["VisualKeywordExtractor"]
