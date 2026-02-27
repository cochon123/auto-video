"""Pixabay stock footage provider implementation."""

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.core.video import ImageResult, StockProvider, VideoResult

logger = logging.getLogger(__name__)


class PixabayError(Exception):
    pass


class PixabayProvider(StockProvider):
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Pixabay API key is required")
        self._api_key = api_key
        self._base_url = "https://pixabay.com/api/videos/"
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
        url = self._base_url
        params: dict[str, str | int] = {
            "key": self._api_key,
            "q": query,
            "per_page": 15,
            "video_type": "film",
            "orientation": "horizontal",
        }

        try:
            response = self._http_client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            videos: list[VideoResult] = []

            for item in data.get("hits", []):
                duration = item.get("duration", 0)
                if duration < duration_min:
                    continue

                selected_url = self._select_best_video_url(item)
                if not selected_url:
                    continue

                videos.append(
                    VideoResult(
                        id=str(item["id"]),
                        url=selected_url["url"],
                        duration=int(duration),
                        thumbnail=item.get("picture_id", ""),
                        quality=selected_url["quality"],
                    )
                )

            logger.info("Pixabay search: query='%s', found=%d videos", query, len(videos))
            return videos
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Pixabay rate limit exceeded, retrying...")
                raise
            logger.error("Pixabay API error: %s", str(e))
            raise PixabayError(f"Pixabay API error: {e}")
        except Exception as e:
            logger.error("Pixabay search failed: %s", str(e))
            raise PixabayError(f"Pixabay search failed: {e}")

    def _select_best_video_url(self, item: dict[str, Any]) -> dict[str, str] | None:
        size_preference = ["large", "medium", "small"]
        for size in size_preference:
            video_key = f"videos/{size}"
            if video_key in item:
                video_obj = item[video_key]
                video_url = video_obj.get("url")
                if isinstance(video_url, str):
                    return {"url": video_url, "quality": size}
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def download_video(self, video_id: str, output_path: Path, quality: str) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        url = self._base_url
        params: dict[str, str] = {"key": self._api_key, "id": video_id}

        try:
            response = self._http_client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            hits = data.get("hits", [])
            if not hits:
                raise PixabayError(f"Video {video_id} not found")

            item = hits[0]
            video_url = self._select_video_url_by_quality(item, quality)

            if not video_url:
                raise PixabayError(
                    f"No suitable video found for video {video_id} with quality {quality}"
                )

            download_response = self._http_client.get(video_url, timeout=60.0)
            download_response.raise_for_status()

            output_path.write_bytes(download_response.content)

            logger.info(
                "Pixabay download: video_id=%s, quality=%s, size=%d bytes",
                video_id,
                quality,
                len(download_response.content),
            )
            return output_path
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Pixabay rate limit exceeded, retrying...")
                raise
            logger.error("Pixabay download error: %s", str(e))
            raise PixabayError(f"Pixabay download error: {e}")
        except Exception as e:
            logger.error("Pixabay download failed: %s", str(e))
            raise PixabayError(f"Pixabay download failed: {e}")

    def _select_video_url_by_quality(self, item: dict[str, Any], quality: str) -> str | None:
        quality_map = {"high": "large", "medium": "medium", "low": "small"}
        target_size = quality_map.get(quality.lower(), "large")
        video_key = f"videos/{target_size}"
        if video_key in item:
            video_obj = item[video_key]
            url = video_obj.get("url")
            if isinstance(url, str):
                return url
        for size in ["large", "medium", "small"]:
            video_key = f"videos/{size}"
            if video_key in item:
                video_obj = item[video_key]
                url = video_obj.get("url")
                if isinstance(url, str):
                    return url
        return None

    def health_check(self) -> bool:
        try:
            url = self._base_url
            params: dict[str, str | int] = {"key": self._api_key, "per_page": 1}
            response = self._http_client.get(url, params=params)
            return response.status_code == 200
        except Exception as e:
            logger.error("Pixabay health check failed: %s", str(e))
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def search_images(self, query: str) -> list[ImageResult]:
        """Search for photos on Pixabay.

        Args:
            query: Search query string.

        Returns:
            List of ImageResult objects.
        """
        url = self._base_url
        params: dict[str, str | int] = {
            "key": self._api_key,
            "q": query,
            "per_page": 15,
            "image_type": "photo",
            "orientation": "horizontal",
            "safesearch": "true",
        }

        try:
            response = self._http_client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            images: list[ImageResult] = []

            for item in data.get("hits", []):
                # Use webformatURL or largeImageURL
                image_url = (
                    item.get("webformatURL")
                    or item.get("largeImageURL")
                    or item.get("fullHDURL")
                )
                if not image_url:
                    continue

                images.append(
                    ImageResult(
                        id=str(item["id"]),
                        url=image_url,
                        thumbnail=item.get("previewURL", image_url),
                        width=item.get("imageWidth", 1920),
                        height=item.get("imageHeight", 1080),
                    )
                )

            logger.info("Pixabay image search: query='%s', found=%d images", query, len(images))
            return images
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Pixabay rate limit exceeded, retrying...")
                raise
            logger.error("Pixabay API error: %s", str(e))
            raise PixabayError(f"Pixabay API error: {e}")
        except Exception as e:
            logger.error("Pixabay image search failed: %s", str(e))
            raise PixabayError(f"Pixabay image search failed: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def download_image(self, image_id: str, output_path: Path) -> Path:
        """Download an image from Pixabay.

        Args:
            image_id: The Pixabay image ID.
            output_path: Path where the image should be saved.

        Returns:
            Path to the downloaded image.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        url = self._base_url
        params: dict[str, str] = {"key": self._api_key, "id": image_id}

        try:
            response = self._http_client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            hits = data.get("hits", [])
            if not hits:
                raise PixabayError(f"Image {image_id} not found")

            item = hits[0]
            image_url = (
                item.get("webformatURL")
                or item.get("largeImageURL")
                or item.get("fullHDURL")
            )

            if not image_url:
                raise PixabayError(f"No suitable image URL found for image {image_id}")

            download_response = self._http_client.get(image_url, timeout=60.0)
            download_response.raise_for_status()

            output_path.write_bytes(download_response.content)

            logger.info(
                "Pixabay image download: image_id=%s, size=%d bytes",
                image_id,
                len(download_response.content),
            )
            return output_path
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Pixabay rate limit exceeded, retrying...")
                raise
            logger.error("Pixabay image download error: %s", str(e))
            raise PixabayError(f"Pixabay image download error: {e}")
        except Exception as e:
            logger.error("Pixabay image download failed: %s", str(e))
            raise PixabayError(f"Pixabay image download failed: {e}")
