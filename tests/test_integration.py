"""Integration tests for auto-video."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from auto_video.config.schema import AppConfig
from auto_video.core.pipeline import PipelineState, PipelineStep, VideoPipeline


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path / "temp"


@pytest.fixture
def test_config(temp_dir: Path) -> AppConfig:
    return AppConfig(
        llm={"provider": "openai", "model": "gpt-4", "api_key": "test-key"},
        tts={"mode": "local", "voice": "default"},
        visuals={"mode": "stock", "providers": ["pexels"]},
        image_gen={"enabled": False},
        storage={
            "videos_path": str(temp_dir / "videos"),
            "temp_path": str(temp_dir),
        },
        youtube={"enabled": False},
        default_format="long",
        default_lang="fr",
    )


@patch("auto_video.core.pipeline.LLM")
@patch("auto_video.core.pipeline.TTS")
@patch("auto_video.core.pipeline.StockManager")
@patch("auto_video.core.pipeline.VideoComposer")
@patch("auto_video.core.pipeline.SubtitleGenerator")
@patch("auto_video.core.pipeline.ThumbnailGenerator")
def test_full_pipeline_mock(
    mock_thumbnail_gen: Mock,
    mock_subtitle_gen: Mock,
    mock_composer: Mock,
    mock_stock_manager: Mock,
    mock_tts: Mock,
    mock_llm: Mock,
    test_config: AppConfig,
    temp_dir: Path,
) -> None:
    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_script.return_value = "Test script content"
    mock_llm_instance.extract_keywords.return_value = ["test", "video"]
    mock_llm.return_value = mock_llm_instance

    mock_tts_instance = MagicMock()
    mock_tts_instance.synthesize_script.return_value = 45.0
    mock_tts.return_value = mock_tts_instance

    mock_stock_instance = MagicMock()
    mock_stock_instance.get_clips_for_script.return_value = [
        temp_dir / "clip1.mp4",
        temp_dir / "clip2.mp4",
    ]
    mock_stock_manager.return_value = mock_stock_instance

    mock_composer_instance = MagicMock()
    mock_composer.return_value = mock_composer_instance

    mock_subtitle_instance = MagicMock()
    mock_subtitle_instance.transcribe.return_value = {"segments": []}
    mock_subtitle_gen.return_value = mock_subtitle_instance

    mock_thumbnail_instance = MagicMock()
    mock_thumbnail_gen.return_value = mock_thumbnail_instance

    (temp_dir / "videos").mkdir(parents=True, exist_ok=True)
    output_file = temp_dir / "output.mp4"
    output_file.write_bytes(b"MOCK_VIDEO_DATA")

    with patch("auto_video.utils.workspace.Workspace.copy_to_output", return_value=output_file):
        pipeline = VideoPipeline(test_config)
        result = pipeline.run(title="Test Video", duration=60, skip_upload=True)

    assert result.status == "success"
    assert len(result.completed_steps) == 6
    assert result.failed_step is None
    assert result.error is None
    assert result.output_path is not None


def test_pipeline_resume(test_config: AppConfig, temp_dir: Path) -> None:
    video_id = "test_resume_video"
    workspace_path = temp_dir / video_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    script_path = workspace_path / "script.txt"
    script_path.write_text("Existing script content", encoding="utf-8")

    state_data = {
        "video_id": video_id,
        "title": "Test Resume",
        "format": "long",
        "lang": "fr",
        "duration": 180,
        "skip_upload": True,
        "current_step": 2,
        "completed_steps": [1],
        "failed_step": None,
        "error": None,
        "output_path": None,
        "youtube_url": None,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }

    state_path = workspace_path / "state.json"
    state_path.write_text(json.dumps(state_data), encoding="utf-8")

    with (
        patch("auto_video.core.pipeline.LLM") as mock_llm,
        patch("auto_video.core.pipeline.TTS") as mock_tts,
        patch("auto_video.core.pipeline.StockManager") as mock_stock,
        patch("auto_video.core.pipeline.VideoComposer") as mock_composer,
        patch("auto_video.core.pipeline.SubtitleGenerator") as mock_subtitle,
        patch("auto_video.core.pipeline.ThumbnailGenerator") as mock_thumbnail,
        patch(
        "auto_video.utils.workspace.Workspace.copy_to_output",
        return_value=temp_dir / "output.mp4",
    ),
    ):
        mock_llm_instance = MagicMock()
        mock_llm_instance.extract_keywords.return_value = ["test"]
        mock_llm_instance.generate_script.return_value = "Test script"
        mock_llm.return_value = mock_llm_instance

        mock_tts_instance = MagicMock()
        mock_tts_instance.synthesize_script.return_value = 30.0
        mock_tts.return_value = mock_tts_instance

        mock_stock_instance = MagicMock()
        mock_stock_instance.get_clips_for_script.return_value = [temp_dir / "clip1.mp4"]
        mock_stock.return_value = mock_stock_instance

        mock_composer.return_value = MagicMock()
        mock_subtitle.return_value = MagicMock()
        mock_subtitle.return_value.transcribe.return_value = {"segments": []}
        mock_thumbnail.return_value = MagicMock()

        pipeline = VideoPipeline(test_config)
        result = pipeline.resume(video_id, PipelineStep.AUDIO)

    assert result.status == "success"
    assert result.video_id == video_id


@patch("auto_video.ui.setup.SetupWizard")
def test_cli_setup_command(mock_setup_wizard: Mock, tmp_path: Path) -> None:
    from auto_video.__main__ import cmd_setup
    from auto_video.config.schema import (
        ImageGenConfig,
        LLMProviderConfig,
        StorageConfig,
        TTSConfig,
        VisualsConfig,
        YouTubeConfig,
    )

    mock_wizard_instance = MagicMock()
    mock_config = AppConfig(
        llm=LLMProviderConfig(provider="openai", model="gpt-4", api_key="test"),
        tts=TTSConfig(mode="local", voice="default"),
        visuals=VisualsConfig(mode="stock", providers=["pexels"]),
        image_gen=ImageGenConfig(enabled=False),
        storage=StorageConfig(
            videos_path=tmp_path / "videos", temp_path=tmp_path / "temp", keep_temp=True
        ),
        youtube=YouTubeConfig(enabled=False),
    )
    mock_wizard_instance.run.return_value = mock_config
    mock_setup_wizard.return_value = mock_wizard_instance

    result = cmd_setup()

    assert result == 0


@patch("auto_video.__main__.VideoPipeline")
def test_cli_create_command(mock_pipeline_class: Mock, tmp_path: Path) -> None:
    from argparse import Namespace

    from auto_video.__main__ import cmd_create
    from auto_video.config.schema import (
        ImageGenConfig,
        LLMProviderConfig,
        StorageConfig,
        TTSConfig,
        VisualsConfig,
        YouTubeConfig,
    )

    config = AppConfig(
        llm=LLMProviderConfig(provider="openai", model="gpt-4", api_key="test"),
        tts=TTSConfig(mode="local", voice="default"),
        visuals=VisualsConfig(mode="stock", providers=["pexels"]),
        image_gen=ImageGenConfig(enabled=False),
        storage=StorageConfig(
            videos_path=tmp_path / "videos", temp_path=tmp_path / "temp", keep_temp=True
        ),
        youtube=YouTubeConfig(enabled=False),
    )

    with patch("auto_video.__main__.load_config", return_value=config):
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.run.return_value = MagicMock(
            status="success",
            video_id="test-video-id",
            output_path=Path("/output/video.mp4"),
            youtube_url=None,
        )
        mock_pipeline_class.return_value = mock_pipeline_instance

        args = Namespace(
            title="Test Video",
            auto=False,
            format="long",
            lang="fr",
            duration=None,
            no_upload=True,
            keep_temp=False,
            config=None,
        )

        result = cmd_create(args)

    assert result == 0


@patch("auto_video.__main__.VideoPipeline")
def test_cli_resume_command(mock_pipeline_class: Mock, tmp_path: Path) -> None:
    from argparse import Namespace

    from auto_video.__main__ import cmd_resume
    from auto_video.config.schema import (
        ImageGenConfig,
        LLMProviderConfig,
        StorageConfig,
        TTSConfig,
        VisualsConfig,
        YouTubeConfig,
    )

    config = AppConfig(
        llm=LLMProviderConfig(provider="openai", model="gpt-4", api_key="test"),
        tts=TTSConfig(mode="local", voice="default"),
        visuals=VisualsConfig(mode="stock", providers=["pexels"]),
        image_gen=ImageGenConfig(enabled=False),
        storage=StorageConfig(
            videos_path=tmp_path / "videos", temp_path=tmp_path / "temp", keep_temp=True
        ),
        youtube=YouTubeConfig(enabled=False),
    )

    with patch("auto_video.__main__.load_config", return_value=config):
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.resume.return_value = MagicMock(
            status="success",
            video_id="test-123",
            output_path=Path("/output/video.mp4"),
            youtube_url=None,
        )
        mock_pipeline_class.return_value = mock_pipeline_instance

        args = Namespace(video_id="test-123", step=None, config=None)

        result = cmd_resume(args)

    assert result == 0


def test_cli_config_show_command(tmp_path: Path) -> None:
    from argparse import Namespace

    from auto_video.__main__ import cmd_config
    from auto_video.config.schema import (
        ImageGenConfig,
        LLMProviderConfig,
        StorageConfig,
        TTSConfig,
        VisualsConfig,
        YouTubeConfig,
    )

    config = AppConfig(
        llm=LLMProviderConfig(provider="openai", model="gpt-4", api_key="test"),
        tts=TTSConfig(mode="local", voice="default"),
        visuals=VisualsConfig(mode="stock", providers=["pexels"]),
        image_gen=ImageGenConfig(enabled=False),
        storage=StorageConfig(
            videos_path=tmp_path / "videos", temp_path=tmp_path / "temp", keep_temp=True
        ),
        youtube=YouTubeConfig(enabled=False),
    )

    with patch("auto_video.__main__.load_config", return_value=config):
        args = Namespace(show=True, edit=False, config=None)

        result = cmd_config(args)

    assert result == 0


def test_cli_models_list_command() -> None:
    from argparse import Namespace

    from auto_video.__main__ import cmd_models

    args = Namespace(list=True, download=False)

    result = cmd_models(args)

    assert result == 0


@patch("auto_video.core.pipeline.LLM")
def test_pipeline_error_handling(mock_llm: Mock, test_config: AppConfig, temp_dir: Path) -> None:
    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_script.side_effect = Exception("LLM API Error")
    mock_llm.return_value = mock_llm_instance

    (temp_dir / "videos").mkdir(parents=True, exist_ok=True)

    pipeline = VideoPipeline(test_config)
    result = pipeline.run(title="Error Test", duration=60, skip_upload=True)

    assert result.status == "failed"
    assert result.failed_step == PipelineStep.SCRIPT
    assert result.error == "LLM API Error"


@patch("auto_video.core.pipeline.LLM")
@patch("auto_video.core.pipeline.TTS")
@patch("auto_video.core.pipeline.StockManager")
@patch("auto_video.core.pipeline.VideoComposer")
@patch("auto_video.core.pipeline.SubtitleGenerator")
def test_pipeline_partial_success(
    mock_subtitle_gen: Mock,
    mock_composer: Mock,
    mock_stock_manager: Mock,
    mock_tts: Mock,
    mock_llm: Mock,
    test_config: AppConfig,
    temp_dir: Path,
) -> None:
    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_script.return_value = "Test script"
    mock_llm_instance.extract_keywords.return_value = []
    mock_llm.return_value = mock_llm_instance

    mock_tts_instance = MagicMock()
    mock_tts_instance.synthesize_script.return_value = 30.0
    mock_tts.return_value = mock_tts_instance

    mock_stock_instance = MagicMock()
    mock_stock_instance.get_clips_for_script.return_value = [temp_dir / "clip1.mp4"]
    mock_stock_manager.return_value = mock_stock_instance

    mock_composer_instance = MagicMock()
    mock_composer_instance.concatenate_clips.side_effect = Exception("FFmpeg Error")
    mock_composer.return_value = mock_composer_instance

    mock_subtitle_gen.return_value = MagicMock()

    (temp_dir / "videos").mkdir(parents=True, exist_ok=True)

    pipeline = VideoPipeline(test_config)
    result = pipeline.run(title="Partial Test", duration=60, skip_upload=True)

    assert result.status == "partial"
    assert result.failed_step == PipelineStep.MONTAGE


@patch("auto_video.core.pipeline.LLM")
@patch("auto_video.core.pipeline.TTS")
@patch("auto_video.core.pipeline.StockManager")
@patch("auto_video.core.pipeline.VideoComposer")
@patch("auto_video.core.pipeline.SubtitleGenerator")
@patch("auto_video.core.pipeline.ThumbnailGenerator")
def test_pipeline_with_stock_visuals_mode(
    mock_thumbnail_gen: Mock,
    mock_subtitle_gen: Mock,
    mock_composer: Mock,
    mock_stock_manager: Mock,
    mock_tts: Mock,
    mock_llm: Mock,
    temp_dir: Path,
) -> None:
    config = AppConfig(
        llm={"provider": "openai", "model": "gpt-4", "api_key": "test-key"},
        tts={"mode": "local", "voice": "default"},
        visuals={"mode": "stock", "providers": ["pexels", "pixabay"]},
        image_gen={"enabled": False},
        storage={
            "videos_path": str(temp_dir / "videos"),
            "temp_path": str(temp_dir / "temp"),
        },
        youtube={"enabled": False},
    )

    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_script.return_value = "Test script"
    mock_llm_instance.extract_keywords.return_value = ["stock", "footage"]
    mock_llm.return_value = mock_llm_instance

    mock_tts_instance = MagicMock()
    mock_tts_instance.synthesize_script.return_value = 30.0
    mock_tts.return_value = mock_tts_instance

    mock_stock_instance = MagicMock()
    mock_stock_instance.get_clips_for_script.return_value = [
        temp_dir / "stock1.mp4",
        temp_dir / "stock2.mp4",
    ]
    mock_stock_manager.return_value = mock_stock_instance

    mock_composer.return_value = MagicMock()
    mock_subtitle_gen.return_value = MagicMock()
    mock_subtitle_gen.return_value.transcribe.return_value = {"segments": []}
    mock_thumbnail_gen.return_value = MagicMock()

    (temp_dir / "videos").mkdir(parents=True, exist_ok=True)
    (temp_dir / "temp").mkdir(parents=True, exist_ok=True)

    with patch(
        "auto_video.utils.workspace.Workspace.copy_to_output",
        return_value=temp_dir / "output.mp4",
    ):
        pipeline = VideoPipeline(config)
        result = pipeline.run(title="Stock Test", duration=60, skip_upload=True)

    assert result.status == "success"


def test_pipeline_state_persistence(test_config: AppConfig, temp_dir: Path) -> None:
    video_id = "test_state_video"
    workspace_path = temp_dir / video_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    state = PipelineState(
        video_id=video_id,
        title="State Test",
        format="long",
        lang="fr",
        duration=180,
        skip_upload=True,
        current_step=2,
        completed_steps=[1],
        failed_step=None,
        error=None,
        output_path=None,
        youtube_url=None,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )

    state_path = workspace_path / "state.json"
    state_path.write_text(state.model_dump_json(), encoding="utf-8")

    from auto_video.utils.workspace import Workspace

    ws = Workspace(temp_dir, video_id)
    loaded_state = VideoPipeline(test_config)._load_state(ws)

    assert loaded_state is not None
    assert loaded_state.video_id == video_id
    assert loaded_state.current_step == 2


@patch("sys.argv", ["auto-video", "--version"])
def test_cli_version_command(capsys: pytest.CaptureFixture[str]) -> None:
    from auto_video.__main__ import main

    result = main()

    assert result == 0
    captured = capsys.readouterr()
    assert "auto-video 0.1.0" in captured.out


@patch("auto_video.__main__.load_config")
def test_cli_missing_config(mock_load_config: Mock, tmp_path: Path) -> None:
    from argparse import Namespace

    from auto_video.__main__ import cmd_create

    mock_load_config.side_effect = FileNotFoundError("Config not found")

    args = Namespace(
        title="Test",
        auto=False,
        format="long",
        lang="fr",
        duration=None,
        no_upload=True,
        keep_temp=False,
        config=tmp_path / "nonexistent.yaml",
    )

    result = cmd_create(args)

    assert result == 1


@patch("auto_video.__main__.load_config")
def test_cli_invalid_step(mock_load_config: Mock, tmp_path: Path) -> None:
    from argparse import Namespace

    from auto_video.__main__ import cmd_resume
    from auto_video.config.schema import (
        ImageGenConfig,
        LLMProviderConfig,
        StorageConfig,
        TTSConfig,
        VisualsConfig,
        YouTubeConfig,
    )

    config = AppConfig(
        llm=LLMProviderConfig(provider="openai", model="gpt-4", api_key="test"),
        tts=TTSConfig(mode="local", voice="default"),
        visuals=VisualsConfig(mode="stock", providers=["pexels"]),
        image_gen=ImageGenConfig(enabled=False),
        storage=StorageConfig(
            videos_path=tmp_path / "videos", temp_path=tmp_path / "temp", keep_temp=True
        ),
        youtube=YouTubeConfig(enabled=False),
    )

    mock_load_config.return_value = config

    args = Namespace(video_id="test-123", step=99, config=None)

    result = cmd_resume(args)

    assert result == 1
