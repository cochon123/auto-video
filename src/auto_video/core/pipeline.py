"""Pipeline orchestrator for video generation."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from auto_video.config.schema import AppConfig
from auto_video.core.llm import LLM
from auto_video.core.subtitles import SubtitleGenerator, SubtitleStyle
from auto_video.core.thumbnail import ThumbnailGenerator
from auto_video.core.tts import TTS
from auto_video.core.video import LocalAssetsManager, VideoComposer
from auto_video.core.visual_keywords import VisualKeywordExtractor
from auto_video.providers.stock import StockManager
from auto_video.upload.youtube import YouTubeUploader
from auto_video.utils.security import (
    validate_duration,
    validate_format,
    validate_language,
    validate_title,
    validate_video_id,
)
from auto_video.utils.workspace import Workspace

logger = logging.getLogger(__name__)


class PipelineStep(Enum):
    SCRIPT = 1
    AUDIO = 2
    VISUALS = 3
    MONTAGE = 4
    SUBTITLES = 5
    THUMBNAIL = 6
    UPLOAD = 7


class PipelineResult(BaseModel):
    video_id: str
    status: Literal["success", "partial", "failed"]
    completed_steps: list[PipelineStep]
    failed_step: PipelineStep | None
    error: str | None
    output_path: Path | None
    youtube_url: str | None


@dataclass
class PipelineProgress:
    video_id: str
    current_step: PipelineStep
    step_progress: float


class StepError(BaseModel):
    """Error information for a pipeline step."""

    step: PipelineStep
    error_message: str
    error_type: str
    timestamp: str
    traceback: str | None = None


class PipelineState(BaseModel):
    video_id: str
    title: str | None
    format: str
    lang: str
    duration: int | None
    skip_upload: bool
    current_step: int
    completed_steps: list[int]
    failed_step: int | None
    error: str | None
    output_path: str | None
    youtube_url: str | None
    artifacts: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []
    created_at: str
    updated_at: str

    @field_validator("completed_steps", mode="before")
    @classmethod
    def remove_duplicates(cls, v: list[int]) -> list[int]:
        return list(sorted(set(v)))


class VideoPipeline:
    def __init__(
        self,
        config: AppConfig,
        progress_display: Any = None,
    ) -> None:
        self.config = config
        self._workspace: Workspace | None = None
        self._progress: PipelineProgress | None = None
        self._progress_display = progress_display

    def run(
        self,
        title: str | None = None,
        format: str | None = None,
        lang: str | None = None,
        duration: int | None = None,
        skip_upload: bool = False,
    ) -> PipelineResult:
        """Run the complete video generation pipeline.

        This is the main entry point for creating a new video.

        Args:
            title: Video title (optional).
            format: Video format (short/long, optional).
            lang: Language code (optional).
            duration: Target duration in seconds (optional).
            skip_upload: Skip YouTube upload (default: False).

        Returns:
            PipelineResult with generation status and output.
        """
        import uuid
        from datetime import datetime

        video_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        workspace = Workspace(self.config.storage.temp_path, video_id)
        workspace.create()

        logger.info(f"Starting video generation: {video_id}")
        logger.info(f"Title: {title}")
        logger.info(f"Format: {format}")
        logger.info(f"Language: {lang}")
        logger.info(f"Duration: {duration}")

        return self.resume(
            video_id=video_id,
            from_step=PipelineStep.SCRIPT,
            title=title,
            format=format,
            lang=lang,
            duration=duration,
            skip_upload=skip_upload,
        )

    def _get_audio_duration(self, audio_path: Path) -> float:
        import subprocess

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            pass
        return 0.0

    def _validate_artifacts(
        self, state: PipelineState, workspace: Workspace, up_to_step: int
    ) -> bool:
        """Validate that required artifacts exist for resume."""
        if up_to_step >= 1:
            if not workspace.script_path.exists():
                logger.error("Script artifact missing for resume")
                return False
            if "script" not in state.artifacts:
                logger.warning("Script not tracked in state artifacts")

        if up_to_step >= 2:
            if not workspace.audio_path.exists():
                logger.error("Audio artifact missing for resume")
                return False
            if "audio" not in state.artifacts:
                logger.warning("Audio not tracked in state artifacts")

        if up_to_step >= 3:
            clips_dir = workspace.workspace_path / "clips"
            if not clips_dir.exists():
                logger.error("Clips directory missing for resume")
                return False
            clips = list(clips_dir.glob("*.mp4"))
            if not clips:
                logger.error("No clip artifacts found for resume")
                return False
            if "clips" not in state.artifacts:
                logger.warning("Clips not tracked in state artifacts")

        if up_to_step >= 4:
            if not workspace.video_raw_path.exists():
                logger.error("Raw video artifact missing for resume")
                return False
            if not workspace.final_path.exists():
                logger.error("Final video artifact missing for resume")
                return False

        if up_to_step >= 5:
            if not workspace.subtitles_path.exists():
                logger.error("Subtitles artifact missing for resume")
                return False

        if up_to_step >= 6:
            if not workspace.thumbnail_path.exists():
                logger.error("Thumbnail artifact missing for resume")
                return False

        return True

    def _cleanup_partial_artifacts(
        self, workspace: Workspace, state: PipelineState, failed_step: int
    ) -> None:
        """Clean up artifacts created after the failed step."""
        clips_dir = workspace.workspace_path / "clips"

        if failed_step >= 7:
            if workspace.final_path.exists():
                try:
                    workspace.final_path.unlink()
                    logger.info("Cleaned up final video")
                except Exception as e:
                    logger.warning(f"Failed to clean up final video: {e}")

        if failed_step >= 6:
            if workspace.thumbnail_path.exists():
                try:
                    workspace.thumbnail_path.unlink()
                    logger.info("Cleaned up thumbnail")
                except Exception as e:
                    logger.warning(f"Failed to clean up thumbnail: {e}")

        if failed_step >= 5:
            if workspace.subtitles_path.exists():
                try:
                    workspace.subtitles_path.unlink()
                    logger.info("Cleaned up subtitles")
                except Exception as e:
                    logger.warning(f"Failed to clean up subtitles: {e}")

        if failed_step >= 4:
            if workspace.video_raw_path.exists():
                try:
                    workspace.video_raw_path.unlink()
                    logger.info("Cleaned up raw video")
                except Exception as e:
                    logger.warning(f"Failed to clean up raw video: {e}")

        if failed_step >= 3:
            if clips_dir.exists():
                try:
                    for clip in clips_dir.glob("*.mp4"):
                        clip.unlink()
                    logger.info("Cleaned up clips")
                except Exception as e:
                    logger.warning(f"Failed to clean up clips: {e}")

    def _update_artifacts(self, state: PipelineState, workspace: Workspace) -> None:
        """Update artifacts dict with current workspace files."""
        if workspace.script_path.exists():
            state.artifacts["script"] = str(workspace.script_path)

        if workspace.audio_path.exists():
            state.artifacts["audio"] = str(workspace.audio_path)

        clips_dir = workspace.workspace_path / "clips"
        if clips_dir.exists():
            clips = list(clips_dir.glob("*.mp4"))
            if clips:
                state.artifacts["clips"] = [str(c) for c in clips]

        if workspace.video_raw_path.exists():
            state.artifacts["video_raw"] = str(workspace.video_raw_path)

        if workspace.final_path.exists():
            state.artifacts["final"] = str(workspace.final_path)

        if workspace.subtitles_path.exists():
            state.artifacts["subtitles"] = str(workspace.subtitles_path)

        if workspace.thumbnail_path.exists():
            state.artifacts["thumbnail"] = str(workspace.thumbnail_path)

    def _record_error(self, state: PipelineState, step: PipelineStep, error: Exception) -> None:
        """Record error information in state."""
        import traceback as tb

        error_dict = {
            "step": step.value,
            "step_name": step.name,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now().isoformat(),
            "traceback": "".join(tb.format_exception(type(error), error, error.__traceback__)),
        }
        state.errors.append(error_dict)

    def retry_step(self, video_id: str, step: PipelineStep) -> PipelineResult:
        if not validate_video_id(video_id):
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=[],
                failed_step=None,
                error="Invalid video_id format",
                output_path=None,
                youtube_url=None,
            )

        workspace = Workspace(self.config.storage.temp_path, video_id)

        if not workspace.workspace_path.exists():
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=[],
                failed_step=None,
                error=f"Workspace not found for video_id: {video_id}",
                output_path=None,
                youtube_url=None,
            )

        state = self._load_state(workspace)
        if state is None:
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=[],
                failed_step=None,
                error=f"State file not found for video_id: {video_id}",
                output_path=None,
                youtube_url=None,
            )

        step_value = step.value

        if step_value not in state.completed_steps:
            logger.info(f"Step {step.name} was not completed, cannot retry")
            return self.resume(video_id, step)

        failed_step: PipelineStep | None = (
            PipelineStep(state.failed_step) if state.failed_step else None
        )
        if failed_step and failed_step.value != step_value:
            logger.info(f"Step {step.name} did not fail, current failed step: {failed_step}")
            return self.resume(video_id, step)

        completed_steps = [PipelineStep(s) for s in state.completed_steps if s < step_value]
        error: str | None = None
        output_path = Path(state.output_path) if state.output_path else None
        youtube_url = state.youtube_url

        script = ""
        audio_duration = 0.0
        keywords: list[str] = []
        clips: list[Path] = []

        if step_value > 1:
            if not workspace.script_path.exists():
                return PipelineResult(
                    video_id=video_id,
                    status="failed",
                    completed_steps=completed_steps,
                    failed_step=PipelineStep.SCRIPT,
                    error="Script artifact missing for retry",
                    output_path=output_path,
                    youtube_url=youtube_url,
                )
            script = workspace.script_path.read_text(encoding="utf-8")

        if step_value > 2:
            audio_duration = self._get_audio_duration(workspace.audio_path)
            if audio_duration == 0.0:
                return PipelineResult(
                    video_id=video_id,
                    status="failed",
                    completed_steps=completed_steps,
                    failed_step=PipelineStep.AUDIO,
                    error="Audio artifact missing or invalid for retry",
                    output_path=output_path,
                    youtube_url=youtube_url,
                )

        if step_value > 3:
            try:
                llm = LLM(self.config.llm)
                keywords = llm.extract_keywords(script)
                # Cleanup LLM to free VRAM
                llm.cleanup()
                del llm
            except Exception as e:
                return PipelineResult(
                    video_id=video_id,
                    status="failed",
                    completed_steps=completed_steps,
                    failed_step=PipelineStep.VISUALS,
                    error=f"Failed to extract keywords: {e}",
                    output_path=output_path,
                    youtube_url=youtube_url,
                )

        self._cleanup_partial_artifacts(workspace, state, step_value - 1)

        state.failed_step = None
        state.error = None
        state.current_step = step_value
        state.updated_at = datetime.now().isoformat()
        self._save_state(state)

        if step_value == 1:
            try:
                llm = LLM(self.config.llm)
                self._progress = PipelineProgress(video_id, PipelineStep.SCRIPT, 0.0)

                duration = (
                    state.duration if state.duration else (180 if state.format == "long" else 60)
                )
                script = llm.generate_script(state.title, duration, state.lang)
                workspace.script_path.write_text(script, encoding="utf-8")
                completed_steps.append(PipelineStep.SCRIPT)
                state.completed_steps.append(1)
                state.current_step = 2
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Script regenerated: %s", workspace.script_path)

                # Cleanup LLM to free VRAM
                llm.cleanup()
                del llm

                if self._progress_display:
                    self._progress_display.update_script_content(script)
                    self._progress_display.update_artifact_path(0, str(workspace.script_path))

            except Exception as e:
                failed_step = PipelineStep.SCRIPT
                error = str(e)
                state.failed_step = 1
                state.error = error
                self._record_error(state, PipelineStep.SCRIPT, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Script generation failed")

        if error:
            self._workspace = None
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=completed_steps,
                failed_step=failed_step,
                error=error,
                output_path=output_path,
                youtube_url=youtube_url,
            )

        if step_value == 2:
            try:
                tts = TTS(self.config.tts)
                self._progress = PipelineProgress(video_id, PipelineStep.AUDIO, 0.0)

                audio_duration = tts.synthesize_script(script, workspace.audio_path)
                completed_steps.append(PipelineStep.AUDIO)
                state.completed_steps.append(2)
                state.current_step = 3
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info(
                    "Audio regenerated: %s (duration: %.2fs)", workspace.audio_path, audio_duration
                )

                if self._progress_display:
                    self._progress_display.update_artifact_path(1, str(workspace.audio_path))

            except Exception as e:
                failed_step = PipelineStep.AUDIO
                error = str(e)
                state.failed_step = 2
                state.error = error
                self._record_error(state, PipelineStep.AUDIO, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Audio generation failed")

        if error:
            self._workspace = None
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=completed_steps,
                failed_step=failed_step,
                error=error,
                output_path=output_path,
                youtube_url=youtube_url,
            )

        if step_value == 3:
            clips_dir = workspace.workspace_path / "clips"
            clips_dir.mkdir(exist_ok=True)

            try:
                llm = LLM(self.config.llm)
                self._progress = PipelineProgress(video_id, PipelineStep.VISUALS, 0.0)

                if not keywords:
                    keywords = llm.extract_keywords(script)

                # Cleanup LLM to free VRAM
                llm.cleanup()
                del llm

                stock_manager = StockManager(self.config.visuals)

                if self.config.visuals.visual_llm and self.config.visuals.mode in (
                    "stock",
                    "hybrid",
                ):
                    try:
                        logger.info("Using VisualKeywordExtractor for segment-based clips")
                        keyword_extractor = VisualKeywordExtractor(self.config.visuals.visual_llm)
                        segments_with_keywords = keyword_extractor.extract_keywords_per_segment(
                            script
                        )
                        # Cleanup VisualKeywordExtractor LLM to free VRAM
                        keyword_extractor.cleanup()
                        del keyword_extractor
                        clips = stock_manager.get_clips_for_segments(
                            segments_with_keywords, clips_dir
                        )

                        if not clips and self.config.visuals.mode == "hybrid":
                            stock_clips = stock_manager.get_clips_for_script(
                                script, keywords, audio_duration * 0.5, clips_dir
                            )
                            clips.extend(stock_clips)
                    except Exception as e:
                        logger.warning(
                            "VisualKeywordExtractor failed: %s, falling back to global keywords",
                            str(e),
                        )
                        if self.config.visuals.mode == "stock":
                            clips = stock_manager.get_clips_for_script(
                                script, keywords, audio_duration, clips_dir
                            )
                        elif self.config.visuals.mode == "hybrid":
                            stock_clips = stock_manager.get_clips_for_script(
                                script, keywords, audio_duration * 0.5, clips_dir
                            )
                            clips.extend(stock_clips)
                            if self.config.visuals.local_path:
                                local_manager = LocalAssetsManager(
                                    Path(self.config.visuals.local_path), True
                                )
                                assets = local_manager.get_random_sequence(audio_duration * 0.5)
                                local_clips = local_manager.prepare_clips(assets)
                                clips.extend(local_clips)
                        else:
                            clips = []

                elif self.config.visuals.mode == "stock":
                    clips = stock_manager.get_clips_for_script(
                        script, keywords, audio_duration, clips_dir
                    )
                elif self.config.visuals.mode == "local" and self.config.visuals.local_path:
                    local_manager = LocalAssetsManager(Path(self.config.visuals.local_path), True)
                    assets = local_manager.get_random_sequence(audio_duration)
                    clips = local_manager.prepare_clips(assets)
                elif self.config.visuals.mode == "hybrid":
                    stock_clips = stock_manager.get_clips_for_script(
                        script, keywords, audio_duration * 0.5, clips_dir
                    )
                    clips.extend(stock_clips)
                    if self.config.visuals.local_path:
                        local_manager = LocalAssetsManager(
                            Path(self.config.visuals.local_path), True
                        )
                        assets = local_manager.get_random_sequence(audio_duration * 0.5)
                        local_clips = local_manager.prepare_clips(assets)
                        clips.extend(local_clips)
                else:
                    for i in range(5):
                        clip_path = clips_dir / f"mock_clip_{i}.mp4"
                        clip_path.write_bytes(b"MOCK_VIDEO_DATA")
                        clips.append(clip_path)

                completed_steps.append(PipelineStep.VISUALS)
                state.completed_steps.append(3)
                state.current_step = 4
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Visuals regenerated: %d clips", len(clips))

                if self._progress_display:
                    self._progress_display.update_artifact_path(2, str(clips_dir))

            except Exception as e:
                failed_step = PipelineStep.VISUALS
                error = str(e)
                state.failed_step = 3
                state.error = error
                self._record_error(state, PipelineStep.VISUALS, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Visuals collection failed")

        if error:
            self._workspace = None
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=completed_steps,
                failed_step=failed_step,
                error=error,
                output_path=output_path,
                youtube_url=youtube_url,
            )

        if step_value == 4:
            try:
                mock_detected = False
                for clip in clips:
                    if clip.exists() and clip.stat().st_size < 1000:
                        content = clip.read_bytes()
                        if content == b"MOCK_VIDEO_DATA":
                            mock_detected = True
                            break

                if mock_detected:
                    raise ValueError(
                        "No valid video clips found. The system used mock/placeholder data "
                        "instead of real videos.\n"
                        "To fix this, please configure at least one stock video provider:\n"
                        "  1. Run: auto-video setup visuals\n"
                        "  2. Enable 'pexels' and/or 'pixabay' and enter your API keys\n"
                        "  3. Or configure a local assets folder with your own videos\n"
                        f"  4. Then run: auto-video resume --video-id {video_id}"
                    )

                if self._progress_display:
                    self._progress_display.start_step(3, "Montage vidéo...")

                composer = VideoComposer(
                    gpu_acceleration=self.config.video.gpu_acceleration,
                    preset=self.config.video.preset,
                    quality=self.config.video.quality,
                )
                self._progress = PipelineProgress(video_id, PipelineStep.MONTAGE, 0.0)

                composer.concatenate_clips(clips, workspace.video_raw_path, audio_duration)
                composer.trim_video_to_duration(
                    workspace.video_raw_path, workspace.video_raw_path, audio_duration
                )
                composer.add_audio(
                    workspace.video_raw_path, workspace.audio_path, workspace.final_path
                )
                composer.apply_format_with_temp(
                    workspace.final_path, workspace.final_path, state.format
                )

                completed_steps.append(PipelineStep.MONTAGE)
                state.completed_steps.append(4)
                state.current_step = 5
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Video montage regenerated: %s", workspace.final_path)

                if self._progress_display:
                    self._progress_display.update_artifact_path(3, str(workspace.final_path))
                    self._progress_display.complete_step(3, "Vidéo montée")

            except Exception as e:
                failed_step = PipelineStep.MONTAGE
                error = str(e)
                if self._progress_display:
                    self._progress_display.fail_step(3, str(e))
                state.failed_step = 4
                state.error = error
                self._record_error(state, PipelineStep.MONTAGE, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Video montage failed")

        if error:
            self._workspace = None
            return PipelineResult(
                video_id=workspace.video_id,
                status="partial",
                completed_steps=completed_steps,
                failed_step=failed_step,
                error=error,
                output_path=output_path,
                youtube_url=youtube_url,
            )

        try:
            if self._progress_display:
                self._progress_display.start_step(4, "Génération des sous-titres...")

            subtitle_gen = SubtitleGenerator()
            self._progress = PipelineProgress(workspace.video_id, PipelineStep.SUBTITLES, 0.0)

            style = SubtitleStyle()
            transcription_result = subtitle_gen.transcribe(workspace.audio_path)
            subtitle_gen.generate_srt(transcription_result, workspace.subtitles_path, style)
            subtitle_gen.burn_subtitles(
                workspace.final_path, workspace.subtitles_path, workspace.final_path, style
            )

            completed_steps.append(PipelineStep.SUBTITLES)
            state.completed_steps.append(5)
            state.current_step = 6
            state.updated_at = datetime.now().isoformat()
            self._update_artifacts(state, workspace)
            self._save_state(state)
            logger.info("Subtitles generated and burned: %s", workspace.subtitles_path)

            if self._progress_display:
                self._progress_display.update_artifact_path(4, str(workspace.subtitles_path))
                self._progress_display.complete_step(4, "Sous-titres ajoutés")

        except Exception as e:
            failed_step = PipelineStep.SUBTITLES
            error = str(e)
            if self._progress_display:
                self._progress_display.fail_step(4, str(e))
            state.failed_step = 5
            state.error = error
            self._record_error(state, PipelineStep.SUBTITLES, e)
            state.updated_at = datetime.now().isoformat()
            self._save_state(state)
            logger.exception("Subtitle generation failed")

        if error:
            self._workspace = None
            return PipelineResult(
                video_id=workspace.video_id,
                status="partial",
                completed_steps=completed_steps,
                failed_step=failed_step,
                error=error,
                output_path=workspace.final_path if workspace.final_path.exists() else None,
                youtube_url=youtube_url,
            )

        try:
            if self._progress_display:
                self._progress_display.start_step(5, "Génération de la miniature...")

            thumbnail_gen = ThumbnailGenerator(self.config.image_gen, self.config.llm)
            self._progress = PipelineProgress(workspace.video_id, PipelineStep.THUMBNAIL, 0.0)

            thumbnail_gen.generate_from_context(title or "Video", script, workspace.thumbnail_path)

            # Cleanup ThumbnailGenerator LLM to free VRAM
            thumbnail_gen.cleanup()
            del thumbnail_gen

            completed_steps.append(PipelineStep.THUMBNAIL)
            state.completed_steps.append(6)
            state.current_step = 7
            state.updated_at = datetime.now().isoformat()
            self._update_artifacts(state, workspace)
            self._save_state(state)
            logger.info("Thumbnail generated: %s", workspace.thumbnail_path)

            if self._progress_display:
                self._progress_display.update_artifact_path(5, str(workspace.thumbnail_path))
                self._progress_display.complete_step(5, "Miniature créée")

        except Exception as e:
            failed_step = PipelineStep.THUMBNAIL
            error = str(e)
            if self._progress_display:
                self._progress_display.fail_step(5, str(e))
            state.failed_step = 6
            state.error = error
            self._record_error(state, PipelineStep.THUMBNAIL, e)
            state.updated_at = datetime.now().isoformat()
            self._save_state(state)
            logger.exception("Thumbnail generation failed")

        if error:
            self._workspace = None
            return PipelineResult(
                video_id=workspace.video_id,
                status="partial",
                completed_steps=completed_steps,
                failed_step=failed_step,
                error=error,
                output_path=workspace.final_path if workspace.final_path.exists() else None,
                youtube_url=youtube_url,
            )

        output_path = workspace.final_path if workspace.final_path.exists() else None

        if not skip_upload and self.config.youtube.enabled:
            try:
                if self._progress_display:
                    self._progress_display.start_step(6, "Upload vers YouTube...")

                uploader = YouTubeUploader(self.config.youtube.credentials_path or Path())
                self._progress = PipelineProgress(workspace.video_id, PipelineStep.UPLOAD, 0.0)

                uploader.authenticate()

                tags = keywords if self.config.youtube.auto_tags else []
                upload_result = uploader.upload(
                    video_path=workspace.final_path,
                    title=title or "Auto-generated video",
                    description=script[:500],
                    tags=tags,
                    thumbnail_path=workspace.thumbnail_path,
                    privacy=self.config.youtube.default_privacy,
                )

                youtube_url = upload_result.url
                completed_steps.append(PipelineStep.UPLOAD)
                state.completed_steps.append(7)
                state.current_step = 7
                state.youtube_url = youtube_url
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Video uploaded to YouTube: %s", youtube_url)

                if self._progress_display:
                    self._progress_display.complete_step(6, f"Uploadé: {youtube_url}")

            except Exception as e:
                failed_step = PipelineStep.UPLOAD
                error = str(e)
                if self._progress_display:
                    self._progress_display.fail_step(6, str(e))
                state.failed_step = 7
                state.error = error
                self._record_error(state, PipelineStep.UPLOAD, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("YouTube upload failed")

                self._workspace = None
                return PipelineResult(
                    video_id=workspace.video_id,
                    status="partial",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=output_path,
                    youtube_url=None,
                )

        if self.config.storage.videos_path:
            output_path = workspace.copy_to_output(self.config.storage.videos_path)
            state.output_path = str(output_path)
            state.updated_at = datetime.now().isoformat()
            self._save_state(state)
            logger.info("Video copied to output: %s", output_path)

        self._workspace = None

        if self._progress_display:
            self._progress_display.stop()

        return PipelineResult(
            video_id=workspace.video_id,
            status="success",
            completed_steps=completed_steps,
            failed_step=None,
            error=None,
            output_path=output_path,
            youtube_url=youtube_url,
        )

    def resume(
        self,
        video_id: str,
        from_step: PipelineStep,
        title: str | None = None,
        format: str | None = None,
        lang: str | None = None,
        duration: int | None = None,
        skip_upload: bool = False,
    ) -> PipelineResult:
        from datetime import datetime

        if not validate_video_id(video_id):
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=[],
                failed_step=None,
                error="Invalid video_id format",
                output_path=None,
                youtube_url=None,
            )

        workspace = Workspace(self.config.storage.temp_path, video_id)

        if not workspace.workspace_path.exists():
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=[],
                failed_step=None,
                error=f"Workspace not found for video_id: {video_id}",
                output_path=None,
                youtube_url=None,
            )
        state = self._load_state(workspace)

        if state is None:
            state = PipelineState(
                video_id=video_id,
                title=title,
                format=format or self.config.default_format,
                lang=lang or self.config.default_lang,
                duration=duration,
                skip_upload=skip_upload,
                current_step=from_step,
                completed_steps=[],
                failed_step=None,
                error=None,
                output_path="",
                youtube_url=None,
                artifacts={},
                errors=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            self._save_state(state)
            logger.info(f"Created new state for video: {video_id}")

        from_step_value = from_step.value
        if from_step_value not in [1, 2, 3, 4, 5, 6, 7]:
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=[],
                failed_step=None,
                error=f"Invalid step: {from_step}",
                output_path=None,
                youtube_url=None,
            )

        self._workspace = workspace
        self._progress = PipelineProgress(video_id, from_step, 0.0)

        if self._progress_display:
            self._progress_display.start()

        if not self._validate_artifacts(state, workspace, from_step_value - 1):
            return PipelineResult(
                video_id=video_id,
                status="failed",
                completed_steps=[],
                failed_step=None,
                error=f"Artifact validation failed for resume from step {from_step.name}",
                output_path=None,
                youtube_url=None,
            )

        completed_steps = [PipelineStep(s) for s in state.completed_steps if s < from_step_value]
        failed_step: PipelineStep | None = None
        error: str | None = None
        output_path = Path(state.output_path) if state.output_path else None
        youtube_url = state.youtube_url

        script = ""
        audio_duration = 0.0
        keywords: list[str] = []

        if from_step_value > 1:
            try:
                script = workspace.script_path.read_text(encoding="utf-8")
            except Exception as e:
                failed_step = PipelineStep.SCRIPT
                error = f"Failed to load script: {e}"
                return PipelineResult(
                    video_id=video_id,
                    status="failed",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=output_path,
                    youtube_url=youtube_url,
                )

        if from_step_value > 2:
            try:
                audio_duration = self._get_audio_duration(workspace.audio_path)
            except Exception as e:
                failed_step = PipelineStep.AUDIO
                error = f"Failed to load audio: {e}"
                return PipelineResult(
                    video_id=video_id,
                    status="failed",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=output_path,
                    youtube_url=youtube_url,
                )

        if from_step_value > 3:
            try:
                llm = LLM(self.config.llm)
                keywords = llm.extract_keywords(script)
                # Cleanup LLM to free VRAM
                llm.cleanup()
                del llm
            except Exception as e:
                failed_step = PipelineStep.VISUALS
                error = f"Failed to load visuals: {e}"
                return PipelineResult(
                    video_id=video_id,
                    status="failed",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=output_path,
                    youtube_url=youtube_url,
                )

        duration = state.duration if state.duration else (180 if state.format == "long" else 60)

        if from_step_value <= 2:
            try:
                llm = LLM(self.config.llm)
                self._progress = PipelineProgress(video_id, PipelineStep.SCRIPT, 0.0)

                if self._progress_display:
                    self._progress_display.start_step(0, "Génération du script...")

                script = llm.generate_script(state.title, duration, state.lang)
                workspace.script_path.write_text(script, encoding="utf-8")
                completed_steps.append(PipelineStep.SCRIPT)
                state.completed_steps.append(1)
                state.current_step = max(state.current_step, 2)
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Script generated: %s", workspace.script_path)

                # Cleanup LLM to free VRAM
                llm.cleanup()
                del llm

                if self._progress_display:
                    self._progress_display.update_script_content(script)
                    self._progress_display.update_artifact_path(0, str(workspace.script_path))
                    self._progress_display.complete_step(0, "Script généré")

            except Exception as e:
                failed_step = PipelineStep.SCRIPT
                error = str(e)
                if self._progress_display:
                    self._progress_display.fail_step(0, str(e))
                state.failed_step = 1
                state.error = error
                self._record_error(state, PipelineStep.SCRIPT, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Script generation failed")

        if error or from_step_value > 2:
            if error:
                self._workspace = None
                return PipelineResult(
                    video_id=video_id,
                    status="failed" if from_step_value <= 2 else "partial",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=output_path,
                    youtube_url=youtube_url,
                )

        if from_step_value <= 3:
            try:
                tts = TTS(self.config.tts)
                self._progress = PipelineProgress(video_id, PipelineStep.AUDIO, 0.0)

                if self._progress_display:
                    self._progress_display.start_step(1, "Synthèse vocale...")

                audio_duration = tts.synthesize_script(script, workspace.audio_path)
                completed_steps.append(PipelineStep.AUDIO)
                state.completed_steps.append(2)
                state.current_step = max(state.current_step, 3)
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info(
                    "Audio generated: %s (duration: %.2fs)", workspace.audio_path, audio_duration
                )

                if self._progress_display:
                    self._progress_display.update_artifact_path(1, str(workspace.audio_path))
                    self._progress_display.complete_step(1, "Audio généré")

            except Exception as e:
                failed_step = PipelineStep.AUDIO
                error = str(e)
                if self._progress_display:
                    self._progress_display.fail_step(1, str(e))
                state.failed_step = 2
                state.error = error
                self._record_error(state, PipelineStep.AUDIO, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Audio generation failed")

        if error or from_step_value > 3:
            if error:
                self._workspace = None
                return PipelineResult(
                    video_id=video_id,
                    status="partial",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=output_path,
                    youtube_url=youtube_url,
                )

        clips_dir = workspace.workspace_path / "clips"
        clips_dir.mkdir(exist_ok=True)
        clips: list[Path] = []

        if from_step_value <= 4:
            try:
                llm = LLM(self.config.llm)
                self._progress = PipelineProgress(video_id, PipelineStep.VISUALS, 0.0)

                if self._progress_display:
                    self._progress_display.start_step(2, "Recherche de clips vidéo...")

                if not keywords:
                    keywords = llm.extract_keywords(script)

                # Cleanup LLM to free VRAM
                llm.cleanup()
                del llm

                stock_manager = StockManager(self.config.visuals)

                if self.config.visuals.visual_llm and self.config.visuals.mode in (
                    "stock",
                    "hybrid",
                ):
                    try:
                        logger.info("Using VisualKeywordExtractor for segment-based clips")
                        keyword_extractor = VisualKeywordExtractor(self.config.visuals.visual_llm)
                        segments_with_keywords = keyword_extractor.extract_keywords_per_segment(
                            script
                        )
                        # Cleanup VisualKeywordExtractor LLM to free VRAM
                        keyword_extractor.cleanup()
                        del keyword_extractor
                        clips = stock_manager.get_clips_for_segments(
                            segments_with_keywords, clips_dir
                        )

                        if not clips and self.config.visuals.mode == "hybrid":
                            stock_clips = stock_manager.get_clips_for_script(
                                script, keywords, audio_duration * 0.5, clips_dir
                            )
                            clips.extend(stock_clips)
                    except Exception as e:
                        logger.warning(
                            "VisualKeywordExtractor failed: %s, falling back to global keywords",
                            str(e),
                        )
                        if self.config.visuals.mode == "stock":
                            clips = stock_manager.get_clips_for_script(
                                script, keywords, audio_duration, clips_dir
                            )
                        elif self.config.visuals.mode == "hybrid":
                            stock_clips = stock_manager.get_clips_for_script(
                                script, keywords, audio_duration * 0.5, clips_dir
                            )
                            clips.extend(stock_clips)
                            if self.config.visuals.local_path:
                                local_manager = LocalAssetsManager(
                                    Path(self.config.visuals.local_path), True
                                )
                                assets = local_manager.get_random_sequence(audio_duration * 0.5)
                                local_clips = local_manager.prepare_clips(assets)
                                clips.extend(local_clips)
                        else:
                            clips = []

                elif self.config.visuals.mode == "stock":
                    clips = stock_manager.get_clips_for_script(
                        script, keywords, audio_duration, clips_dir
                    )
                elif self.config.visuals.mode == "local" and self.config.visuals.local_path:
                    local_manager = LocalAssetsManager(Path(self.config.visuals.local_path), True)
                    assets = local_manager.get_random_sequence(audio_duration)
                    clips = local_manager.prepare_clips(assets)
                elif self.config.visuals.mode == "hybrid":
                    stock_clips = stock_manager.get_clips_for_script(
                        script, keywords, audio_duration * 0.5, clips_dir
                    )
                    clips.extend(stock_clips)
                    if self.config.visuals.local_path:
                        local_manager = LocalAssetsManager(
                            Path(self.config.visuals.local_path), True
                        )
                        assets = local_manager.get_random_sequence(audio_duration * 0.5)
                        local_clips = local_manager.prepare_clips(assets)
                        clips.extend(local_clips)
                else:
                    for i in range(5):
                        clip_path = clips_dir / f"mock_clip_{i}.mp4"
                        clip_path.write_bytes(b"MOCK_VIDEO_DATA")
                        clips.append(clip_path)

                completed_steps.append(PipelineStep.VISUALS)
                state.completed_steps.append(3)
                state.current_step = max(state.current_step, 4)
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Visuals collected: %d clips", len(clips))

                if self._progress_display:
                    self._progress_display.update_artifact_path(2, str(clips_dir))
                    self._progress_display.complete_step(2, f"{len(clips)} clips collectés")

            except Exception as e:
                failed_step = PipelineStep.VISUALS
                error = str(e)
                if self._progress_display:
                    self._progress_display.fail_step(2, str(e))
                state.failed_step = 3
                state.error = error
                self._record_error(state, PipelineStep.VISUALS, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Visuals collection failed")

        if error or from_step_value > 4:
            if error:
                self._workspace = None
                return PipelineResult(
                    video_id=video_id,
                    status="partial",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=output_path,
                    youtube_url=youtube_url,
                )

        if from_step_value <= 5:
            try:
                mock_detected = False
                for clip in clips:
                    if clip.exists() and clip.stat().st_size < 1000:
                        content = clip.read_bytes()
                        if content == b"MOCK_VIDEO_DATA":
                            mock_detected = True
                            break

                if mock_detected:
                    raise ValueError(
                        "No valid video clips found. The system used mock/placeholder data "
                        "instead of real videos.\n"
                        "To fix this, please configure at least one stock video provider:\n"
                        "  1. Run: auto-video setup visuals\n"
                        "  2. Enable 'pexels' and/or 'pixabay' and enter your API keys\n"
                        "  3. Or configure a local assets folder with your own videos\n"
                        f"  4. Then run: auto-video resume --video-id {video_id}"
                    )

                if self._progress_display:
                    self._progress_display.start_step(3, "Montage vidéo...")

                composer = VideoComposer(
                    gpu_acceleration=self.config.video.gpu_acceleration,
                    preset=self.config.video.preset,
                    quality=self.config.video.quality,
                )
                self._progress = PipelineProgress(video_id, PipelineStep.MONTAGE, 0.0)

                composer.concatenate_clips(clips, workspace.video_raw_path, audio_duration)
                composer.add_audio(
                    workspace.video_raw_path, workspace.audio_path, workspace.final_path
                )
                composer.apply_format_with_temp(
                    workspace.final_path, workspace.final_path, state.format
                )

                completed_steps.append(PipelineStep.MONTAGE)
                state.completed_steps.append(4)
                state.current_step = max(state.current_step, 5)
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Video montage completed: %s", workspace.final_path)

                if self._progress_display:
                    self._progress_display.update_artifact_path(3, str(workspace.final_path))
                    self._progress_display.complete_step(3, "Vidéo montée")

            except Exception as e:
                failed_step = PipelineStep.MONTAGE
                error = str(e)
                if self._progress_display:
                    self._progress_display.fail_step(3, str(e))
                state.failed_step = 4
                state.error = error
                self._record_error(state, PipelineStep.MONTAGE, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Video montage failed")

        if error or from_step_value > 5:
            if error:
                self._workspace = None
                return PipelineResult(
                    video_id=video_id,
                    status="partial",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=output_path,
                    youtube_url=youtube_url,
                )

        if from_step_value <= 6:
            try:
                subtitle_gen = SubtitleGenerator()
                self._progress = PipelineProgress(video_id, PipelineStep.SUBTITLES, 0.0)

                if self._progress_display:
                    self._progress_display.start_step(4, "Génération des sous-titres...")

                style = SubtitleStyle()
                transcription_result = subtitle_gen.transcribe(workspace.audio_path)
                subtitle_gen.generate_srt(transcription_result, workspace.subtitles_path, style)
                subtitle_gen.burn_subtitles(
                    workspace.final_path, workspace.subtitles_path, workspace.final_path, style
                )

                completed_steps.append(PipelineStep.SUBTITLES)
                state.completed_steps.append(5)
                state.current_step = max(state.current_step, 6)
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Subtitles generated and burned: %s", workspace.subtitles_path)

                if self._progress_display:
                    self._progress_display.update_artifact_path(4, str(workspace.subtitles_path))
                    self._progress_display.complete_step(4, "Sous-titres ajoutés")

            except Exception as e:
                failed_step = PipelineStep.SUBTITLES
                error = str(e)
                if self._progress_display:
                    self._progress_display.fail_step(4, str(e))
                state.failed_step = 5
                state.error = error
                self._record_error(state, PipelineStep.SUBTITLES, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Subtitle generation failed")

        if error or from_step_value > 6:
            if error:
                self._workspace = None
                return PipelineResult(
                    video_id=video_id,
                    status="partial",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=workspace.final_path if workspace.final_path.exists() else None,
                    youtube_url=youtube_url,
                )

        if from_step_value <= 7:
            try:
                thumbnail_gen = ThumbnailGenerator(self.config.image_gen, self.config.llm)
                self._progress = PipelineProgress(video_id, PipelineStep.THUMBNAIL, 0.0)

                if self._progress_display:
                    self._progress_display.start_step(5, "Génération de la miniature...")

                thumbnail_gen.generate_from_context(
                    state.title or "Video", script, workspace.thumbnail_path
                )

                # Cleanup ThumbnailGenerator LLM to free VRAM
                thumbnail_gen.cleanup()
                del thumbnail_gen

                completed_steps.append(PipelineStep.THUMBNAIL)
                state.completed_steps.append(6)
                state.current_step = max(state.current_step, 7)
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Thumbnail generated: %s", workspace.thumbnail_path)

                if self._progress_display:
                    self._progress_display.update_artifact_path(5, str(workspace.thumbnail_path))
                    self._progress_display.complete_step(5, "Miniature créée")

            except Exception as e:
                failed_step = PipelineStep.THUMBNAIL
                error = str(e)
                if self._progress_display:
                    self._progress_display.fail_step(5, str(e))
                state.failed_step = 6
                state.error = error
                self._record_error(state, PipelineStep.THUMBNAIL, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("Thumbnail generation failed")

        if error or from_step_value > 7:
            if error:
                self._workspace = None
                return PipelineResult(
                    video_id=video_id,
                    status="partial",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=workspace.final_path if workspace.final_path.exists() else None,
                    youtube_url=youtube_url,
                )

        output_path = workspace.final_path if workspace.final_path.exists() else None

        if not state.skip_upload and self.config.youtube.enabled:
            try:
                uploader = YouTubeUploader(self.config.youtube.credentials_path or Path())
                self._progress = PipelineProgress(video_id, PipelineStep.UPLOAD, 0.0)

                if self._progress_display:
                    self._progress_display.start_step(6, "Upload vers YouTube...")

                uploader.authenticate()

                tags = keywords if self.config.youtube.auto_tags else []
                upload_result = uploader.upload(
                    video_path=workspace.final_path,
                    title=state.title or "Auto-generated video",
                    description=script[:500],
                    tags=tags,
                    thumbnail_path=workspace.thumbnail_path,
                    privacy=self.config.youtube.default_privacy,
                )

                youtube_url = upload_result.url
                completed_steps.append(PipelineStep.UPLOAD)
                state.completed_steps.append(7)
                state.current_step = 7
                state.youtube_url = youtube_url
                state.updated_at = datetime.now().isoformat()
                self._update_artifacts(state, workspace)
                self._save_state(state)
                logger.info("Video uploaded to YouTube: %s", youtube_url)

                if self._progress_display:
                    self._progress_display.complete_step(6, f"Uploadé: {youtube_url}")

            except Exception as e:
                failed_step = PipelineStep.UPLOAD
                error = str(e)
                if self._progress_display:
                    self._progress_display.fail_step(6, str(e))
                state.failed_step = 7
                state.error = error
                self._record_error(state, PipelineStep.UPLOAD, e)
                state.updated_at = datetime.now().isoformat()
                self._save_state(state)
                logger.exception("YouTube upload failed")

                self._workspace = None
                return PipelineResult(
                    video_id=video_id,
                    status="partial",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=error,
                    output_path=output_path,
                    youtube_url=None,
                )

        if self.config.storage.videos_path:
            output_path = workspace.copy_to_output(self.config.storage.videos_path)
            state.output_path = str(output_path)
            state.updated_at = datetime.now().isoformat()
            self._save_state(state)
            logger.info("Video copied to output: %s", output_path)

        if self._progress_display:
            self._progress_display.stop()

        self._workspace = None
        return PipelineResult(
            video_id=video_id,
            status="success",
            completed_steps=completed_steps,
            failed_step=None,
            error=None,
            output_path=output_path,
            youtube_url=youtube_url,
        )

    def get_progress(self) -> PipelineProgress | None:
        return self._progress

    def _save_state(self, state: PipelineState) -> None:
        if self._workspace is None:
            return
        self._workspace.state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def _load_state(self, workspace: Workspace) -> PipelineState | None:
        if not workspace.state_path.exists():
            return None
        try:
            data = json.loads(workspace.state_path.read_text(encoding="utf-8"))
            return PipelineState(**data)
        except Exception:
            return None
