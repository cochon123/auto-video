"""Test stock footage providers."""

from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest

from auto_video.config.schema import VisualsConfig
from auto_video.core.video import StockProvider
from auto_video.providers.stock import StockManager
from auto_video.providers.stock.base import MockStockProvider
from auto_video.providers.stock.pexels import PexelsProvider
from auto_video.providers.stock.pixabay import PixabayProvider


@pytest.fixture
def pexels_api_key() -> str:
    return "test-pexels-api-key"


@pytest.fixture
def pixabay_api_key() -> str:
    return "test-pixabay-api-key"


@pytest.fixture
def visuals_config_pexels(pexels_api_key: str) -> VisualsConfig:
    return VisualsConfig(
        mode="stock",
        providers=["pexels"],
        pexels_api_key=pexels_api_key,
    )


@pytest.fixture
def visuals_config_pixabay(pixabay_api_key: str) -> VisualsConfig:
    return VisualsConfig(
        mode="stock",
        providers=["pixabay"],
        pixabay_api_key=pixabay_api_key,
    )


@pytest.fixture
def visuals_config_both(pexels_api_key: str, pixabay_api_key: str) -> VisualsConfig:
    return VisualsConfig(
        mode="stock",
        providers=["pexels", "pixabay"],
        pexels_api_key=pexels_api_key,
        pixabay_api_key=pixabay_api_key,
    )


class TestStockProvider:
    def test_stock_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            StockProvider()


class TestPexelsProvider:
    def test_init_with_valid_config(self, pexels_api_key: str) -> None:
        provider = PexelsProvider(pexels_api_key)

        assert provider._api_key == pexels_api_key
        assert provider._base_url == "https://api.pexels.com/videos"

    def test_init_with_no_api_key_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Pexels API key is required"):
            PexelsProvider("")

    def test_search_videos_returns_results(self, pexels_api_key: str) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "videos": [
                {
                    "id": 1,
                    "duration": 10,
                    "image": "https://example.com/thumb1.jpg",
                    "video_files": [
                        {"quality": "hd", "link": "https://example.com/video1_hd.mp4"},
                        {"quality": "sd", "link": "https://example.com/video1_sd.mp4"},
                    ],
                }
            ]
        }

        with patch("httpx.get") as mock_get:
            mock_get.return_value = mock_response

            provider = PexelsProvider(pexels_api_key)
            results = provider.search_videos("nature", 5)

        assert len(results) == 1
        assert results[0].id == "1"
        assert results[0].url == "https://example.com/video1_hd.mp4"
        assert results[0].duration == 10

    def test_search_videos_filters_by_duration(self, pexels_api_key: str) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "videos": [
                {
                    "id": 1,
                    "duration": 5,
                    "image": "https://example.com/thumb1.jpg",
                    "video_files": [{"quality": "hd", "link": "https://example.com/video1.mp4"}],
                },
                {
                    "id": 2,
                    "duration": 15,
                    "image": "https://example.com/thumb2.jpg",
                    "video_files": [{"quality": "hd", "link": "https://example.com/video2.mp4"}],
                },
            ]
        }

        with patch("httpx.get") as mock_get:
            mock_get.return_value = mock_response

            provider = PexelsProvider(pexels_api_key)
            results = provider.search_videos("nature", 10)

        assert len(results) == 1
        assert results[0].id == "2"
        assert results[0].duration == 15

    def test_search_videos_handles_empty_results(self, pexels_api_key: str) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"videos": []}

        with patch("httpx.get") as mock_get:
            mock_get.return_value = mock_response

            provider = PexelsProvider(pexels_api_key)
            results = provider.search_videos("nonexistent", 5)

        assert len(results) == 0

    def test_download_video_downloads_file(self, pexels_api_key: str, tmp_path: Path) -> None:
        mock_video_response = Mock()
        mock_video_response.status_code = 200
        mock_video_response.content = b"MOCK_VIDEO_DATA"

        mock_detail_response = Mock()
        mock_detail_response.status_code = 200
        mock_detail_response.json.return_value = {
            "id": 1,
            "video_files": [{"quality": "hd", "link": "https://example.com/video.mp4"}],
        }

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [mock_detail_response, mock_video_response]

            provider = PexelsProvider(pexels_api_key)
            output_path = tmp_path / "output.mp4"
            result = provider.download_video("1", output_path, "high")

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == b"MOCK_VIDEO_DATA"

    def test_download_video_handles_quality_selection(
        self, pexels_api_key: str, tmp_path: Path
    ) -> None:
        mock_video_response = Mock()
        mock_video_response.status_code = 200
        mock_video_response.content = b"MOCK_VIDEO_DATA"

        mock_detail_response = Mock()
        mock_detail_response.status_code = 200
        mock_detail_response.json.return_value = {
            "id": 1,
            "video_files": [
                {"quality": "hd", "link": "https://example.com/video_hd.mp4"},
                {"quality": "sd", "link": "https://example.com/video_sd.mp4"},
            ],
        }

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [mock_detail_response, mock_video_response]

            provider = PexelsProvider(pexels_api_key)
            output_path = tmp_path / "output.mp4"
            provider.download_video("1", output_path, "low")

        assert mock_get.call_count == 2

    def test_health_check_returns_true_on_success(self, pexels_api_key: str) -> None:
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.get") as mock_get:
            mock_get.return_value = mock_response

            provider = PexelsProvider(pexels_api_key)
            result = provider.health_check()

        assert result is True

    def test_health_check_returns_false_on_failure(self, pexels_api_key: str) -> None:
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection failed")

            provider = PexelsProvider(pexels_api_key)
            result = provider.health_check()

        assert result is False

    def test_retry_on_rate_limit(self, pexels_api_key: str) -> None:
        mock_response_error = Mock()
        mock_response_error.status_code = 429
        mock_response_error.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit", request=Mock(), response=mock_response_error
        )

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "videos": [
                {
                    "id": 1,
                    "duration": 10,
                    "image": "https://example.com/thumb1.jpg",
                    "video_files": [{"quality": "hd", "link": "https://example.com/video1.mp4"}],
                }
            ]
        }

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [mock_response_error, mock_response_success]

            provider = PexelsProvider(pexels_api_key)
            results = provider.search_videos("nature", 5)

        assert len(results) == 1


