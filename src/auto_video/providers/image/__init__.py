"""Image generation provider implementations."""

from importlib import import_module
from typing import TYPE_CHECKING

from auto_video.config.schema import ImageGenConfig

if TYPE_CHECKING:
    from auto_video.providers.image.zimage import ZImageProvider


def create_provider(config: ImageGenConfig) -> "ZImageProvider":
    from auto_video.providers.image.zimage import ZImageProvider

    return ZImageProvider(config)


def __getattr__(name: str):
    if name == "ZImageProvider":
        return import_module("auto_video.providers.image.zimage").ZImageProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "create_provider",
    "ZImageProvider",
]
