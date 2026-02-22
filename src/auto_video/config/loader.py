"""Configuration loader."""

import os
from pathlib import Path

import yaml

from auto_video.config.schema import AppConfig


def _substitute_env_vars(value: str) -> str:
    """Substitute environment variables in a string.

    Supports ${VAR_NAME} and $VAR_NAME syntax.
    """
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


def _substitute_env_vars_recursive(data: dict | list | str) -> dict | list | str:
    """Recursively substitute environment variables in a data structure."""
    if isinstance(data, dict):
        return {k: _substitute_env_vars_recursive(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_substitute_env_vars_recursive(item) for item in data]
    if isinstance(data, str):
        return _substitute_env_vars(data)
    return data


def save_config(config: AppConfig, path: Path) -> None:
    """Save configuration to a YAML file.

    Args:
        config: Configuration to save.
        path: Path to save the configuration file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    config_dict = config.model_dump(mode="json")

    with path.open("w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)


def load_config(path: Path) -> AppConfig:
    """Load configuration from a YAML file.

    Args:
        path: Path to the configuration file.

    Returns:
        Loaded configuration.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the configuration is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid configuration format in {path}")

    data = _substitute_env_vars_recursive(data)

    if isinstance(data, dict):
        data = _convert_paths_to_path_objects(data)

    return AppConfig.model_validate(data)


def _convert_paths_to_path_objects(data: dict | list | str) -> dict | list | str:
    """Convert path strings to Path objects in configuration data."""
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
    """Get the default configuration file path.

    Returns:
        Path to ~/.config/auto-video/config.yaml
    """
    config_dir = Path.home() / ".config" / "auto-video"
    return config_dir / "config.yaml"


def create_default_config(path: Path) -> AppConfig:
    """Create a default configuration file.

    Args:
        path: Path to save the default configuration.

    Returns:
        Default configuration.
    """
    from auto_video.config.schema import (
        ImageGenConfig,
        LLMProviderConfig,
        StorageConfig,
        TTSConfig,
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
        tts=TTSConfig(mode="local", voice="default"),
        visuals=VisualsConfig(mode="stock", providers=["pexels"]),
        image_gen=ImageGenConfig(enabled=False),
        storage=StorageConfig(
            videos_path=Path.home() / "Videos" / "auto-videos",
            temp_path=Path.home() / ".cache" / "auto-video" / "temp",
            keep_temp=True,
        ),
        youtube=YouTubeConfig(enabled=False),
        default_format="long",
        default_lang="fr",
    )

    save_config(config, path)
    return config
