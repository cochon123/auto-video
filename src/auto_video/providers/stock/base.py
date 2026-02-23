"""Stock provider base classes."""

import logging
from pathlib import Path

from auto_video.core.video import StockProvider, VideoResult

logger = logging.getLogger(__name__)


class MockStockProvider(StockProvider):
    def search_videos(self, query: str, duration_min: int) -> list[VideoResult]:
        mock_results = [
            VideoResult(
                id="mock_001",
                url="https://example.com/mock1.mp4",
                duration=10,
                thumbnail="https://example.com/thumb1.jpg",
                quality="hd",
            ),
            VideoResult(
                id="mock_002",
                url="https://example.com/mock2.mp4",
                duration=15,
                thumbnail="https://example.com/thumb2.jpg",
                quality="hd",
            ),
        ]
        return [r for r in mock_results if r.duration >= duration_min]

    def download_video(self, video_id: str, output_path: Path, quality: str) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"MOCK_VIDEO_DATA")
        logger.info("MockStockProvider: downloaded video %s to %s", video_id, output_path)
        return output_path

    def health_check(self) -> bool:
        return True