class TestPixabayProvider:
    def test_init_with_valid_config(self, pixabay_api_key: str) -> None:
        provider = PixabayProvider(pixabay_api_key)

        assert provider._api_key == pixabay_api_key
        assert provider._base_url == "https://pixabay.com/api/videos/"

    def test_init_with_no_api_key_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Pixabay API key is required"):
            PixabayProvider("")

    def test_search_videos_returns_results(self, pixabay_api_key: str) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "id": 1,
                    "duration": 10,
                    "picture_id": "pic1",
                    "videos/large": {"url": "https://example.com/video1_large.mp4"},
                    "videos/medium": {"url": "https://example.com/video1_medium.mp4"},
                }
            ]
        }

        with patch("httpx.get") as mock_get:
            mock_get.return_value = mock_response

            provider = PixabayProvider(pixabay_api_key)
            results = provider.search_videos("nature", 5)

        assert len(results) == 1
        assert results[0].id == "1"
        assert results[0].url == "https://example.com/video1_large.mp4"
        assert results[0].duration == 10

    def test_search_videos_filters_by_duration(self, pixabay_api_key: str) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "id": 1,
                    "duration": 5,
                    "picture_id": "pic1",
                    "videos/large": {"url": "https://example.com/video1.mp4"},
                },
                {
                    "id": 2,
                    "duration": 15,
                    "picture_id": "pic2",
                    "videos/large": {"url": "https://example.com/video2.mp4"},
                },
            ]
        }

        with patch("httpx.get") as mock_get:
            mock_get.return_value = mock_response

            provider = PixabayProvider(pixabay_api_key)
            results = provider.search_videos("nature", 10)

        assert len(results) == 1
        assert results[0].id == "2"
        assert results[0].duration == 15

    def test_search_videos_handles_empty_results(self, pixabay_api_key: str) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": []}

        with patch("httpx.get") as mock_get:
            mock_get.return_value = mock_response

            provider = PixabayProvider(pixabay_api_key)
            results = provider.search_videos("nonexistent", 5)

        assert len(results) == 0

    def test_download_video_downloads_file(self, pixabay_api_key: str, tmp_path: Path) -> None:
        mock_video_response = Mock()
        mock_video_response.status_code = 200
        mock_video_response.content = b"MOCK_VIDEO_DATA"

        mock_detail_response = Mock()
        mock_detail_response.status_code = 200
        mock_detail_response.json.return_value = {
            "hits": [
                {
                    "id": 1,
                    "videos/large": {"url": "https://example.com/video_large.mp4"},
                    "videos/medium": {"url": "https://example.com/video_medium.mp4"},
                }
            ]
        }

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [mock_detail_response, mock_video_response]

            provider = PixabayProvider(pixabay_api_key)
            output_path = tmp_path / "output.mp4"
            result = provider.download_video("1", output_path, "high")

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == b"MOCK_VIDEO_DATA"

    def test_health_check_returns_true_on_success(self, pixabay_api_key: str) -> None:
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.get") as mock_get:
            mock_get.return_value = mock_response

            provider = PixabayProvider(pixabay_api_key)
            result = provider.health_check()

        assert result is True

    def test_retry_on_rate_limit(self, pixabay_api_key: str) -> None:
        mock_response_error = Mock()
        mock_response_error.status_code = 429
        mock_response_error.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit", request=Mock(), response=mock_response_error
        )

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "hits": [
                {
                    "id": 1,
                    "duration": 10,
                    "picture_id": "pic1",
                    "videos/large": {"url": "https://example.com/video1.mp4"},
                }
            ]
        }

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [mock_response_error, mock_response_success]

            provider = PixabayProvider(pixabay_api_key)
            results = provider.search_videos("nature", 5)

        assert len(results) == 1


