"""Image generation provider implementations."""

from typing import TYPE_CHECKING

from auto_video.config.schema import ImageGenConfig

if TYPE_CHECKING:
    from auto_video.providers.image.zimage import ZImageProvider


def create_provider(config: ImageGenConfig) -> "ZImageProvider":
    from auto_video.providers.image.zimage import ZImageProvider

    return ZImageProvider(config)


__all__ = [
    "create_provider",
    "ZImageProvider",
]
