"""Stock footage provider implementations."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from auto_video.config.schema import VisualsConfig
from auto_video.core.video import StockProvider, VideoResult
from auto_video.providers.stock.base import MockStockProvider

if TYPE_CHECKING:
    from auto_video.core.visual_keywords import SegmentInfo

logger = logging.getLogger(__name__)


class StockManager:
    def __init__(self, config: VisualsConfig) -> None:
        self.config = config
        self._providers = self._create_providers()

    def _create_providers(self) -> list[StockProvider]:
        providers: list[StockProvider] = []

        if "pexels" in self.config.providers and self.config.pexels_api_key:
            from auto_video.providers.stock.pexels import PexelsProvider

            providers.append(PexelsProvider(self.config.pexels_api_key))

        if "pixabay" in self.config.providers and self.config.pixabay_api_key:
            from auto_video.providers.stock.pixabay import PixabayProvider

            providers.append(PixabayProvider(self.config.pixabay_api_key))

        if not providers:
            providers.append(MockStockProvider())

        return providers

    def get_clips_for_segments(
        self,
        segments: "list[SegmentInfo]",
        output_dir: Path,
    ) -> list[Path]:
        """Get clips for each segment with specific keywords and duration.

        Each segment gets exactly one clip matching its estimated duration.

        Args:
            segments: List of SegmentInfo with text, keywords, and duration.
            output_dir: Directory to save downloaded clips.

        Returns:
            List of paths to downloaded video clips (one clip per segment).
        """
        clips: list[Path] = []
        clip_index = 0

        for segment_info in segments:
            keywords = segment_info.keywords
            duration = segment_info.duration

            if not keywords:
                keywords = ["nature", "technology", "abstract"]

            clean_keywords = []
            for kw in keywords:
                kw_clean = kw.replace("\n", " ").replace("\r", " ").strip()
                if kw_clean and len(kw_clean) > 1:
                    clean_keywords.append(kw_clean)

            if not clean_keywords:
                clean_keywords = ["nature", "technology", "abstract"]

            query = clean_keywords[0]

            try:
                all_results: list[tuple[StockProvider, VideoResult]] = []
                for provider in self._providers:
                    try:
                        duration_min = max(2, int(duration) - 2)
                        results = provider.search_videos(query, duration_min=duration_min)
                        all_results.extend([(provider, r) for r in results])
                    except Exception:
                        continue

                if not all_results:
                    logger.warning(
                        "No results for segment: %s (duration: %.2fs)",
                        segment_info.text[:50],
                        duration,
                    )
                    continue

                provider, video_result = self._find_best_matching_clip(all_results, duration)

                output_path = output_dir / f"clip_{clip_index:03d}.mp4"
                downloaded = provider.download_video(video_result.id, output_path, "medium")
                clips.append(downloaded)
                clip_index += 1
                logger.debug(
                    "Downloaded clip %d: %s (%.2fs) for segment (%.2fs), keywords: %s",
                    clip_index,
                    video_result.duration,
                    duration,
                    keywords[:2],
                )

            except Exception as e:
                logger.warning("Failed to download clip: %s", str(e))
                continue

        logger.info(
            "StockManager: downloaded %d clips for %d segments (one clip per segment)",
            len(clips),
            len(segments),
        )

        return clips

    def _find_best_matching_clip(
        self, results: list[tuple[StockProvider, VideoResult]], target_duration: float
    ) -> tuple[StockProvider, VideoResult]:
        """Find the clip that best matches the target duration.

        Args:
            results: List of (provider, video_result) tuples.
            target_duration: Desired clip duration in seconds.

        Returns:
            Tuple of (provider, video_result) for best matching clip.
        """
        if not results:
            raise ValueError("No clips to choose from")

        best_result = results[0]
        best_diff = abs(best_result[1].duration - target_duration)

        for provider, video_result in results[1:]:
            diff = abs(video_result.duration - target_duration)
            if diff < best_diff:
                best_result = (provider, video_result)
                best_diff = diff

        return best_result

    def get_clips_for_script(
        self, script: str, keywords: list[str], total_duration: float, output_dir: Path
    ) -> list[Path]:
        import random

        clips: list[Path] = []
        current_duration = 0.0
        clip_index = 0

        clean_keywords = []
        for kw in keywords[:10]:
            kw_clean = kw.replace("\n", " ").replace("\r", " ").strip()
            if kw_clean and len(kw_clean) > 1:
                clean_keywords.append(kw_clean)

        if not clean_keywords:
            clean_keywords = ["nature", "landscape", "technology"]

        clean_keywords.append(self._extract_keywords_from_script(script))

        while current_duration < total_duration:
            query = random.choice(clean_keywords)
            duration_needed = min(10, int(total_duration - current_duration))

            all_results: list[tuple[StockProvider, VideoResult]] = []
            for provider in self._providers:
                try:
                    results = provider.search_videos(query, duration_needed)
                    all_results.extend([(provider, r) for r in results])
                except Exception:
                    continue

            if not all_results:
                continue

            provider, video_result = random.choice(all_results)

            try:
                output_path = output_dir / f"clip_{clip_index:03d}.mp4"
                downloaded = provider.download_video(video_result.id, output_path, "medium")
                clips.append(downloaded)
                current_duration += video_result.duration
                clip_index += 1
            except Exception:
                continue

        logger.info(
            "StockManager: downloaded %d clips, total_duration=%.2fs", len(clips), current_duration
        )
        return clips

    def _extract_keywords_from_script(self, script: str) -> str:
        words = script.lower().split()
        stop_words = {"le", "la", "les", "un", "une", "des", "de", "du", "et", "en", "dans", "pour"}
        filtered = [w for w in words if len(w) > 4 and w not in stop_words]
        return filtered[0] if filtered else "video"


__all__ = ["StockManager", "MockStockProvider"]
