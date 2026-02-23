"""Z-Image provider implementation."""

import logging

from auto_video.config.schema import ImageGenConfig

logger = logging.getLogger(__name__)

try:
    import torch
    from diffusers import DiffusionPipeline  # type: ignore[import-not-found]

    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    logger.warning("diffusers or torch not available, using mock mode")
    DiffusionPipeline = object  # type: ignore[misc,assignment]
    torch = None  # type: ignore[assignment]

try:
    from PIL import Image, ImageFont

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("PIL not available, image operations limited")
    Image = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]


class ZImageProvider:
    def __init__(self, config: ImageGenConfig) -> None:
        self.config = config
        self._pipeline: DiffusionPipeline | None = None
        self._device = self._get_device()

    def _get_device(self) -> str:
        if not DIFFUSERS_AVAILABLE:
            return "cpu"
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    @property
    def pipeline(self) -> DiffusionPipeline:
        if self._pipeline is None:
            self._pipeline = self._load_model()
        return self._pipeline

    def _load_model(self) -> DiffusionPipeline:
        if not DIFFUSERS_AVAILABLE:
            raise ImportError("diffusers and torch are required for Z-Image")

        logger.info("Loading Z-Image model: %s", self.config.model)
        logger.info("Using device: %s", self._device)

        pipeline = DiffusionPipeline.from_pretrained(
            self.config.model,
            torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
        )

        if self._device != "cpu":
            pipeline = pipeline.to(self._device)

        if self.config.lora:
            logger.info("Loading LoRA: %s", self.config.lora)
            pipeline.load_lora_weights(self.config.lora)

        if self._device == "cuda":
            try:
                pipeline.enable_attention_slicing()
            except Exception as e:
                logger.warning("Could not enable attention slicing: %s", e)

        return pipeline

    def generate(self, prompt: str, width: int = 1280, height: int = 720) -> "Image.Image | None":
        if not DIFFUSERS_AVAILABLE or not PILLOW_AVAILABLE:
            logger.warning("Image generation not available, returning mock image")
            return self._create_mock_image(prompt, width, height)

        logger.info("Generating image with prompt (length=%d)", len(prompt))

        try:
            steps = self.config.steps
            image = self.pipeline(
                prompt,
                num_inference_steps=steps,
                guidance_scale=7.5,
                height=height,
                width=width,
            ).images[0]

            logger.info("Image generated successfully")
            return image
        except Exception as e:
            logger.error("Failed to generate image: %s", str(e))
            return self._create_mock_image(prompt, width, height)

    def _create_mock_image(self, prompt: str, width: int, height: int) -> "Image.Image | None":
        if not PILLOW_AVAILABLE or Image is None:
            return None

        from PIL import ImageDraw

        image = Image.new("RGB", (width, height), color="#3b82f6")
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        except Exception:
            font = ImageFont.load_default()

        text = "MOCK IMAGE\n\n" + prompt[:100]
        if len(prompt) > 100:
            text += "..."

        lines = text.split("\n")
        y_offset = 50
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            draw.text((x, y_offset), line, fill="white", font=font)
            y_offset += text_height + 10

        return image

    def health_check(self) -> bool:
        if not DIFFUSERS_AVAILABLE:
            logger.info("Z-Image not available (diffusers not installed)")
            return False
        try:
            _ = self.pipeline
            return True
        except Exception as e:
            logger.error("Z-Image health check failed: %s", str(e))
            return False

    def unload_model(self) -> None:
        if self._pipeline is not None:
            if self._device == "cuda":
                self._pipeline.to("cpu")
            del self._pipeline
            self._pipeline = None
            if self._device == "cuda":
                torch.cuda.empty_cache()
            logger.info("Z-Image model unloaded")
