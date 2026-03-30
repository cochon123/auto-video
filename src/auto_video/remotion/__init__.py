"""
Auto-Video Remotion Module.

This module provides integration with Remotion for complex
motion graphics and animations.
"""

from auto_video.remotion.registry import RemotionRegistry, get_registry
from auto_video.remotion.renderer import RemotionRenderer, get_renderer

__all__ = ["RemotionRenderer", "RemotionRegistry", "get_renderer", "get_registry"]
