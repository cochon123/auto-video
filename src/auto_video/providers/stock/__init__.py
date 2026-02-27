"""Stock footage provider implementations."""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from auto_video.config.schema import VisualsConfig
from auto_video.core.video import ImageResult, StockProvider, VideoResult
from auto_video.providers.stock.base import MockStockProvider

if TYPE_CHECKING:
    from auto_video.core.visual_keywords import MediaSegment, SegmentInfo

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

    def get_media_for_segments(
        self,
        segments: "list[MediaSegment]",
        output_dir: Path,
        global_keywords: list[str] | None = None,
    ) -> list[Path]:
        """Get media (videos or images) for each MediaSegment.

        For segments with media_type="image", downloads the image and converts
        it to a video using the Ken Burns effect.

        Args:
            segments: List of MediaSegment with text, keywords, duration, and media_type.
            output_dir: Directory to save downloaded clips.
            global_keywords: Optional global keywords to use as fallback.

        Returns:
            List of paths to video clips (one clip per segment).
        """
        logger.info(
            "[StockManager] Starting media search for %d segments (mixed video/image), output_dir: %s",
            len(segments),
            output_dir,
        )

        clips: list[Path] = []
        clip_index = 0

        # Default fallback keywords
        fallback_keywords_tiers = [
            ["politics", "speech", "campaign", "government", "leader"],
            ["business", "office", "meeting", "presentation"],
            ["people", "crowd", "city", "urban"],
            ["nature", "landscape", "technology", "abstract"],
        ]

        for segment_info in segments:
            keywords = segment_info.keywords
            duration = segment_info.duration
            media_type = segment_info.media_type

            logger.debug(
                "[StockManager] Segment %d: %r, keywords=%s, media_type=%s, duration=%.2fs",
                clip_index + 1,
                segment_info.text[:50],
                keywords,
                media_type,
                duration,
            )

            # Build keyword tiers
            keyword_tiers = []

            if keywords:
                clean_keywords = []
                for kw in keywords:
                    kw_clean = kw.replace("\n", " ").replace("\r", " ").strip()
                    if kw_clean and len(kw_clean) > 1:
                        clean_keywords.append(kw_clean)
                if clean_keywords:
                    keyword_tiers.append(clean_keywords)
                    logger.debug("[StockManager] Tier 0 (LLM): %s", clean_keywords)

            if global_keywords:
                clean_global = []
                for kw in global_keywords[:5]:
                    kw_clean = kw.replace("\n", " ").replace("\r", " ").strip()
                    if kw_clean and len(kw_clean) > 1:
                        clean_global.append(kw_clean)
                if clean_global:
                    keyword_tiers.append(clean_global)

            keyword_tiers.extend(fallback_keywords_tiers)

            media_found = False
            for tier_idx, tier_keywords in enumerate(keyword_tiers):
                query = tier_keywords[0]

                logger.debug(
                    "[StockManager] Trying tier %d with query: %r, media_type: %s",
                    tier_idx,
                    query,
                    media_type,
                )

                try:
                    if media_type == "image":
                        clip_path = self._get_image_for_segment(
                            query, duration, output_dir, clip_index
                        )
                        if clip_path:
                            clips.append(clip_path)
                            clip_index += 1
                            tier_name = "LLM" if tier_idx == 0 else ("Global" if tier_idx == 1 else f"Fallback-{tier_idx-1}")
                            logger.info(
                                "✓ Segment %d: %s (%.2fs) using %s keywords: %r [IMAGE]",
                                clip_index,
                                segment_info.text[:40],
                                duration,
                                tier_name,
                                query,
                            )
                            media_found = True
                            break
                    else:  # video
                        clip_path = self._get_video_for_segment(
                            query, duration, output_dir, clip_index
                        )
                        if clip_path:
                            clips.append(clip_path)
                            clip_index += 1
                            tier_name = "LLM" if tier_idx == 0 else ("Global" if tier_idx == 1 else f"Fallback-{tier_idx-1}")
                            logger.info(
                                "✓ Segment %d: %s (%.2fs) using %s keywords: %r [VIDEO]",
                                clip_index,
                                segment_info.text[:40],
                                duration,
                                tier_name,
                                query,
                            )
                            media_found = True
                            break

                except Exception as e:
                    logger.warning("[StockManager] Failed to get media with %r: %s", query, str(e))
                    continue

            if not media_found:
                logger.error(
                    "[StockManager] ✗ FAILED to find ANY media for segment: %r (tried %d keyword tiers)",
                    segment_info.text[:60],
                    len(keyword_tiers),
                )

        logger.info(
            "[StockManager] Complete: downloaded %d media clips for %d segments (%.1f%% coverage)",
            len(clips),
            len(segments),
            100.0 * len(clips) / len(segments) if segments else 0,
        )

        return clips

    def _get_video_for_segment(
        self, query: str, duration: float, output_dir: Path, clip_index: int
    ) -> Path | None:
        """Get a video clip for a segment.

        Args:
            query: Search query.
            duration: Target duration.
            output_dir: Output directory.
            clip_index: Clip index for naming.

        Returns:
            Path to downloaded video, or None if failed.
        """
        try:
            all_results: list[tuple[StockProvider, VideoResult]] = []
            duration_min = max(2, int(duration) - 2)

            for provider in self._providers:
                try:
                    results = provider.search_videos(query, duration_min=duration_min)
                    logger.debug(
                        "[StockManager] %s returned %d video results for %r",
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
                return None

            provider, video_result = self._find_best_matching_clip(all_results, duration)
            output_path = output_dir / f"clip_{clip_index:03d}.mp4"

            downloaded = provider.download_video(video_result.id, output_path, "medium")
            return downloaded

        except Exception as e:
            logger.warning("[StockManager] Failed to get video: %s", str(e))
            return None

    def _get_image_for_segment(
        self, query: str, duration: float, output_dir: Path, clip_index: int
    ) -> Path | None:
        """Get an image and convert it to a video with Ken Burns effect.

        Args:
            query: Search query.
            duration: Target duration.
            output_dir: Output directory.
            clip_index: Clip index for naming.

        Returns:
            Path to generated video, or None if failed.
        """
        temp_dir = Path(tempfile.gettempdir()) / "auto_video_images"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            all_results: list[tuple[StockProvider, ImageResult]] = []

            for provider in self._providers:
                try:
                    results = provider.search_images(query)
                    logger.debug(
                        "[StockManager] %s returned %d image results for %r",
                        provider.__class__.__name__,
                        len(results),
                        query,
                    )
                    all_results.extend([(provider, r) for r in results])
                except Exception as e:
                    logger.debug(
                        "[StockManager] %s image search failed for %r: %s",
                        provider.__class__.__name__,
                        query,
                        e,
                    )
                    continue

            if not all_results:
                return None

            # Select the first image (could add smarter selection later)
            provider, image_result = all_results[0]

            # Download the image
            image_path = temp_dir / f"img_{clip_index:03d}_{image_result.id}.jpg"
            downloaded = provider.download_image(image_result.id, image_path)

            # Convert to video with Ken Burns effect
            video_path = output_dir / f"clip_{clip_index:03d}.mp4"
            self._create_ken_burns_video(downloaded, video_path, duration)

            return video_path

        except Exception as e:
            logger.warning("[StockManager] Failed to get image: %s", str(e))
            return None

    def _create_ken_burns_video(self, image_path: Path, output_path: Path, duration: float) -> None:
        """Convert an image to a video with Ken Burns (pan/zoom) effect.

        Args:
            image_path: Path to the source image.
            output_path: Path where the video should be saved.
            duration: Target video duration in seconds.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Verify image exists
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # First, scale the image to 1920x1080 with padding if needed
        scaled_path = output_path.parent / f"{output_path.stem}_scaled.jpg"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(image_path),
                "-vf",
                "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                "-qscale:v",
                "2",
                str(scaled_path),
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )

        # Create video with simple pan effect using the zoompan filter
        # A simpler approach: slow zoom in from center
        total_frames = int(duration * 30)  # 30 fps

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(scaled_path),
                "-vf",
                f"zoompan=z='min(zoom+0.0015,1.5)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-t",
                str(duration),
                "-pix_fmt",
                "yuv420p",
                "-r",
                "30",
                "-threads",
                "2",
                str(output_path),
            ],
            capture_output=True,
            check=True,
            timeout=120,
        )

        # Clean up scaled image
        scaled_path.unlink(missing_ok=True)

        # Verify the output video was created and has content
        if not output_path.exists() or output_path.stat().st_size < 1000:
            raise ValueError(f"Output video is invalid or empty: {output_path}")

        logger.debug("[StockManager] Ken Burns video created: %s", output_path)


__all__ = ["StockManager", "MockStockProvider"]
