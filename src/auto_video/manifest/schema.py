"""Manifest schema for multi-agent video generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from auto_video.agents.contracts import ContractBaseModel


class TimelineAsset(ContractBaseModel):
    asset_id: str
    path: str
    source: str
    start_s: float
    end_s: float
    role: str
    scene_start_s: float | None = None
    scene_end_s: float | None = None

    @field_validator("asset_id", "path", "source", "role")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("start_s", "end_s")
    @classmethod
    def _validate_time(cls, value: float) -> float:
        if value < 0:
            raise ValueError("time values must be non-negative")
        return value

    @field_validator("end_s")
    @classmethod
    def _validate_range(cls, value: float, info: Any) -> float:
        start_s = info.data.get("start_s")
        if start_s is not None and value < start_s:
            raise ValueError("end_s must be greater than or equal to start_s")
        return value

    @field_validator("scene_start_s", "scene_end_s")
    @classmethod
    def _validate_scene_time(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("scene time values must be non-negative")
        return value

    @field_validator("scene_end_s")
    @classmethod
    def _validate_scene_range(cls, value: float | None, info: Any) -> float | None:
        if value is None:
            return None
        start_s = info.data.get("scene_start_s")
        if start_s is not None and value < start_s:
            raise ValueError("scene_end_s must be greater than or equal to scene_start_s")
        return value


class TimelineScene(ContractBaseModel):
    scene_id: str
    start_s: float
    end_s: float
    narration: str
    subtitles: str
    render_mode: str
    assets: list[TimelineAsset] = Field(default_factory=list)
    effects: list[str] = Field(default_factory=list)
    remotion_source_file: str | None = None
    remotion_composition: str | None = None
    remotion_props: dict[str, Any] = Field(default_factory=dict)
    editable_notes: str = ""

    @field_validator("scene_id", "narration", "subtitles", "render_mode")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("start_s", "end_s")
    @classmethod
    def _validate_time(cls, value: float) -> float:
        if value < 0:
            raise ValueError("time values must be non-negative")
        return value

    @field_validator("end_s")
    @classmethod
    def _validate_range(cls, value: float, info: Any) -> float:
        start_s = info.data.get("start_s")
        if start_s is not None and value < start_s:
            raise ValueError("end_s must be greater than or equal to start_s")
        return value

    @field_validator("editable_notes")
    @classmethod
    def _strip_editable_notes(cls, value: str) -> str:
        return value.strip()

    @field_validator("assets")
    @classmethod
    def _sort_assets(cls, value: list[TimelineAsset]) -> list[TimelineAsset]:
        return sorted(
            value,
            key=lambda asset: (
                asset.scene_start_s if asset.scene_start_s is not None else asset.start_s,
                asset.scene_end_s if asset.scene_end_s is not None else asset.end_s,
                asset.asset_id,
            ),
        )


class VideoManifest(ContractBaseModel):
    video_id: str
    title: str
    language: str
    total_duration_s: float
    scenes: list[TimelineScene]
    workspace_dir: str
    output_video: str | None = None
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    schema_version: str = "1.0"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("video_id", "title", "language", "workspace_dir")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("total_duration_s")
    @classmethod
    def _validate_duration(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("total_duration_s must be positive")
        return value

    @field_validator("scenes")
    @classmethod
    def _validate_scenes(cls, value: list[TimelineScene]) -> list[TimelineScene]:
        if not value:
            raise ValueError("scenes must not be empty")
        return sorted(value, key=lambda scene: scene.start_s)

    @field_validator("output_video")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    def resolve_output_path(self) -> Path | None:
        """Return the output path as a Path object when present."""
        if self.output_video is None:
            return None
        return Path(self.output_video)


__all__ = ["TimelineAsset", "TimelineScene", "VideoManifest"]
