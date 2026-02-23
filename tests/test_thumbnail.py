"""Test thumbnail generator."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from auto_video.config.schema import ImageGenConfig, LLMProviderConfig
from auto_video.core.llm import LLM
from auto_video.core.thumbnail import ThumbnailGenerator
from auto_video.providers.image.zimage import ZImageProvider


def test_thumbnail_generator_initialization():
    image_config = ImageGenConfig(
        enabled=True,
        mode="local",
        model="Z-Image/Z-Image-Turbo",
        steps=6,
    )
    llm_config = LLMProviderConfig(provider="mock", model="test-model")
    generator = ThumbnailGenerator(image_config, llm_config)

    assert generator.config == image_config
    assert generator.llm_config == llm_config
    assert isinstance(generator.llm, LLM)
    assert isinstance(generator.provider, ZImageProvider)


def test_thumbnail_generator_generate_creates_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "thumbnail.jpg"
        image_config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
        llm_config = LLMProviderConfig(provider="mock", model="test-model")
        generator = ThumbnailGenerator(image_config, llm_config)

        generator.generate("A beautiful sunset", output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0


def test_thumbnail_generator_generate_with_custom_size():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "thumbnail_custom.jpg"
        image_config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
        llm_config = LLMProviderConfig(provider="mock", model="test-model")
        generator = ThumbnailGenerator(image_config, llm_config)

        generator.generate("Test prompt", output_path, size=(1920, 1080))

        assert output_path.exists()
        assert output_path.stat().st_size > 0


@patch("auto_video.core.thumbnail.LLM")
def test_thumbnail_generator_generate_from_context_uses_llm(mock_llm_class):
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "thumbnail_from_context.jpg"
        prompt_file = Path(tmpdir) / "image.txt"
        prompt_file.write_text(
            "Generate image for title: {title}, script: {script}", encoding="utf-8"
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "Beautiful mountain landscape"
        mock_llm_instance = MagicMock()
        mock_llm_instance.provider = mock_provider
        mock_llm_class.return_value = mock_llm_instance

        image_config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
        llm_config = LLMProviderConfig(provider="mock", model="test-model")

        with patch("auto_video.core.thumbnail.load_prompt") as mock_load_prompt:
            mock_load_prompt.return_value = "Generate image for title: {title}, script: {script}"
            generator = ThumbnailGenerator(image_config, llm_config)
            generator.generate_from_context("Test Title", "Test script content here", output_path)

        mock_provider.generate.assert_called_once()
        call_args = mock_provider.generate.call_args[0][0]
        assert "Test Title" in call_args or "Test script" in call_args
        assert output_path.exists()


@patch("auto_video.core.thumbnail.LLM")
def test_thumbnail_generator_generate_from_context_uses_title_and_script(mock_llm_class):
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "thumbnail_title_script.jpg"
        prompt_file = Path(tmpdir) / "image.txt"
        prompt_file.write_text(
            "Generate image for title: {title}, script: {script}", encoding="utf-8"
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "Ocean waves at sunset"
        mock_llm_instance = MagicMock()
        mock_llm_instance.provider = mock_provider
        mock_llm_class.return_value = mock_llm_instance

        image_config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
        llm_config = LLMProviderConfig(provider="mock", model="test-model")

        with patch("auto_video.core.thumbnail.load_prompt") as mock_load_prompt:
            mock_load_prompt.return_value = "Generate image for title: {title}, script: {script}"
            generator = ThumbnailGenerator(image_config, llm_config)
            generator.generate_from_context(
                "Mountain Climbing", "This is a longer script about climbing mountains", output_path
            )

        mock_provider.generate.assert_called_once()
        call_args = mock_provider.generate.call_args[0][0]
        assert "Mountain Climbing" in call_args or "This is a longer script" in call_args
        assert output_path.exists()


def test_z_image_provider_initialization():
    config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
    provider = ZImageProvider(config)

    assert provider.config == config
    assert provider._pipeline is None


def test_z_image_provider_generate_creates_image():
    config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
    provider = ZImageProvider(config)

    image = provider.generate("A colorful landscape", width=800, height=600)

    assert image is not None
    assert image.size == (800, 600)


def test_z_image_provider_generate_with_different_sizes():
    config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
    provider = ZImageProvider(config)

    image_small = provider.generate("Small image", width=320, height=240)
    image_large = provider.generate("Large image", width=1920, height=1080)

    assert image_small.size == (320, 240)
    assert image_large.size == (1920, 1080)


@patch("auto_video.providers.image.zimage.DIFFUSERS_AVAILABLE", True)
@patch("auto_video.providers.image.zimage.torch")
@patch("auto_video.providers.image.zimage.DiffusionPipeline")
def test_z_image_provider_health_check_returns_true_when_available(mock_pipeline, mock_torch):
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends = MagicMock()
    mock_torch.backends.mps.is_available.return_value = False
    mock_torch.float32 = "float32"

    mock_pipeline_instance = MagicMock()
    mock_pipeline.from_pretrained.return_value = mock_pipeline_instance
    mock_pipeline_instance.to.return_value = mock_pipeline_instance
    mock_pipeline_instance.enable_attention_slicing.return_value = None

    config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
    provider = ZImageProvider(config)

    result = provider.health_check()

    assert result is True


@patch("auto_video.providers.image.zimage.DIFFUSERS_AVAILABLE", False)
def test_z_image_provider_health_check_returns_false_when_unavailable():
    config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")

    with patch("auto_video.providers.image.zimage.torch", None):
        provider = ZImageProvider(config)

        result = provider.health_check()

        assert result is False


def test_z_image_provider_get_device_detects_cuda():
    with patch("auto_video.providers.image.zimage.DIFFUSERS_AVAILABLE", True):
        with patch("auto_video.providers.image.zimage.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = True

            config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
            provider = ZImageProvider(config)

            assert provider._device == "cuda"


def test_z_image_provider_get_device_detects_cpu():
    with patch("auto_video.providers.image.zimage.DIFFUSERS_AVAILABLE", True):
        with patch("auto_video.providers.image.zimage.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            mock_torch.backends = MagicMock()
            mock_torch.backends.mps.is_available.return_value = False

            config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
            provider = ZImageProvider(config)

            assert provider._device == "cpu"


def test_z_image_provider_mock_mode_generates_images():
    with patch("auto_video.providers.image.zimage.DIFFUSERS_AVAILABLE", False):
        config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
        provider = ZImageProvider(config)

        image = provider.generate("Mock mode image", width=640, height=480)

        assert image is not None
        assert image.size == (640, 480)


def test_z_image_provider_unload_model():
    config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
    provider = ZImageProvider(config)

    provider.unload_model()

    assert provider._pipeline is None


def test_thumbnail_generator_property_access():
    image_config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
    llm_config = LLMProviderConfig(provider="mock", model="test-model")
    generator = ThumbnailGenerator(image_config, llm_config)

    assert isinstance(generator.provider, ZImageProvider)
    assert isinstance(generator.llm, LLM)


def test_z_image_provider_pipeline_property():
    with patch("auto_video.providers.image.zimage.DIFFUSERS_AVAILABLE", False):
        config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
        provider = ZImageProvider(config)

        with pytest.raises(ImportError):
            _ = provider.pipeline


def test_thumbnail_generator_generate_creates_parent_directories():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "subdir" / "nested" / "thumbnail.jpg"
        image_config = ImageGenConfig(enabled=True, mode="local", model="Z-Image/Z-Image-Turbo")
        llm_config = LLMProviderConfig(provider="mock", model="test-model")
        generator = ThumbnailGenerator(image_config, llm_config)

        generator.generate("Test", output_path)

        assert output_path.exists()
        assert output_path.parent.exists()
