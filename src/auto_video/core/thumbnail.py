"""Thumbnail core module."""

import logging
from pathlib import Path
from typing import Any

from auto_video.config.schema import ImageGenConfig, LLMProviderConfig
from auto_video.core.llm import LLM, load_prompt

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    def __init__(self, config: ImageGenConfig, llm_config: LLMProviderConfig) -> None:
        self.config = config
        self.llm_config = llm_config
        self._llm = LLM(llm_config)
        self._provider: Any = self._create_provider()

    def _create_provider(self) -> Any:
        from auto_video.providers.image import create_provider

        return create_provider(self.config)

    @property
    def provider(self) -> Any:
        return self._provider

    @property
    def llm(self) -> LLM:
        return self._llm

    def generate(self, prompt: str, output_path: Path, size: tuple[int, int] = (1280, 720)) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        width, height = size

        logger.info("Generating thumbnail image: %s", output_path)
        logger.info("Image size: %dx%d", width, height)
        logger.info("Prompt length: %d chars", len(prompt))

        image = self.provider.generate(prompt, width=width, height=height)

        if image is not None:
            try:
                image.save(output_path, format="JPEG", quality=95)
                logger.info("Thumbnail saved successfully: %s", output_path)
            except Exception as e:
                logger.error("Failed to save thumbnail: %s", str(e))
                raise
        else:
            raise RuntimeError("Failed to generate image: provider returned None")

    def generate_from_context(self, title: str, script: str, output_path: Path) -> None:
        logger.info("Generating thumbnail from context")
        logger.info("Title: %s", title)
        logger.info("Script length: %d chars", len(script))

        prompt = self._generate_image_prompt(title, script)

        logger.info("Generated image prompt length: %d chars", len(prompt))

        self.generate(prompt, output_path)

    def _generate_image_prompt(self, title: str, script: str) -> str:
        prompt_template = load_prompt("image.txt")

        script_excerpt = script[:500]
        if len(script) > 500:
            script_excerpt += "..."

        variables = {
            "title": title,
            "script": script_excerpt,
        }

        prompt = prompt_template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{key}}}", value)

        logger.info("Generating image prompt using LLM")

        try:
            image_prompt = self.llm.provider.generate(prompt)
            image_prompt = image_prompt.strip()

            logger.info("Image prompt generated successfully")
            return image_prompt
        except Exception as e:
            logger.error("Failed to generate image prompt: %s", str(e))
            raise

    def cleanup(self) -> None:
        """Cleanup LLM resources and free GPU VRAM."""
        try:
            if self._llm:
                self._llm.cleanup()
                logger.info("Cleaned up ThumbnailGenerator LLM resources")
        except Exception as e:
            logger.warning(f"Error during ThumbnailGenerator cleanup: {str(e)}")

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during garbage collection
