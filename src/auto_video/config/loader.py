"""Configuration loader."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from auto_video.config.schema import AppConfig
from auto_video.utils.security import mask_secrets_in_string

logger = logging.getLogger(__name__)


def _substitute_env_vars(value: str) -> str:
    if not isinstance(value, str):
        return value

    if "${" in value:
        start = value.find("${")
        end = value.find("}", start)
        if end > start:
            var_name = value[start + 2 : end]
            var_value = os.environ.get(var_name, "")
            return _substitute_env_vars(value[:start] + var_value + value[end + 1 :])

    return value


def _substitute_env_vars_recursive(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _substitute_env_vars_recursive(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_substitute_env_vars_recursive(item) for item in data]
    if isinstance(data, str):
        return _substitute_env_vars(data)
    return data


def save_config(config: AppConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    config_dict = config.model_dump(mode="json")

    old_umask = os.umask(0o077)
    try:
        with path.open("w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
    finally:
        os.umask(old_umask)

    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        with path.open("r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        masked_error = mask_secrets_in_string(str(e))
        raise ValueError(f"Invalid YAML in configuration file: {masked_error}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Invalid configuration format in {path}")

    data = _substitute_env_vars_recursive(data)

    if isinstance(data, dict):
        data = _convert_paths_to_path_objects(data)

    try:
        return AppConfig.model_validate(data)
    except Exception as e:
        masked_error = mask_secrets_in_string(str(e))
        raise ValueError(f"Invalid configuration: {masked_error}") from e


def _convert_paths_to_path_objects(data: Any) -> Any:
    if isinstance(data, list):
        return [_convert_paths_to_path_objects(item) for item in data]
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        path_keys = ["videos_path", "temp_path", "credentials_path", "local_path"]

        for key in path_keys:
            if key in data and isinstance(data[key], str):
                data[key] = Path(data[key])

        for section in ["storage", "youtube", "visuals"]:
            if section in data and isinstance(data[section], dict):
                for key in path_keys:
                    if key in data[section] and isinstance(data[section][key], str):
                        data[section][key] = Path(data[section][key])

    return data


def get_default_config_path() -> Path:
    config_dir = Path.home() / ".config" / "auto-video"
    return config_dir / "config.yaml"


def create_default_config(path: Path) -> AppConfig:
    from auto_video.config.schema import (
        ImageGenConfig,
        LLMProviderConfig,
        StorageConfig,
        TTSConfig,
        VideoConfig,
        VisualsConfig,
        YouTubeConfig,
    )

    config = AppConfig(
        llm=LLMProviderConfig(
            provider="openai",
            model="gpt-4",
            api_key=None,
            temperature=0.7,
        ),
        tts=TTSConfig(mode="api", provider="openai", model="tts-1", voice="alloy"),
        visuals=VisualsConfig(mode="stock", providers=["pexels", "duckduckgo"]),
        image_gen=ImageGenConfig(enabled=False),
        storage=StorageConfig(
            videos_path=Path.home() / "Videos" / "auto-videos",
            temp_path=Path.home() / ".cache" / "auto-video" / "temp",
            keep_temp=True,
        ),
        youtube=YouTubeConfig(enabled=False),
        video=VideoConfig(gpu_acceleration="auto", preset="fast", quality=22),
        default_format="long",
        default_lang="fr",
    )

    save_config(config, path)
    return config
