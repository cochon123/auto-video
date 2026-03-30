"""Base classes for stock media providers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class VideoResult:
    """Result from searching stock videos."""

    id: str
    url: str
    duration: int
    thumbnail: str
    quality: str


@dataclass
class ImageResult:
    """Result from searching stock images."""

    id: str
    url: str
    thumbnail: str
    width: int
    height: int


@dataclass
class Asset:
    """Local asset file."""

    path: Path
    type: str  # "video" or "image"
    duration: float | None


class StockProvider(ABC):
    """Abstract base class for stock media providers."""

    @abstractmethod
    def search_videos(self, query: str, duration_min: int) -> list[VideoResult]:
        """Search for videos matching the query.

        Args:
            query: Search query string
            duration_min: Minimum duration in seconds

        Returns:
            List of video results
        """
        ...

    @abstractmethod
    def download_video(self, video_id: str, output_path: Path, quality: str) -> Path:
        """Download a video by ID.

        Args:
            video_id: Video identifier
            output_path: Where to save the video
            quality: Quality setting (low, medium, high)

        Returns:
            Path to downloaded video
        """
        ...

    @abstractmethod
    def search_images(self, query: str) -> list[ImageResult]:
        """Search for images matching the query.

        Args:
            query: Search query string

        Returns:
            List of image results
        """
        ...

    @abstractmethod
    def download_image(self, image_id: str, output_path: Path) -> Path:
        """Download an image by ID.

        Args:
            image_id: Image identifier
            output_path: Where to save the image

        Returns:
            Path to downloaded image
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is accessible.

        Returns:
            True if provider is working, False otherwise
        """
        ...


__all__ = ["VideoResult", "ImageResult", "Asset", "StockProvider"]
