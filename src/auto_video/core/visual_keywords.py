"""Visual keyword extraction for segment-based video clips."""

import json
import logging
import random
from dataclasses import dataclass
from typing import Literal

from auto_video.config.schema import LLMProviderConfig
from auto_video.core.llm import LLM, load_prompt
from auto_video.utils.workspace import Workspace

logger = logging.getLogger(__name__)


@dataclass
class SegmentInfo:
    """Information about a script segment."""

    text: str
    keywords: list[str]
    duration: float


@dataclass
class MediaSegment:
    """Segment with media type support for videos or images."""

    text: str
    keywords: list[str]
    duration: float
    media_type: Literal["video", "image"] = "video"
    source: Literal["pexels", "duckduckgo"] | None = None
    start_time: float | None = None
    end_time: float | None = None


class VisualKeywordExtractor:
    def __init__(self, config: LLMProviderConfig, workspace: Workspace | None = None) -> None:
        self._llm = LLM(config)
        self._default_keywords = ["nature", "technology", "business", "abstract", "landscape"]
        self._workspace = workspace

    def extract_keywords_per_segment(self, script: str) -> list[SegmentInfo]:
        """Extract keywords and duration for each segment of the script.

        Args:
            script: The full video script text.

        Returns:
            List of SegmentInfo with text, keywords, and duration.
        """
        logger.debug(
            "[VisualKeywords] extract_keywords_per_segment: "
            "script_type=%s, script_is_none=%s, script_len=%s, first_100_chars=%r",
            type(script).__name__,
            script is None,
            len(script) if script is not None else "N/A",
            script[:100] if script else None,
        )
        if script is None:
            logger.warning("[VisualKeywords] Received None script! Using empty string.")
            script = ""

        logger.info("[VisualKeywords] Starting segmentation and keyword extraction...")
        segments = self._segment_script(script)
        logger.info("[VisualKeywords] ✓ Segmented into %d segments", len(segments))

        results = []

        for i, segment in enumerate(segments):
            logger.debug(
                "[VisualKeywords] Processing segment %d/%d: %r", i + 1, len(segments), segment[:80]
            )
            try:
                keywords = self._extract_keywords_for_segment(segment, script)
                duration = self._estimate_segment_duration(segment)
                results.append(SegmentInfo(text=segment, keywords=keywords, duration=duration))
                logger.debug(
                    "[VisualKeywords] ✓ Segment %d: %s -> keywords=%s, duration=%.2fs",
                    i,
                    segment[:50],
                    keywords,
                    duration,
                )
            except Exception as e:
                logger.warning(
                    "[VisualKeywords] Failed to extract keywords for segment %d: %s", i, str(e)
                )
                keywords = random.sample(
                    self._default_keywords, min(2, len(self._default_keywords))
                )
                duration = self._estimate_segment_duration(segment)
                results.append(SegmentInfo(text=segment, keywords=keywords, duration=duration))

        total_duration = sum(seg.duration for seg in results)
        logger.info(
            "[VisualKeywords] ✓ Extraction complete: %d segments, total duration=%.2fs",
            len(results),
            total_duration,
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
            logger.debug(
                "[VisualKeywords] Duration %.2fs below minimum, padding to %.2fs (words=%d)",
                estimated_seconds,
                minimum_duration,
                words,
            )
            return minimum_duration
        if estimated_seconds > maximum_duration:
            logger.debug(
                "[VisualKeywords] Duration %.2fs above maximum, capping at %.2fs (words=%d)",
                estimated_seconds,
                maximum_duration,
                words,
            )
            return maximum_duration

        return estimated_seconds

    def _extract_keywords_for_segment(self, segment: str, full_script: str) -> list[str]:
        logger.debug(
            "[VisualKeywords] extract_keywords: segment_len=%d, full_script_type=%s, full_script_is_none=%s",
            len(segment),
            type(full_script).__name__,
            full_script is None,
        )
        if full_script is None:
            logger.warning("[VisualKeywords] Received None full_script! Using empty string.")
            full_script = ""
        context = full_script[:1000] if len(full_script) > 1000 else full_script

        prompt = load_prompt(
            "visual_keywords_segment.txt",
            segment=segment,
            context=context,
        )

        logger.debug("[VisualKeywords] Sending prompt to LLM for segment: %r", segment[:60])

        try:
            response = self._llm.provider.generate(prompt)
            response = response.strip()

            if response.lower().startswith("keywords"):
                response = response.split(":", 1)[-1].strip()

            response = response.replace("\n", ",")
            keywords = [k.strip() for k in response.split(",") if k.strip()]

            logger.debug(
                "[VisualKeywords] LLM response: %r -> keywords: %s", response[:100], keywords
            )

            return keywords[:3] if keywords else random.sample(self._default_keywords, 2)

        except Exception as e:
            logger.error("[VisualKeywords] LLM error: %s", str(e))
            raise

    def _segment_script(self, script: str) -> list[str]:
        """Segment the script by sentence boundaries.

        Args:
            script: The full script text.

        Returns:
            List of script segments (one sentence per segment).
        """
        import re

        logger.debug("[VisualKeywords] Starting sentence-based segmentation...")
        segments = []
        lines = script.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Scene markers like [Intro] become their own segments
            if line.startswith("[") and line.endswith("]"):
                logger.debug("[VisualKeywords] Found scene marker: %r", line)
                segments.append(line)
                continue

            # Split by sentence boundaries: . ! ? followed by space or end of string
            # Handles common sentence endings and respects abbreviations
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", line)

            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and len(sentence) > 1:
                    logger.debug("[VisualKeywords] Extracted sentence: %r", sentence[:60])
                    segments.append(sentence)

        # Fallback: if no segments found, split by period as last resort
        if not segments:
            logger.warning("[VisualKeywords] No segments found, using fallback period splitting")
            parts = script.split(". ")
            segments = [s.strip() + "." for s in parts if s.strip()]

        logger.debug("[VisualKeywords] Segmentation complete: %d segments", len(segments))

        return segments if segments else [script[:200]]

    def cleanup(self) -> None:
        """Cleanup LLM resources and free GPU VRAM."""
        try:
            if self._llm:
                self._llm.cleanup()
                logger.info("Cleaned up VisualKeywordExtractor LLM resources")
        except Exception as e:
            logger.warning(f"Error during VisualKeywordExtractor cleanup: {str(e)}")

    def extract_keywords_all_at_once(self, script: str) -> list[MediaSegment]:
        """Extract all keywords and media types for the entire script in one LLM call.

        This method provides better context to the LLM, allowing for more coherent
        visual storytelling and intelligent alternation between videos and images.

        Args:
            script: The full video script text.

        Returns:
            List of MediaSegment with text, keywords, duration, and media_type.
        """
        logger.info("[VisualKeywords] Starting all-at-once extraction with media type selection...")
        logger.debug(
            "[VisualKeywords] script_type=%s, script_len=%s, first_200_chars=%r",
            type(script).__name__,
            len(script) if script is not None else "N/A",
            script[:200] if script else None,
        )

        if script is None:
            logger.warning("[VisualKeywords] Received None script! Using empty string.")
            script = ""

        prompt = self._build_structured_prompt(script)

        try:
            response = self._llm.provider.generate(prompt)
            response = response.strip()

            # Save raw response for debugging
            if self._workspace:
                try:
                    self._workspace.workspace_path.mkdir(parents=True, exist_ok=True)
                    self._workspace.visual_keywords_debug_path.write_text(
                        response, encoding="utf-8"
                    )
                    logger.info(
                        "[VisualKeywords] Saved raw LLM response to %s",
                        self._workspace.visual_keywords_debug_path,
                    )
                except Exception as e:
                    logger.warning("[VisualKeywords] Failed to save debug JSON: %s", str(e))

            # Try to extract JSON from the response
            segments_data = self._extract_json_from_response(response)

            if not segments_data:
                logger.warning("[VisualKeywords] Failed to parse JSON response, using fallback")
                return self._fallback_to_segmented_extraction(script)

            results = []
            for i, seg_data in enumerate(segments_data):
                text = seg_data.get("text", "").strip()
                keywords = seg_data.get("keywords", [])
                media_type = seg_data.get("media_type", "video")
                source = seg_data.get("source")

                if not text:
                    continue

                # Validate media_type
                if media_type not in ("video", "image"):
                    media_type = "video"

                # Ensure keywords is a list
                if isinstance(keywords, str):
                    keywords = [k.strip() for k in keywords.split(",") if k.strip()]
                elif not isinstance(keywords, list):
                    keywords = []

                # Clean keywords
                keywords = [k.replace("\n", " ").strip() for k in keywords if k and k.strip()]

                if not keywords:
                    keywords = random.sample(self._default_keywords, 2)

                duration = self._estimate_segment_duration(text)

                segment = MediaSegment(
                    text=text,
                    keywords=keywords,
                    duration=duration,
                    media_type=media_type,
                    source=source if media_type == "image" else None,
                )
                results.append(segment)

                logger.debug(
                    "[VisualKeywords] Segment %d: text=%r, keywords=%s, media_type=%s, source=%s, duration=%.2fs",
                    i + 1,
                    text[:50],
                    keywords,
                    media_type,
                    source,
                    duration,
                )

            total_duration = sum(seg.duration for seg in results)
            video_count = sum(1 for s in results if s.media_type == "video")
            image_count = sum(1 for s in results if s.media_type == "image")

            logger.info(
                "[VisualKeywords] ✓ All-at-once extraction complete: %d segments, "
                "%d videos, %d images, total_duration=%.2fs",
                len(results),
                video_count,
                image_count,
                total_duration,
            )

            return results

        except Exception as e:
            logger.error("[VisualKeywords] All-at-once extraction failed: %s", str(e))
            logger.warning("[VisualKeywords] Falling back to segmented extraction")
            return self._fallback_to_segmented_extraction(script)

    def _build_structured_prompt(self, script: str) -> str:
        return load_prompt("visual_keywords_structured.txt", script=script)

    def _extract_json_from_response(self, response: str) -> list[dict] | None:
        """Extract and parse JSON from LLM response.

        Args:
            response: The raw LLM response string.

        Returns:
            Parsed list of segment dictionaries, or None if parsing fails.
        """
        response = response.strip()

        # Try direct JSON parsing first
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in the response
        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, ValueError):
            pass

        # Try to find JSON code block
        if "```" in response:
            try:
                # Extract content between code blocks
                lines = response.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith("```"):
                        in_json = not in_json
                        continue
                    if in_json:
                        json_lines.append(line)
                if json_lines:
                    json_str = "\n".join(json_lines)
                    data = json.loads(json_str)
                    if isinstance(data, list):
                        return data
            except (json.JSONDecodeError, ValueError):
                pass

        logger.warning("[VisualKeywords] Could not extract valid JSON from response")
        return None

    def _fallback_to_segmented_extraction(self, script: str) -> list[MediaSegment]:
        """Fallback to legacy segmented extraction when JSON parsing fails.

        Args:
            script: The script text.

        Returns:
            List of MediaSegment objects.
        """
        logger.info("[VisualKeywords] Using fallback segmented extraction")

        segment_infos = self.extract_keywords_per_segment(script)

        # Convert to MediaSegment with default video type
        media_segments = []
        for seg_info in segment_infos:
            segment = MediaSegment(
                text=seg_info.text,
                keywords=seg_info.keywords,
                duration=seg_info.duration,
                media_type="video",
            )
            media_segments.append(segment)

        return media_segments

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during garbage collection


__all__ = ["VisualKeywordExtractor", "MediaSegment", "SegmentInfo"]
