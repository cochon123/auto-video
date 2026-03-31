"""DuckDuckGo images provider implementation."""

import logging
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.core.video import ImageResult, StockProvider, VideoResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DuckDuckGoError(Exception):
    pass


class DuckDuckGoProvider(StockProvider):
    def __init__(self) -> None:
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        logger.info("[DuckDuckGo] Provider initialized")

    def search_videos(self, query: str, duration_min: int) -> list[VideoResult]:
        raise NotImplementedError("DuckDuckGo does not support video search")

    def download_video(self, video_id: str, output_path: Path, quality: str) -> Path:
        raise NotImplementedError("DuckDuckGo does not support video download")

    def search_images(self, query: str) -> list[ImageResult]:
        """Search for images using DuckDuckGo.

        Args:
            query: Search query string.

        Returns:
            List of ImageResult objects.

        Raises:
            DuckDuckGoError: If the search fails.
        """
        try:
            from ddgs import DDGS
        except ImportError:
            logger.warning(
                "[DuckDuckGo] Optional dependency missing. Install auto-video[visual-search] to enable it."
            )
            return []

        try:

            logger.debug("[DuckDuckGo] Searching images with query: %s", query)

            with DDGS() as ddgs:
                results = ddgs.images(
                    keywords=query,
                    region="us-en",
                    safesearch="moderate",
                    max_results=15,
                    layout="Wide",
                    type_image="photo",
                )

                if not results:
                    logger.debug("[DuckDuckGo] No results found for query: %s", query)
                    return []

                image_results: list[ImageResult] = []
                for idx, result in enumerate(results):
                    image_url = result.get("image")
                    if not image_url:
                        continue

                    image_results.append(
                        ImageResult(
                            id=image_url,
                            url=image_url,
                            thumbnail=result.get("thumbnail", image_url),
                            width=result.get("width", 0),
                            height=result.get("height", 0),
                        )
                    )

                logger.info("[DuckDuckGo] Found %d images for query: %s", len(image_results), query)
                return image_results

        except Exception as e:
            logger.error("[DuckDuckGo] Search failed for query %s: %s", query, str(e))
            raise DuckDuckGoError(f"DuckDuckGo search failed: {str(e)}") from e

    def download_image(self, image_id: str, output_path: Path) -> Path:
        """Download an image from DuckDuckGo URL.

        Args:
            image_id: The image URL (stored as ID).
            output_path: Path where the image should be saved.

        Returns:
            Path to the downloaded image.

        Raises:
            DuckDuckGoError: If download fails.
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            logger.debug("[DuckDuckGo] Downloading image to: %s", output_path)

            response = self._http_client.get(image_id, follow_redirects=True, timeout=30.0)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            extension = mimetypes.guess_extension(content_type.split(";")[0]) or ".jpg"

            if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
                extension = ".jpg"

            final_path = output_path.with_suffix(extension)

            final_path.write_bytes(response.content)
            logger.info(
                "[DuckDuckGo] Downloaded image: %s (size: %d bytes)",
                final_path,
                len(response.content),
            )

            return final_path

        except httpx.HTTPError as e:
            logger.error("[DuckDuckGo] HTTP error downloading image: %s", str(e))
            raise DuckDuckGoError(f"HTTP error: {str(e)}") from e
        except Exception as e:
            logger.error("[DuckDuckGo] Failed to download image: %s", str(e))
            raise DuckDuckGoError(f"Download failed: {str(e)}") from e

    def health_check(self) -> bool:
        """Check if DuckDuckGo service is available.

        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.images("test", max_results=1))
                return len(results) > 0
        except Exception as e:
            logger.warning("[DuckDuckGo] Health check failed: %s", str(e))
            return False

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        try:
            self._http_client.close()
        except Exception:
            pass
