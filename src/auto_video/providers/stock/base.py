"""Stock provider base classes."""

import logging
import subprocess
import tempfile
from pathlib import Path

from auto_video.core.video import ImageResult, StockProvider, VideoResult

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
        # Create a valid minimal video using ffmpeg
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=blue:s=1920x1080:d=5",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                    "-t",
                    "5",
                    "-y",
                    str(output_path),
                ],
                capture_output=True,
                timeout=30,
            )
            logger.info("MockStockProvider: created mock video %s", output_path)
        except Exception as e:
            logger.warning("MockStockProvider: failed to create mock video, using fallback: %s", e)
            output_path.write_bytes(b"MOCK_VIDEO_DATA")
        return output_path

    def search_images(self, query: str) -> list[ImageResult]:
        mock_results = [
            ImageResult(
                id="mock_img_001",
                url="https://example.com/mock_img1.jpg",
                thumbnail="https://example.com/thumb_img1.jpg",
                width=1920,
                height=1080,
            ),
            ImageResult(
                id="mock_img_002",
                url="https://example.com/mock_img2.jpg",
                thumbnail="https://example.com/thumb_img2.jpg",
                width=1920,
                height=1080,
            ),
        ]
        return mock_results

    def download_image(self, image_id: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Create a valid minimal image using ffmpeg
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=green:s=1920x1080:d=1",
                    "-vframes",
                    "1",
                    "-qscale:v",
                    "2",
                    "-y",
                    str(output_path),
                ],
                capture_output=True,
                timeout=30,
            )
            logger.info("MockStockProvider: created mock image %s", output_path)
        except Exception as e:
            logger.warning("MockStockProvider: failed to create mock image: %s", e)
            # Create a minimal valid JPEG using PIL if available, otherwise use a simple pattern
            try:
                from PIL import Image

                img = Image.new("RGB", (1920, 1080), color=(0, 128, 0))
                img.save(output_path, "JPEG", quality=95)
                logger.info("MockStockProvider: created PIL mock image %s", output_path)
            except ImportError:
                # Fallback: write a very simple valid JPEG header + data
                # This is a minimal 1x1 green JPEG
                jpeg_data = bytes([
                    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
                    0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
                    0x00, 0x03, 0x02, 0x02, 0x03, 0x02, 0x02, 0x03, 0x03, 0x03, 0x03, 0x04,
                    0x03, 0x03, 0x04, 0x05, 0x08, 0x05, 0x05, 0x04, 0x04, 0x05, 0x0A, 0x07,
                    0x07, 0x06, 0x08, 0x0C, 0x0A, 0x0C, 0x0C, 0x0B, 0x0A, 0x0B, 0x0B, 0x0D,
                    0x0E, 0x12, 0x10, 0x0D, 0x0E, 0x11, 0x0E, 0x0B, 0x0B, 0x10, 0x16, 0x10,
                    0x11, 0x13, 0x14, 0x15, 0x15, 0x15, 0x0C, 0x0F, 0x17, 0x18, 0x16, 0x14,
                    0x18, 0x12, 0x14, 0x15, 0x14, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
                    0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01,
                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x09, 0xFF, 0xC4, 0x00, 0x14, 0x10, 0x01, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00,
                    0x37, 0xFF, 0xD9
                ])
                output_path.write_bytes(jpeg_data)
                logger.info("MockStockProvider: created minimal mock JPEG %s", output_path)
        return output_path

    def health_check(self) -> bool:
        return True