class TestStockManager:
    def test_initialization_with_providers(self, visuals_config_pexels: VisualsConfig) -> None:
        manager = StockManager(visuals_config_pexels)

        assert len(manager._providers) == 1
        assert isinstance(manager._providers[0], PexelsProvider)

    def test_initialization_with_both_providers(self, visuals_config_both: VisualsConfig) -> None:
        manager = StockManager(visuals_config_both)

        assert len(manager._providers) == 2
        assert isinstance(manager._providers[0], PexelsProvider)
        assert isinstance(manager._providers[1], PixabayProvider)

    def test_initialization_fallback_to_mock_provider(self) -> None:
        config = VisualsConfig(mode="stock", providers=[])
        manager = StockManager(config)

        assert len(manager._providers) == 1
        assert isinstance(manager._providers[0], MockStockProvider)

    def test_get_clips_for_script_returns_clips(
        self, visuals_config_pexels: VisualsConfig, tmp_path: Path
    ) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "videos": [
                {
                    "id": 1,
                    "duration": 10,
                    "image": "https://example.com/thumb1.jpg",
                    "video_files": [{"quality": "hd", "link": "https://example.com/video1.mp4"}],
                }
            ]
        }

        mock_video_response = Mock()
        mock_video_response.status_code = 200
        mock_video_response.content = b"MOCK_VIDEO_DATA"

        mock_detail_response = Mock()
        mock_detail_response.status_code = 200
        mock_detail_response.json.return_value = {
            "id": 1,
            "video_files": [{"quality": "hd", "link": "https://example.com/video1.mp4"}],
        }

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [mock_response, mock_detail_response, mock_video_response]

            manager = StockManager(visuals_config_pexels)
            clips = manager.get_clips_for_script("Test script", [], 10, tmp_path)

        assert len(clips) == 1
        assert clips[0].exists()

    def test_get_clips_for_script_uses_keywords(
        self, visuals_config_pexels: VisualsConfig, tmp_path: Path
    ) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "videos": [
                {
                    "id": 1,
                    "duration": 10,
                    "image": "https://example.com/thumb1.jpg",
                    "video_files": [{"quality": "hd", "link": "https://example.com/video1.mp4"}],
                }
            ]
        }

        mock_video_response = Mock()
        mock_video_response.status_code = 200
        mock_video_response.content = b"MOCK_VIDEO_DATA"

        mock_detail_response = Mock()
        mock_detail_response.status_code = 200
        mock_detail_response.json.return_value = {
            "id": 1,
            "video_files": [{"quality": "hd", "link": "https://example.com/video1.mp4"}],
        }

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [mock_response, mock_detail_response, mock_video_response]

            manager = StockManager(visuals_config_pexels)
            clips = manager.get_clips_for_script(
                "Test script", ["nature", "landscape"], 10, tmp_path
            )

        assert len(clips) == 1
        assert clips[0].exists()

    def test_extract_keywords_from_script_works(self, visuals_config_pexels: VisualsConfig) -> None:
        manager = StockManager(visuals_config_pexels)

        script = "La nature est belle dans le paysage"
        keyword = manager._extract_keywords_from_script(script)

        assert keyword == "nature"

    def test_extract_keywords_from_script_with_short_words(
        self, visuals_config_pexels: VisualsConfig
    ) -> None:
        manager = StockManager(visuals_config_pexels)

        script = "Le chat est dans la maison"
        keyword = manager._extract_keywords_from_script(script)

        assert keyword == "maison"

    def test_extract_keywords_from_script_no_keywords(
        self, visuals_config_pexels: VisualsConfig
    ) -> None:
        manager = StockManager(visuals_config_pexels)

        script = "Le un et la"
        keyword = manager._extract_keywords_from_script(script)

        assert keyword == "video"
