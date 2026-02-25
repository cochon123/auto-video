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
        provider_names = [p.__class__.__name__ for p in self._providers]
        logger.info("[StockManager] Initialized with providers: %s", provider_names)

    def _create_providers(self) -> list[StockProvider]:
        providers: list[StockProvider] = []

        logger.debug("[StockManager] Configured providers: %s", self.config.providers)

        if "pexels" in self.config.providers and self.config.pexels_api_key:
            from auto_video.providers.stock.pexels import PexelsProvider

            providers.append(PexelsProvider(self.config.pexels_api_key))
            logger.debug("[StockManager] ✓ Pexels provider added")

        if "pixabay" in self.config.providers and self.config.pixabay_api_key:
            from auto_video.providers.stock.pixabay import PixabayProvider

            providers.append(PixabayProvider(self.config.pixabay_api_key))
            logger.debug("[StockManager] ✓ Pixabay provider added")

        if not providers:
            providers.append(MockStockProvider())
            logger.warning("[StockManager] No stock providers configured, using MockStockProvider")

        return providers

    def get_clips_for_segments(
        self,
        segments: "list[SegmentInfo]",
        output_dir: Path,
        global_keywords: list[str] | None = None,
    ) -> list[Path]:
        """Get clips for each segment with specific keywords and duration.

        Each segment gets exactly one clip matching its estimated duration.
        Implements a fallback mechanism to ensure every segment gets a clip.

        Args:
            segments: List of SegmentInfo with text, keywords, and duration.
            output_dir: Directory to save downloaded clips.
            global_keywords: Optional global keywords to use as fallback.

        Returns:
            List of paths to downloaded video clips (one clip per segment).
        """
        logger.info("[StockManager] Starting clip search for %d segments, output_dir: %s", len(segments), output_dir)
        if global_keywords:
            logger.debug("[StockManager] Global keywords provided: %s", global_keywords[:5])

        clips: list[Path] = []
        clip_index = 0

        # Default fallback keywords in increasing order of generality
        fallback_keywords_tiers = [
            ["politics", "speech", "campaign", "government", "leader"],
            ["business", "office", "meeting", "presentation"],
            ["people", "crowd", "city", "urban"],
            ["nature", "landscape", "technology", "abstract"],
        ]

        for segment_info in segments:
            keywords = segment_info.keywords
            duration = segment_info.duration

            logger.debug(
                "[StockManager] Segment %d: %r, keywords=%s, duration=%.2fs",
                clip_index + 1,
                segment_info.text[:50],
                keywords,
                duration,
            )

            # Build keyword tiers for this segment
            keyword_tiers = []

            # Tier 0: LLM-extracted keywords for this segment
            if keywords:
                clean_keywords = []
                for kw in keywords:
                    kw_clean = kw.replace("\n", " ").replace("\r", " ").strip()
                    if kw_clean and len(kw_clean) > 1:
                        clean_keywords.append(kw_clean)
                if clean_keywords:
                    keyword_tiers.append(clean_keywords)
                    logger.debug("[StockManager] Tier 0 (LLM): %s", clean_keywords)

            # Tier 1: Global keywords (if provided)
            if global_keywords:
                clean_global = []
                for kw in global_keywords[:5]:
                    kw_clean = kw.replace("\n", " ").replace("\r", " ").strip()
                    if kw_clean and len(kw_clean) > 1:
                        clean_global.append(kw_clean)
                if clean_global:
                    keyword_tiers.append(clean_global)
                    logger.debug("[StockManager] Tier 1 (Global): %s", clean_global)

            # Tier 2+: Fallback keyword tiers
            keyword_tiers.extend(fallback_keywords_tiers)
            logger.debug("[StockManager] Total tiers available: %d", len(keyword_tiers))

            # Try each tier until we find a clip
            clip_found = False
            for tier_idx, tier_keywords in enumerate(keyword_tiers):
                query = tier_keywords[0]

                logger.debug(
                    "[StockManager] Trying tier %d with query: %r",
                    tier_idx,
                    query,
                )

                try:
                    all_results: list[tuple[StockProvider, VideoResult]] = []
                    for provider in self._providers:
                        try:
                            duration_min = max(2, int(duration) - 2)
                            results = provider.search_videos(query, duration_min=duration_min)
                            logger.debug(
                                "[StockManager] %s returned %d results for %r",
                                provider.__class__.__name__,
                                len(results),
                                query,
                            )
                            all_results.extend([(provider, r) for r in results])
                        except Exception as e:
                            logger.debug(
                                "[StockManager] %s failed for %r: %s",
                                provider.__class__.__name__,
                                query,
                                e,
                            )
                            continue

                    if not all_results:
                        logger.debug(
                            "[StockManager] Tier %d: No results for query %r",
                            tier_idx,
                            query,
                        )
                        continue

                    provider, video_result = self._find_best_matching_clip(all_results, duration)

                    logger.debug(
                        "[StockManager] Best match: duration=%.2fs (target=%.2fs), id=%s",
                        video_result.duration,
                        duration,
                        video_result.id,
                    )

                    output_path = output_dir / f"clip_{clip_index:03d}.mp4"
                    logger.debug("[StockManager] Downloading to: %s", output_path)

                    downloaded = provider.download_video(video_result.id, output_path, "medium")
                    clips.append(downloaded)
                    clip_index += 1

                    tier_name = "LLM" if tier_idx == 0 else ("Global" if tier_idx == 1 else f"Fallback-{tier_idx-1}")
                    logger.info(
                        "✓ Segment %d: %s (%.2fs) using %s keywords: %r",
                        clip_index,
                        segment_info.text[:40],
                        duration,
                        tier_name,
                        query,
                    )
                    clip_found = True
                    break

                except Exception as e:
                    logger.warning("[StockManager] Failed to download clip with %r: %s", query, str(e))
                    continue

            if not clip_found:
                logger.error(
                    "[StockManager] ✗ FAILED to find ANY clip for segment: %r (tried %d keyword tiers)",
                    segment_info.text[:60],
                    len(keyword_tiers),
                )

        logger.info(
            "[StockManager] Complete: downloaded %d clips for %d segments (%.1f%% coverage)",
            len(clips),
            len(segments),
            100.0 * len(clips) / len(segments) if segments else 0,
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

        logger.debug("[StockManager] Finding best match for target_duration=%.2fs from %d results", target_duration, len(results))

        best_result = results[0]
        best_diff = abs(best_result[1].duration - target_duration)

        for provider, video_result in results[1:]:
            diff = abs(video_result.duration - target_duration)
            if diff < best_diff:
                best_result = (provider, video_result)
                best_diff = diff

        logger.debug(
            "[StockManager] Best match: provider=%s, duration=%.2fs, diff=%.2fs",
            best_result[0].__class__.__name__,
            best_result[1].duration,
            best_diff,
        )

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
