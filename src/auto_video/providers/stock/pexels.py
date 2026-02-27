"""Pexels stock footage provider implementation."""

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.core.video import ImageResult, StockProvider, VideoResult

logger = logging.getLogger(__name__)


class PexelsError(Exception):
    pass


class PexelsProvider(StockProvider):
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Pexels API key is required")
        self._api_key = api_key
        self._base_url_videos = "https://api.pexels.com/videos"
        self._base_url_photos = "https://api.pexels.com/v1"
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def download_videos_async(
        self, videos: list[tuple[str, Path, str]], concurrency_limit: int = 5
    ) -> list[Path]:
        async def download_one(video_id: str, output_path: Path, quality: str) -> Path:
            return await asyncio.to_thread(self.download_video, video_id, output_path, quality)

        semaphore = asyncio.Semaphore(concurrency_limit)
        results: list[Path] = []

        async def download_with_semaphore(video_id: str, output_path: Path, quality: str) -> None:
            async with semaphore:
                result = await download_one(video_id, output_path, quality)
                results.append(result)

        tasks = [
            download_with_semaphore(video_id, output_path, quality)
            for video_id, output_path, quality in videos
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def search_videos(self, query: str, duration_min: int) -> list[VideoResult]:
        url = f"{self._base_url_videos}/search"
        headers = {"Authorization": self._api_key}
        params: dict[str, str | int] = {
            "query": query,
            "per_page": 15,
            "orientation": "landscape",
        }

        try:
            response = self._http_client.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            videos: list[VideoResult] = []

            for item in data.get("videos", []):
                video_files = item.get("video_files", [])
                if not video_files:
                    continue

                duration = item.get("duration", 0)
                if duration < duration_min:
                    continue

                selected_file = self._select_best_quality(video_files)
                if not selected_file:
                    continue

                videos.append(
                    VideoResult(
                        id=str(item["id"]),
                        url=selected_file["link"],
                        duration=int(duration),
                        thumbnail=item.get("image", ""),
                        quality=selected_file["quality"],
                    )
                )

            logger.info("Pexels search: query='%s', found=%d videos", query, len(videos))
            return videos
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Pexels rate limit exceeded, retrying...")
                raise
            logger.error("Pexels API error: %s", str(e))
            raise PexelsError(f"Pexels API error: {e}")
        except Exception as e:
            logger.error("Pexels search failed: %s", str(e))
            raise PexelsError(f"Pexels search failed: {e}")

    def _select_best_quality(self, video_files: list[dict[str, Any]]) -> dict[str, Any] | None:
        quality_preference = ["hd", "sd"]
        for pref in quality_preference:
            for file in video_files:
                if file.get("quality") == pref:
                    return file
        return video_files[0] if video_files else None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def download_video(self, video_id: str, output_path: Path, quality: str) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"{self._base_url_videos}/videos/{video_id}"
        headers = {"Authorization": self._api_key}

        try:
            response = self._http_client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            video_files = data.get("video_files", [])
            if not video_files:
                raise PexelsError(f"No video files found for video {video_id}")

            selected_file = self._select_file_by_quality(video_files, quality)
            if not selected_file:
                selected_file = video_files[0]

            video_url = selected_file["link"]
            download_response = self._http_client.get(video_url, timeout=60.0)
            download_response.raise_for_status()

            output_path.write_bytes(download_response.content)

            logger.info(
                "Pexels download: video_id=%s, quality=%s, size=%d bytes",
                video_id,
                selected_file.get("quality", "unknown"),
                len(download_response.content),
            )
            return output_path
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Pexels rate limit exceeded, retrying...")
                raise
            logger.error("Pexels download error: %s", str(e))
            raise PexelsError(f"Pexels download error: {e}")
        except Exception as e:
            logger.error("Pexels download failed: %s", str(e))
            raise PexelsError(f"Pexels download failed: {e}")

    def _select_file_by_quality(
        self, video_files: list[dict[str, Any]], quality: str
    ) -> dict[str, Any] | None:
        quality_map = {"high": "hd", "medium": "sd", "low": "sd"}
        target_quality = quality_map.get(quality.lower(), "hd")
        for file in video_files:
            if file.get("quality") == target_quality:
                return file
        return None

    def health_check(self) -> bool:
        try:
            url = f"{self._base_url_videos}/popular"
            headers = {"Authorization": self._api_key}
            params: dict[str, int] = {"per_page": 1}
            response = self._http_client.get(url, headers=headers, params=params)
            return response.status_code == 200
        except Exception as e:
            logger.error("Pexels health check failed: %s", str(e))
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def search_images(self, query: str) -> list[ImageResult]:
        """Search for photos on Pexels.

        Args:
            query: Search query string.

        Returns:
            List of ImageResult objects.
        """
        url = f"{self._base_url_photos}/search"
        headers = {"Authorization": self._api_key}
        params: dict[str, str | int] = {
            "query": query,
            "per_page": 15,
            "orientation": "landscape",
        }

        try:
            response = self._http_client.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            images: list[ImageResult] = []

            for item in data.get("photos", []):
                # Get the original or large image
                src = item.get("src", {})
                image_url = src.get("original") or src.get("large") or src.get("large2x")
                if not image_url:
                    continue

                images.append(
                    ImageResult(
                        id=str(item["id"]),
                        url=image_url,
                        thumbnail=src.get("large", image_url),
                        width=item.get("width", 1920),
                        height=item.get("height", 1080),
                    )
                )

            logger.info("Pexels image search: query='%s', found=%d images", query, len(images))
            return images
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Pexels rate limit exceeded, retrying...")
                raise
            logger.error("Pexels API error: %s", str(e))
            raise PexelsError(f"Pexels API error: {e}")
        except Exception as e:
            logger.error("Pexels image search failed: %s", str(e))
            raise PexelsError(f"Pexels image search failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def download_image(self, image_id: str, output_path: Path) -> Path:
        """Download an image from Pexels.

        Args:
            image_id: The Pexels image ID.
            output_path: Path where the image should be saved.

        Returns:
            Path to the downloaded image.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"{self._base_url_photos}/photos/{image_id}"
        headers = {"Authorization": self._api_key}

        try:
            response = self._http_client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            src = data.get("src", {})
            image_url = src.get("original") or src.get("large") or src.get("large2x")

            if not image_url:
                raise PexelsError(f"No image URL found for image {image_id}")

            download_response = self._http_client.get(image_url, timeout=60.0)
            download_response.raise_for_status()

            output_path.write_bytes(download_response.content)

            logger.info(
                "Pexels image download: image_id=%s, size=%d bytes",
                image_id,
                len(download_response.content),
            )
            return output_path
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Pexels rate limit exceeded, retrying...")
                raise
            logger.error("Pexels image download error: %s", str(e))
            raise PexelsError(f"Pexels image download error: {e}")
        except Exception as e:
            logger.error("Pexels image download failed: %s", str(e))
            raise PexelsError(f"Pexels image download failed: {e}")
