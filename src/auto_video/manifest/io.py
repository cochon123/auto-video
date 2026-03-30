"""Helpers for reading and writing multi-agent manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auto_video.manifest.schema import VideoManifest


def load_manifest(path: Path | str) -> VideoManifest:
    """Load a manifest from disk."""
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return VideoManifest.model_validate(data)


def save_manifest(manifest: VideoManifest, path: Path | str) -> Path:
    """Save a manifest to disk using stable, human-readable JSON."""
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest.model_dump(mode="json")
    manifest_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def manifest_to_dict(manifest: VideoManifest) -> dict[str, Any]:
    """Serialize a manifest to a JSON-compatible dictionary."""
    return manifest.model_dump(mode="json")


def manifest_from_dict(data: dict[str, Any]) -> VideoManifest:
    """Build a manifest from a dictionary."""
    return VideoManifest.model_validate(data)


__all__ = ["load_manifest", "manifest_from_dict", "manifest_to_dict", "save_manifest"]
