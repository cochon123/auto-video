"""Test pipeline orchestrator."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from auto_video.config.schema import AppConfig
from auto_video.core.pipeline import (
    PipelineProgress,
    PipelineResult,
    PipelineState,
    PipelineStep,
    VideoPipeline,
)


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path / "temp"


@pytest.fixture
def config(temp_dir: Path) -> AppConfig:
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


@pytest.fixture
def pipeline(config: AppConfig) -> VideoPipeline:
    return VideoPipeline(config)


def test_pipeline_step_enum_values() -> None:
    assert PipelineStep.SCRIPT.value == 1
    assert PipelineStep.AUDIO.value == 2
    assert PipelineStep.VISUALS.value == 3
    assert PipelineStep.MONTAGE.value == 4
    assert PipelineStep.SUBTITLES.value == 5
    assert PipelineStep.THUMBNAIL.value == 6
    assert PipelineStep.UPLOAD.value == 7


def test_pipeline_result_with_success_status() -> None:
    result = PipelineResult(
        video_id="test-id",
        status="success",
        completed_steps=[PipelineStep.SCRIPT, PipelineStep.AUDIO],
        failed_step=None,
        error=None,
        output_path=Path("/output/video.mp4"),
        youtube_url="https://youtube.com/watch?v=123",
    )
    assert result.video_id == "test-id"
    assert result.status == "success"
    assert len(result.completed_steps) == 2
    assert result.failed_step is None
    assert result.error is None
    assert result.output_path == Path("/output/video.mp4")
    assert result.youtube_url == "https://youtube.com/watch?v=123"


def test_pipeline_result_with_failed_status() -> None:
    result = PipelineResult(
        video_id="test-id",
        status="failed",
        completed_steps=[PipelineStep.SCRIPT],
        failed_step=PipelineStep.AUDIO,
        error="Audio generation failed",
        output_path=None,
        youtube_url=None,
    )
    assert result.video_id == "test-id"
    assert result.status == "failed"
    assert len(result.completed_steps) == 1
    assert result.failed_step == PipelineStep.AUDIO
    assert result.error == "Audio generation failed"
    assert result.output_path is None
    assert result.youtube_url is None


def test_pipeline_result_with_partial_status() -> None:
    result = PipelineResult(
        video_id="test-id",
        status="partial",
        completed_steps=[PipelineStep.SCRIPT, PipelineStep.AUDIO, PipelineStep.VISUALS],
        failed_step=PipelineStep.MONTAGE,
        error="Montage failed",
        output_path=None,
        youtube_url=None,
    )
    assert result.video_id == "test-id"
    assert result.status == "partial"
    assert len(result.completed_steps) == 3
    assert result.failed_step == PipelineStep.MONTAGE
    assert result.error == "Montage failed"


def test_video_pipeline_initialization(config: AppConfig) -> None:
    pipeline = VideoPipeline(config)
    assert pipeline.config == config
    assert pipeline._workspace is None
    assert pipeline._progress is None


@patch("auto_video.core.pipeline.LLM")
@patch("auto_video.core.pipeline.TTS")
@patch("auto_video.core.pipeline.StockManager")
@patch("auto_video.core.pipeline.VideoComposer")
@patch("auto_video.core.pipeline.SubtitleGenerator")
@patch("auto_video.core.pipeline.ThumbnailGenerator")
def test_run_with_mocked_providers_returns_success(
    mock_thumbnail_gen: Mock,
    mock_subtitle_gen: Mock,
    mock_composer: Mock,
    mock_stock_manager: Mock,
    mock_tts: Mock,
    mock_llm: Mock,
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_script.return_value = "Test script"
    mock_llm_instance.extract_keywords.return_value = ["keyword1", "keyword2"]
    mock_llm.return_value = mock_llm_instance

    mock_tts_instance = MagicMock()
    mock_tts_instance.synthesize_script.return_value = 45.0
    mock_tts.return_value = mock_tts_instance

    mock_stock_instance = MagicMock()
    mock_stock_instance.get_clips_for_script.return_value = [
        Path("/clip1.mp4"),
        Path("/clip2.mp4"),
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

    with patch(
        "auto_video.utils.workspace.Workspace.copy_to_output",
        return_value=Path("/output/video.mp4"),
    ):
        result = pipeline.run(title="Test Video", duration=60, skip_upload=True)

    assert result.status == "success"
    assert len(result.completed_steps) == 6
    assert result.failed_step is None
    assert result.error is None


@patch("auto_video.core.pipeline.LLM")
def test_run_with_error_returns_failure(
    mock_llm: Mock,
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_script.side_effect = Exception("LLM failed")
    mock_llm.return_value = mock_llm_instance

    (temp_dir / "videos").mkdir(parents=True, exist_ok=True)

    result = pipeline.run(title="Test Video", duration=60, skip_upload=True)

    assert result.status == "failed"
    assert result.failed_step == PipelineStep.SCRIPT
    assert result.error == "LLM failed"
    assert len(result.completed_steps) == 0


def test_run_creates_workspace(
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    with (
        patch("auto_video.core.pipeline.LLM") as mock_llm,
        patch("auto_video.core.pipeline.TTS") as mock_tts,
        patch("auto_video.core.pipeline.StockManager") as mock_stock,
        patch("auto_video.core.pipeline.VideoComposer") as mock_composer,
        patch("auto_video.core.pipeline.SubtitleGenerator") as mock_subtitle,
        patch("auto_video.core.pipeline.ThumbnailGenerator") as mock_thumbnail,
        patch(
            "auto_video.utils.workspace.Workspace.copy_to_output",
            return_value=Path("/output/video.mp4"),
        ),
    ):
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_script.return_value = "Test script"
        mock_llm_instance.extract_keywords.return_value = []
        mock_llm.return_value = mock_llm_instance

        mock_tts_instance = MagicMock()
        mock_tts_instance.synthesize_script.return_value = 30.0
        mock_tts.return_value = mock_tts_instance

        mock_stock_instance = MagicMock()
        mock_stock_instance.get_clips_for_script.return_value = [
            Path("/clip1.mp4"),
            Path("/clip2.mp4"),
        ]
        mock_stock.return_value = mock_stock_instance

        mock_composer.return_value = MagicMock()
        mock_subtitle.return_value = MagicMock()
        mock_subtitle.return_value.transcribe.return_value = {"segments": []}
        mock_thumbnail.return_value = MagicMock()

        (temp_dir / "videos").mkdir(parents=True, exist_ok=True)

        result = pipeline.run(title="Test Video", duration=60, skip_upload=True)

        workspace_path = temp_dir / result.video_id
        assert workspace_path.exists()
        assert (workspace_path / "script.txt").exists()
        assert (workspace_path / "state.json").exists()


def test_run_skips_upload_when_skip_upload_true(
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    with (
        patch("auto_video.core.pipeline.LLM") as mock_llm,
        patch("auto_video.core.pipeline.TTS") as mock_tts,
        patch("auto_video.core.pipeline.StockManager") as mock_stock,
        patch("auto_video.core.pipeline.VideoComposer") as mock_composer,
        patch("auto_video.core.pipeline.SubtitleGenerator") as mock_subtitle,
        patch("auto_video.core.pipeline.YouTubeUploader") as mock_uploader,
        patch("auto_video.core.pipeline.ThumbnailGenerator") as mock_thumbnail,
        patch("auto_video.core.pipeline.Workspace") as mock_workspace,
    ):
        mock_workspace_instance = MagicMock()
        mock_workspace_instance.video_id = "test-video-id"
        mock_workspace_instance.copy_to_output.return_value = Path("/output/video.mp4")
        mock_workspace.return_value = mock_workspace_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_script.return_value = "Test script"
        mock_llm_instance.extract_keywords.return_value = []
        mock_llm.return_value = mock_llm_instance

        mock_tts_instance = MagicMock()
        mock_tts_instance.synthesize_script.return_value = 30.0
        mock_tts.return_value = mock_tts_instance

        mock_stock_instance = MagicMock()
        mock_stock_instance.get_clips_for_script.return_value = [
            Path("/clip1.mp4"),
            Path("/clip2.mp4"),
        ]
        mock_stock.return_value = mock_stock_instance

        mock_composer.return_value = MagicMock()
        mock_subtitle.return_value = MagicMock()
        mock_subtitle.return_value.transcribe.return_value = {"segments": []}
        mock_thumbnail.return_value = MagicMock()

        (temp_dir / "videos").mkdir(parents=True, exist_ok=True)

        result = pipeline.run(title="Test Video", duration=60, skip_upload=True)

        assert result.status == "success"
        assert PipelineStep.UPLOAD not in result.completed_steps
        mock_uploader.assert_not_called()


def test_resume_loads_existing_state(
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    video_id = "test_video_id"
    workspace_path = temp_dir / video_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    state_data = {
        "video_id": video_id,
        "title": "Test Title",
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
    ):
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_script.return_value = "Test script"
        mock_llm_instance.extract_keywords.return_value = []
        mock_llm.return_value = mock_llm_instance

        mock_tts_instance = MagicMock()
        mock_tts_instance.synthesize_script.return_value = 30.0
        mock_tts.return_value = mock_tts_instance

        result = pipeline.resume(video_id, PipelineStep.AUDIO)

        assert result.video_id == video_id


def test_resume_continues_from_step(
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    video_id = "test_video_id"
    workspace_path = temp_dir / video_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    script_path = workspace_path / "script.txt"
    script_path.write_text("Existing script", encoding="utf-8")

    state_data = {
        "video_id": video_id,
        "title": "Test Title",
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
            return_value=Path("/output/video.mp4"),
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
        mock_stock_instance.get_clips_for_script.return_value = [
            Path("/clip1.mp4"),
            Path("/clip2.mp4"),
        ]
        mock_stock.return_value = mock_stock_instance

        mock_composer.return_value = MagicMock()
        mock_subtitle.return_value = MagicMock()
        mock_subtitle.return_value.transcribe.return_value = {"segments": []}
        mock_thumbnail.return_value = MagicMock()

        result = pipeline.resume(video_id, PipelineStep.AUDIO)

        assert result.status == "success"
        assert PipelineStep.SCRIPT in result.completed_steps
        assert PipelineStep.AUDIO in result.completed_steps


def test_resume_skips_completed_steps(
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    video_id = "test_video_id"
    workspace_path = temp_dir / video_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    script_path = workspace_path / "script.txt"
    script_path.write_text("Existing script", encoding="utf-8")

    state_data = {
        "video_id": video_id,
        "title": "Test Title",
        "format": "long",
        "lang": "fr",
        "duration": 180,
        "skip_upload": True,
        "current_step": 3,
        "completed_steps": [1, 2],
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
        patch("auto_video.core.pipeline.StockManager") as mock_stock,
        patch("auto_video.core.pipeline.VideoComposer") as mock_composer,
        patch("auto_video.core.pipeline.SubtitleGenerator") as mock_subtitle,
        patch("auto_video.core.pipeline.ThumbnailGenerator") as mock_thumbnail,
        patch(
            "auto_video.utils.workspace.Workspace.copy_to_output",
            return_value=Path("/output/video.mp4"),
        ),
    ):
        mock_llm_instance = MagicMock()
        mock_llm_instance.extract_keywords.return_value = ["test"]
        mock_llm_instance.generate_script.return_value = "Test script"
        mock_llm.return_value = mock_llm_instance

        mock_stock_instance = MagicMock()
        mock_stock_instance.get_clips_for_script.return_value = [
            Path("/clip1.mp4"),
            Path("/clip2.mp4"),
        ]
        mock_stock.return_value = mock_stock_instance

        mock_composer.return_value = MagicMock()
        mock_subtitle.return_value = MagicMock()
        mock_subtitle.return_value.transcribe.return_value = {"segments": []}
        mock_thumbnail.return_value = MagicMock()

        result = pipeline.resume(video_id, PipelineStep.VISUALS)

        assert PipelineStep.SCRIPT in result.completed_steps
        assert PipelineStep.AUDIO in result.completed_steps
        assert PipelineStep.VISUALS in result.completed_steps
        assert PipelineStep.MONTAGE in result.completed_steps


def test_get_progress_returns_current_state(
    pipeline: VideoPipeline,
) -> None:
    progress = pipeline.get_progress()
    assert progress is None

    pipeline._progress = PipelineProgress("test-id", PipelineStep.SCRIPT, 0.5)

    progress = pipeline.get_progress()
    assert progress is not None
    assert progress.video_id == "test-id"
    assert progress.current_step == PipelineStep.SCRIPT
    assert progress.step_progress == 0.5


def test_save_state_writes_state_file(
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    from auto_video.utils.workspace import Workspace

    video_id = "test_video_id"
    workspace_path = temp_dir / video_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    pipeline._workspace = Workspace(temp_dir, video_id)

    state = PipelineState(
        video_id=video_id,
        title="Test Title",
        format="long",
        lang="fr",
        duration=180,
        skip_upload=True,
        current_step=1,
        completed_steps=[],
        failed_step=None,
        error=None,
        output_path=None,
        youtube_url=None,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )

    pipeline._save_state(state)

    state_path = workspace_path / "state.json"
    assert state_path.exists()

    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["video_id"] == video_id
    assert data["title"] == "Test Title"
    assert data["current_step"] == 1


def test_load_state_reads_state_file(
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    from auto_video.utils.workspace import Workspace

    video_id = "test_video_id"
    workspace_path = temp_dir / video_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    state_data = {
        "video_id": video_id,
        "title": "Test Title",
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

    workspace = Workspace(temp_dir, video_id)
    state = pipeline._load_state(workspace)

    assert state is not None
    assert state.video_id == video_id
    assert state.title == "Test Title"
    assert state.current_step == 2
    assert state.completed_steps == [1]


def test_load_state_returns_none_when_file_not_found(
    pipeline: VideoPipeline,
    temp_dir: Path,
) -> None:
    from auto_video.utils.workspace import Workspace

    workspace = Workspace(temp_dir, "non_existent_video_id")

    state = pipeline._load_state(workspace)
    assert state is None


@patch("subprocess.run")
def test_get_audio_duration_returns_duration(
    mock_run: Mock,
    pipeline: VideoPipeline,
) -> None:
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "45.5"
    mock_run.return_value = mock_result

    duration = pipeline._get_audio_duration(Path("/fake/audio.wav"))
    assert duration == 45.5


@patch("subprocess.run")
def test_get_audio_duration_returns_zero_on_error(
    mock_run: Mock,
    pipeline: VideoPipeline,
) -> None:
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_run.return_value = mock_result

    duration = pipeline._get_audio_duration(Path("/fake/audio.wav"))
    assert duration == 0.0


@patch("subprocess.run")
def test_get_audio_duration_returns_zero_on_timeout(
    mock_run: Mock,
    pipeline: VideoPipeline,
) -> None:
    from subprocess import TimeoutExpired

    mock_run.side_effect = TimeoutExpired("ffprobe", 10)

    duration = pipeline._get_audio_duration(Path("/fake/audio.wav"))
    assert duration == 0.0


@patch("auto_video.core.pipeline.LLM")
@patch("auto_video.core.pipeline.TTS")
@patch("auto_video.core.pipeline.StockManager")
@patch("auto_video.core.pipeline.VideoComposer")
@patch("auto_video.core.pipeline.SubtitleGenerator")
@patch("auto_video.core.pipeline.ThumbnailGenerator")
@patch("auto_video.core.pipeline.Workspace")
def test_pipeline_with_stock_visuals_mode(
    mock_workspace: Mock,
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

    pipeline = VideoPipeline(config)

    mock_workspace_instance = MagicMock()
    mock_workspace_instance.video_id = "test-video-id"
    mock_workspace_instance.copy_to_output.return_value = Path("/output/video.mp4")
    mock_workspace.return_value = mock_workspace_instance

    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_script.return_value = "Test script"
    mock_llm_instance.extract_keywords.return_value = ["stock", "footage"]
    mock_llm.return_value = mock_llm_instance

    mock_tts_instance = MagicMock()
    mock_tts_instance.synthesize_script.return_value = 30.0
    mock_tts.return_value = mock_tts_instance

    mock_stock_instance = MagicMock()
    mock_stock_instance.get_clips_for_script.return_value = [
        Path("/stock1.mp4"),
        Path("/stock2.mp4"),
    ]
    mock_stock_manager.return_value = mock_stock_instance

    mock_composer.return_value = MagicMock()
    mock_subtitle_gen.return_value = MagicMock()
    mock_subtitle_gen.return_value.transcribe.return_value = {"segments": []}
    mock_thumbnail_gen.return_value = MagicMock()

    (temp_dir / "videos").mkdir(parents=True, exist_ok=True)
    (temp_dir / "temp").mkdir(parents=True, exist_ok=True)

    result = pipeline.run(title="Stock Test", duration=60, skip_upload=True)

    assert result.status == "success"
    mock_stock_instance.get_clips_for_script.assert_called_once()


@patch("auto_video.core.pipeline.LLM")
@patch("auto_video.core.pipeline.TTS")
@patch("auto_video.core.pipeline.LocalAssetsManager")
@patch("auto_video.core.pipeline.VideoComposer")
@patch("auto_video.core.pipeline.SubtitleGenerator")
@patch("auto_video.core.pipeline.ThumbnailGenerator")
@patch("auto_video.core.pipeline.Workspace")
def test_pipeline_with_local_visuals_mode(
    mock_workspace: Mock,
    mock_thumbnail_gen: Mock,
    mock_subtitle_gen: Mock,
    mock_composer: Mock,
    mock_local_manager: Mock,
    mock_tts: Mock,
    mock_llm: Mock,
    temp_dir: Path,
) -> None:
    local_videos_path = temp_dir / "local_videos"
    local_videos_path.mkdir(parents=True, exist_ok=True)

    config = AppConfig(
        llm={"provider": "openai", "model": "gpt-4", "api_key": "test-key"},
        tts={"mode": "local", "voice": "default"},
        visuals={"mode": "local", "local_path": str(local_videos_path)},
        image_gen={"enabled": False},
        storage={
            "videos_path": str(temp_dir / "videos"),
            "temp_path": str(temp_dir / "temp"),
        },
        youtube={"enabled": False},
    )

    pipeline = VideoPipeline(config)

    mock_workspace_instance = MagicMock()
    mock_workspace_instance.video_id = "test-video-id"
    mock_workspace_instance.copy_to_output.return_value = Path("/output/video.mp4")
    mock_workspace.return_value = mock_workspace_instance

    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_script.return_value = "Test script"
    mock_llm_instance.extract_keywords.return_value = []
    mock_llm.return_value = mock_llm_instance

    mock_tts_instance = MagicMock()
    mock_tts_instance.synthesize_script.return_value = 30.0
    mock_tts.return_value = mock_tts_instance

    mock_local_instance = MagicMock()
    mock_local_instance.get_random_sequence.return_value = [
        {"path": Path("/local1.mp4"), "duration": 10.0},
        {"path": Path("/local2.mp4"), "duration": 20.0},
    ]
    mock_local_instance.prepare_clips.return_value = [
        Path("/local1.mp4"),
        Path("/local2.mp4"),
    ]
    mock_local_manager.return_value = mock_local_instance

    mock_composer.return_value = MagicMock()
    mock_subtitle_gen.return_value = MagicMock()
    mock_subtitle_gen.return_value.transcribe.return_value = {"segments": []}
    mock_thumbnail_gen.return_value = MagicMock()

    (temp_dir / "videos").mkdir(parents=True, exist_ok=True)
    (temp_dir / "temp").mkdir(parents=True, exist_ok=True)

    result = pipeline.run(title="Local Test", duration=60, skip_upload=True)

    assert result.status == "success"
    mock_local_instance.get_random_sequence.assert_called_once()
    mock_local_instance.prepare_clips.assert_called_once()


@patch("auto_video.core.pipeline.LLM")
@patch("auto_video.core.pipeline.TTS")
@patch("auto_video.core.pipeline.StockManager")
@patch("auto_video.core.pipeline.LocalAssetsManager")
@patch("auto_video.core.pipeline.VideoComposer")
@patch("auto_video.core.pipeline.SubtitleGenerator")
@patch("auto_video.core.pipeline.ThumbnailGenerator")
@patch("auto_video.core.pipeline.Workspace")
def test_pipeline_with_hybrid_visuals_mode(
    mock_workspace: Mock,
    mock_thumbnail_gen: Mock,
    mock_subtitle_gen: Mock,
    mock_composer: Mock,
    mock_local_manager: Mock,
    mock_stock_manager: Mock,
    mock_tts: Mock,
    mock_llm: Mock,
    temp_dir: Path,
) -> None:
    local_videos_path = temp_dir / "local_videos"
    local_videos_path.mkdir(parents=True, exist_ok=True)

    config = AppConfig(
        llm={"provider": "openai", "model": "gpt-4", "api_key": "test-key"},
        tts={"mode": "local", "voice": "default"},
        visuals={
            "mode": "hybrid",
            "providers": ["pexels"],
            "local_path": str(local_videos_path),
        },
        image_gen={"enabled": False},
        storage={
            "videos_path": str(temp_dir / "videos"),
            "temp_path": str(temp_dir / "temp"),
        },
        youtube={"enabled": False},
    )

    pipeline = VideoPipeline(config)

    mock_workspace_instance = MagicMock()
    mock_workspace_instance.video_id = "test-video-id"
    mock_workspace_instance.copy_to_output.return_value = Path("/output/video.mp4")
    mock_workspace.return_value = mock_workspace_instance

    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_script.return_value = "Test script"
    mock_llm_instance.extract_keywords.return_value = ["hybrid", "test"]
    mock_llm.return_value = mock_llm_instance

    mock_tts_instance = MagicMock()
    mock_tts_instance.synthesize_script.return_value = 60.0
    mock_tts.return_value = mock_tts_instance

    mock_stock_instance = MagicMock()
    mock_stock_instance.get_clips_for_script.return_value = [
        Path("/stock1.mp4"),
        Path("/stock2.mp4"),
    ]
    mock_stock_manager.return_value = mock_stock_instance

    mock_local_instance = MagicMock()
    mock_local_instance.get_random_sequence.return_value = [
        {"path": Path("/local1.mp4"), "duration": 15.0},
        {"path": Path("/local2.mp4"), "duration": 15.0},
    ]
    mock_local_instance.prepare_clips.return_value = [
        Path("/local1.mp4"),
        Path("/local2.mp4"),
    ]
    mock_local_manager.return_value = mock_local_instance

    mock_composer.return_value = MagicMock()
    mock_subtitle_gen.return_value = MagicMock()
    mock_subtitle_gen.return_value.transcribe.return_value = {"segments": []}
    mock_thumbnail_gen.return_value = MagicMock()

    (temp_dir / "videos").mkdir(parents=True, exist_ok=True)
    (temp_dir / "temp").mkdir(parents=True, exist_ok=True)

    result = pipeline.run(title="Hybrid Test", duration=60, skip_upload=True)

    assert result.status == "success"
    mock_stock_instance.get_clips_for_script.assert_called_once()
    mock_local_instance.get_random_sequence.assert_called_once()


def test_pipeline_progress_initialization() -> None:
    progress = PipelineProgress("test-id", PipelineStep.SCRIPT, 0.5)
    assert progress.video_id == "test-id"
    assert progress.current_step == PipelineStep.SCRIPT
    assert progress.step_progress == 0.5


def test_pipeline_state_initialization() -> None:
    state = PipelineState(
        video_id="test-id",
        title="Test Title",
        format="long",
        lang="fr",
        duration=180,
        skip_upload=True,
        current_step=1,
        completed_steps=[],
        failed_step=None,
        error=None,
        output_path=None,
        youtube_url=None,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )
    assert state.video_id == "test-id"
    assert state.title == "Test Title"
    assert state.format == "long"
    assert state.lang == "fr"
    assert state.duration == 180
    assert state.skip_upload is True
    assert state.current_step == 1
    assert state.completed_steps == []
    assert state.failed_step is None
    assert state.error is None
