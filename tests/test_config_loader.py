"""Test configuration loader."""

import os
import tempfile
from pathlib import Path

import pytest

from auto_video.config.loader import (
    _substitute_env_vars,
    _substitute_env_vars_recursive,
    create_default_config,
    get_default_config_path,
    load_config,
    save_config,
)
from auto_video.config.schema import AppConfig


def test_substitute_env_vars_simple():
    """Test simple environment variable substitution."""
    os.environ["TEST_VAR"] = "test-value"
    result = _substitute_env_vars("${TEST_VAR}")
    assert result == "test-value"
    del os.environ["TEST_VAR"]


def test_substitute_env_vars_partial():
    """Test partial environment variable substitution."""
    os.environ["PREFIX"] = "pre"
    result = _substitute_env_vars("text-${PREFIX}-suffix")
    assert result == "text-pre-suffix"
    del os.environ["PREFIX"]


def test_substitute_env_vars_none():
    """Test substitution with undefined env var."""
    os.environ.pop("UNDEFINED_VAR", None)
    result = _substitute_env_vars("${UNDEFINED_VAR}")
    assert result == ""


def test_substitute_env_vars_no_template():
    """Test that non-template strings are unchanged."""
    result = _substitute_env_vars("plain text")
    assert result == "plain text"


def test_substitute_env_vars_recursive_dict():
    """Test recursive substitution in dicts."""
    os.environ["KEY1"] = "value1"
    os.environ["KEY2"] = "value2"
    data = {"key1": "${KEY1}", "nested": {"key2": "${KEY2}"}}
    result = _substitute_env_vars_recursive(data)
    assert result["key1"] == "value1"
    assert result["nested"]["key2"] == "value2"
    del os.environ["KEY1"]
    del os.environ["KEY2"]


def test_substitute_env_vars_recursive_list():
    """Test recursive substitution in lists."""
    os.environ["ITEM"] = "item-value"
    data = ["${ITEM}", "static", "${ITEM}"]
    result = _substitute_env_vars_recursive(data)
    assert result == ["item-value", "static", "item-value"]
    del os.environ["ITEM"]


def test_save_and_load_config():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        config = AppConfig(
            llm={"provider": "openai", "model": "gpt-4", "api_key": "test-key"},
            tts={"mode": "local", "voice": "default"},
            visuals={"mode": "stock", "providers": ["pexels"]},
            image_gen={"enabled": False},
            storage={
                "videos_path": Path("/tmp/videos"),
                "temp_path": Path("/tmp/temp"),
            },
            youtube={"enabled": False},
            default_format="long",
            default_lang="fr",
        )

        save_config(config, config_path)

        assert config_path.exists()

        loaded = load_config(config_path)

        assert loaded.llm.provider == "openai"
        assert loaded.llm.model == "gpt-4"
        assert loaded.llm.api_key == "test-key"
        assert loaded.tts.mode == "local"
        assert loaded.visuals.mode == "stock"
        assert loaded.default_format == "long"


def test_load_config_with_env_vars():
    """Test loading config with environment variable substitution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        os.environ["TEST_API_KEY"] = "env-secret"
        os.environ["TEST_PROVIDER"] = "anthropic"

        config = AppConfig(
            llm={
                "provider": "${TEST_PROVIDER}",
                "model": "claude-3",
                "api_key": "${TEST_API_KEY}",
            },
            tts={"mode": "local", "voice": "default"},
            visuals={"mode": "stock"},
            image_gen={"enabled": False},
            storage={
                "videos_path": Path("/tmp/videos"),
                "temp_path": Path("/tmp/temp"),
            },
            youtube={"enabled": False},
        )

        save_config(config, config_path)
        del os.environ["TEST_API_KEY"]
        del os.environ["TEST_PROVIDER"]

        os.environ["TEST_API_KEY"] = "env-loaded-secret"
        os.environ["TEST_PROVIDER"] = "anthropic-loaded"

        loaded = load_config(config_path)

        assert loaded.llm.api_key == "env-loaded-secret"
        assert loaded.llm.provider == "anthropic-loaded"

        del os.environ["TEST_API_KEY"]
        del os.environ["TEST_PROVIDER"]


def test_load_config_not_found():
    """Test loading non-existent config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config(config_path)


def test_get_default_config_path():
    """Test getting default configuration path."""
    path = get_default_config_path()
    assert path.name == "config.yaml"
    assert path.parent.name == "auto-video"
    assert path.parent.parent.name == ".config"


def test_create_default_config():
    """Test creating default configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        config = create_default_config(config_path)

        assert config_path.exists()

        assert config.llm.provider == "openai"
        assert config.llm.model == "gpt-4"
        assert config.tts.mode == "api"
        assert config.tts.provider == "openai"
        assert config.tts.model == "tts-1"
        assert config.visuals.mode == "stock"
        assert "duckduckgo" in config.visuals.providers
        assert config.default_format == "long"
        assert config.default_lang == "fr"


def test_path_conversion_in_config():
    """Test that path strings are converted to Path objects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        config = AppConfig(
            llm={"provider": "openai", "model": "gpt-4", "api_key": "test"},
            tts={"mode": "local", "voice": "default"},
            visuals={"mode": "stock"},
            image_gen={"enabled": False},
            storage={
                "videos_path": "/tmp/videos",
                "temp_path": "/tmp/temp",
            },
            youtube={"enabled": False},
        )

        save_config(config, config_path)

        loaded = load_config(config_path)

        assert isinstance(loaded.storage.videos_path, Path)
        assert isinstance(loaded.storage.temp_path, Path)
        assert loaded.storage.videos_path == Path("/tmp/videos")
