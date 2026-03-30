"""Registry of supported Remotion compositions and defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from auto_video.domain import CompositionRenderSettings, RemotionSpec


@dataclass(frozen=True)
class CompositionDefinition:
    composition_id: str
    default_duration_in_frames: int
    fps: int = 30
    width: int = 1920
    height: int = 1080
    supports_dynamic_duration: bool = False

    def resolve_duration(self, props: dict[str, Any]) -> int:
        if self.composition_id == "ListReveal":
            item_count = max(len(props.get("items", [])), 1)
            return max(90, item_count * 45)
        if self.composition_id == "ComparisonCard":
            return max(105, self.default_duration_in_frames)
        return self.default_duration_in_frames

    def normalize_spec(self, spec: RemotionSpec) -> RemotionSpec:
        duration = spec.render_settings.duration_in_frames or self.resolve_duration(spec.props)
        return spec.model_copy(
            update={
                "render_settings": spec.render_settings.model_copy(
                    update={
                        "fps": spec.render_settings.fps or self.fps,
                        "width": spec.render_settings.width or self.width,
                        "height": spec.render_settings.height or self.height,
                        "duration_in_frames": duration,
                    }
                )
            }
        )


class RemotionRegistry:
    """Central registry for supported Remotion compositions."""

    def __init__(self) -> None:
        self._definitions = {
            definition.composition_id: definition
            for definition in [
                CompositionDefinition("Intro", 90),
                CompositionDefinition("LowerThird", 120),
                CompositionDefinition("CustomTransition", 60),
                CompositionDefinition("DataViz", 180, supports_dynamic_duration=True),
                CompositionDefinition("ListReveal", 120, supports_dynamic_duration=True),
                CompositionDefinition("ComparisonCard", 120, supports_dynamic_duration=True),
            ]
        }

    def get(self, composition_id: str) -> CompositionDefinition:
        if composition_id not in self._definitions:
            raise KeyError(f"Unknown Remotion composition: {composition_id}")
        return self._definitions[composition_id]

    def has(self, composition_id: str) -> bool:
        return composition_id in self._definitions

    def normalize_spec(self, spec: RemotionSpec) -> RemotionSpec:
        return self.get(spec.composition_id).normalize_spec(spec)

    def get_default_duration(self, composition_id: str, props: dict[str, Any] | None = None) -> int:
        definition = self.get(composition_id)
        return definition.resolve_duration(props or {})


_registry: RemotionRegistry | None = None


def get_registry() -> RemotionRegistry:
    global _registry
    if _registry is None:
        _registry = RemotionRegistry()
    return _registry
