"""
Monitoring utilities for the auto-video pipeline.

This module provides monitoring and logging capabilities
for tracking performance and metrics.
"""

import logging
import time
from contextlib import contextmanager
from typing import Generator, Optional


class PipelineMonitor:
    """
    Monitor for the video generation pipeline.

    Tracks execution time, resource usage, and performance metrics.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the monitor.

        Args:
            logger: Optional logger instance (creates default if None)
        """
        self.logger = logger or logging.getLogger("auto_video.pipeline")
        self.metrics: dict = {}

    @contextmanager
    def measure(self, operation: str) -> Generator[None, None, None]:
        """
        Measure the time of an operation.

        Args:
            operation: Name of the operation to measure

        Example:
            >>> with monitor.measure("script_generation"):
            ...     generate_script()
        """
        start = time.time()
        self.logger.info(f"Starting: {operation}")
        try:
            yield
        finally:
            duration = time.time() - start
            self.metrics[operation] = duration
            self.logger.info(f"Completed: {operation} ({duration:.2f}s)")

    def get_metrics(self) -> dict:
        """
        Get all collected metrics.

        Returns:
            Dictionary of operation names to durations
        """
        return self.metrics.copy()

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics = {}

    def log_agent_decision(
        self,
        agent: str,
        decision: str,
        reasoning: str = ""
    ) -> None:
        """
        Log an agent's decision.

        Args:
            agent: Name of the agent
            decision: The decision made
            reasoning: Optional reasoning for the decision
        """
        self.logger.info(f"[{agent}] Decision: {decision}")
        if reasoning:
            self.logger.debug(f"[{agent}] Reasoning: {reasoning}")

    def log_metric(self, name: str, value: float, unit: str = "") -> None:
        """
        Log a custom metric.

        Args:
            name: Metric name
            value: Metric value
            unit: Optional unit (e.g., "MB", "fps")
        """
        self.metrics[name] = value
        unit_str = f" {unit}" if unit else ""
        self.logger.info(f"Metric: {name} = {value}{unit_str}")

    def log_stage_start(self, stage: str, details: str = "") -> None:
        """Log the start of a pipeline stage."""
        msg = f"Stage: {stage}"
        if details:
            msg += f" - {details}"
        self.logger.info(f"[START] {msg}")

    def log_stage_complete(self, stage: str, details: str = "") -> None:
        """Log the completion of a pipeline stage."""
        msg = f"Stage: {stage}"
        if details:
            msg += f" - {details}"
        self.logger.info(f"[COMPLETE] {msg}")

    def log_stage_error(self, stage: str, error: str) -> None:
        """Log an error in a pipeline stage."""
        self.logger.error(f"[ERROR] Stage: {stage} - {error}")

    def get_summary(self) -> str:
        """
        Get a summary of all metrics.

        Returns:
            Formatted summary string
        """
        if not self.metrics:
            return "No metrics collected"

        lines = ["=== Pipeline Metrics ==="]
        for operation, duration in self.metrics.items():
            lines.append(f"  {operation}: {duration:.2f}s")

        total = sum(self.metrics.values())
        lines.append(f"  Total: {total:.2f}s")

        return "\n".join(lines)


# Global monitor instance
_global_monitor: Optional[PipelineMonitor] = None


def get_monitor() -> PipelineMonitor:
    """Get the global monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PipelineMonitor()
    return _global_monitor
