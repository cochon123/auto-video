"""Logging system for auto-video."""

import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Any

from auto_video.core.pipeline import PipelineStep
from auto_video.utils.workspace import Workspace

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FORMAT_WITH_VIDEO = "%(asctime)s [%(levelname)s] %(name)s: [%(video_id)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class VideoAwareFormatter(logging.Formatter):
    """Formatter that handles missing video_id gracefully."""

    def __init__(self, fmt: str | None = None, datefmt: str | None = None, style: str = "%") -> None:
        """Initialize the formatter.

        Args:
            fmt: Format string.
            datefmt: Date format string.
            style: Style of the format string (%, {, or $).
        """
        super().__init__(fmt, datefmt, style)

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record, adding default video_id if missing.

        Args:
            record: The log record to format.

        Returns:
            The formatted log message.
        """
        # Add default video_id if not present
        if not hasattr(record, "video_id"):
            record.video_id = "N/A"
        return super().format(record)


class VideoLogger(logging.LoggerAdapter[logging.Logger]):
    """Logger scoped to a specific video."""

    extra: dict[str, Any]

    def __init__(self, video_id: str, workspace: Workspace) -> None:
        """Initialize video logger.

        Args:
            video_id: Video identifier.
            workspace: Workspace instance for file logging.
        """
        self.video_id = video_id
        self.workspace = workspace
        self._start_times: dict[PipelineStep, float] = {}
        self._api_call_count = 0

        base_logger = logging.getLogger("auto_video")
        super().__init__(base_logger, {"video_id": video_id})

        self._setup_file_handler()

    def _setup_file_handler(self) -> None:
        """Setup file handler for workspace-specific logging."""
        try:
            self.workspace.workspace_path.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(self.workspace.logs_path, mode="a", encoding="utf-8")
            file_handler.setFormatter(VideoAwareFormatter(LOG_FORMAT_WITH_VIDEO, LOG_DATE_FORMAT))
            file_handler.setLevel(logging.DEBUG)

            self.logger.addHandler(file_handler)
        except Exception:
            pass

    def log_step_start(self, step: PipelineStep) -> None:
        """Log start of a pipeline step.

        Args:
            step: Pipeline step being started.
        """
        self._start_times[step] = time.time()
        self.info(f"Starting step: {step.name}")

    def log_step_end(self, step: PipelineStep, duration: float | None = None) -> None:
        """Log completion of a pipeline step.

        Args:
            step: Pipeline step being completed.
            duration: Optional duration override in seconds.
        """
        if duration is None:
            start_time = self._start_times.get(step)
            if start_time is not None:
                duration = time.time() - start_time
            else:
                duration = 0.0

        self.info(f"Completed step: {step.name} (duration: {duration:.2f}s)")
        self._start_times.pop(step, None)

    def log_step_error(self, step: PipelineStep, error: Exception) -> None:
        """Log error in a pipeline step.

        Args:
            step: Pipeline step that failed.
            error: Exception that was raised.
        """
        start_time = self._start_times.get(step)
        duration = (time.time() - start_time) if start_time else 0.0

        self.error(
            f"Error in step: {step.name} (duration: {duration:.2f}s) - "
            f"{type(error).__name__}: {error}"
        )
        self._start_times.pop(step, None)

    def log_api_call(self, provider: str, model: str, tokens: int) -> None:
        """Log API call without exposing secrets.

        Args:
            provider: API provider name (e.g., "openai", "anthropic").
            model: Model name (e.g., "gpt-4", "claude-3").
            tokens: Number of tokens used.
        """
        self._api_call_count += 1
        self.info(f"API call #{self._api_call_count}: {provider}/{model} - {tokens} tokens")


def setup_logging(verbose: bool = False, log_file: Path | None = None) -> None:
    """Configure logging for the auto-video application.

    Args:
        verbose: If True, set level to DEBUG. Otherwise, INFO.
        log_file: Optional path to a log file. If provided, logs will be written to this file.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(VideoAwareFormatter(LOG_FORMAT, LOG_DATE_FORMAT))
    root_logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            mode="a",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(VideoAwareFormatter(LOG_FORMAT, LOG_DATE_FORMAT))
        root_logger.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("onnxruntime").setLevel(logging.ERROR)
    logging.getLogger("diffusers").setLevel(logging.WARNING)
