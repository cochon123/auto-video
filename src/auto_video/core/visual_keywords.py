"""Visual keyword extraction for segment-based video clips."""

import logging
import random

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.llm import LLM

logger = logging.getLogger(__name__)


class VisualKeywordExtractor:
    def __init__(self, config: LLMProviderConfig) -> None:
        self._llm = LLM(config)
        self._default_keywords = ["nature", "technology", "business", "abstract", "landscape"]

    def extract_keywords_per_segment(self, script: str) -> list[tuple[str, list[str]]]:
        """Extract keywords for each segment of the script.

        Args:
            script: The full video script text.

        Returns:
            List of (segment_text, keywords) tuples.
        """
        segments = self._segment_script(script)
        results = []

        logger.info("Extracting keywords for %d segments", len(segments))

        for i, segment in enumerate(segments):
            try:
                keywords = self._extract_keywords_for_segment(segment, script)
                results.append((segment, keywords))
                logger.debug("Segment %d: %s -> %s", i, segment[:50], keywords)
            except Exception as e:
                logger.warning("Failed to extract keywords for segment %d: %s", i, str(e))
                keywords = random.sample(
                    self._default_keywords, min(2, len(self._default_keywords))
                )
                results.append((segment, keywords))

        return results

    def _extract_keywords_for_segment(self, segment: str, full_script: str) -> list[str]:
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
        """Segment the script into individual parts.

        Args:
            script: The full script text.

        Returns:
            List of script segments.
        """
        segments = []
        lines = script.split("\n")

        current_segment = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("[") and line.endswith("]"):
                if current_segment:
                    segments.append(current_segment.strip())
                    current_segment = ""
                current_segment = line
            else:
                if current_segment:
                    current_segment += " " + line
                else:
                    current_segment = line

                if len(current_segment) > 100:
                    segments.append(current_segment.strip())
                    current_segment = ""

        if current_segment:
            segments.append(current_segment.strip())

        if not segments:
            sentences = script.replace(".", ".\n").split("\n")
            current = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                current += " " + sentence if current else sentence
                if len(current) > 80:
                    segments.append(current.strip())
                    current = ""
            if current:
                segments.append(current.strip())

        return segments if segments else [script[:200]]


__all__ = ["VisualKeywordExtractor"]
