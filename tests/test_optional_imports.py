"""Tests for optional dependency boundaries."""

import importlib
import sys

from auto_video.config.schema import TTSConfig
from auto_video.core.llm import load_prompt
from auto_video.core.tts import MockTTSProvider
from auto_video.providers.tts import create_provider


def test_load_prompt_reads_packaged_prompt() -> None:
    """Packaged prompts should be available without repo-relative paths."""
    prompt = load_prompt("general.txt")

    assert "You are a skilled YouTuber" in prompt


def test_local_tts_falls_back_to_mock_provider() -> None:
    """Local TTS config should not require Kokoro to be installed."""
    provider = create_provider(TTSConfig(mode="local", provider="mock"))

    assert isinstance(provider, MockTTSProvider)


def test_optional_packages_import_without_youtube_sdk(monkeypatch) -> None:
    """Importing upload/pipeline modules should not require Google SDKs eagerly."""
    for module_name in [
        "google.auth.transport.requests",
        "google.oauth2.credentials",
        "google_auth_oauthlib.flow",
        "googleapiclient.discovery",
        "googleapiclient.errors",
        "googleapiclient.http",
    ]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    upload_module = importlib.import_module("auto_video.upload")
    pipeline_module = importlib.import_module("auto_video.core.pipeline")

    assert hasattr(upload_module, "YouTubeUploader")
    assert hasattr(pipeline_module, "VideoPipeline")
