"""Core package exports.

Avoid importing pipeline eagerly here to keep module initialization acyclic.
"""

__all__ = [
    "VideoPipeline",
    "PipelineStep",
    "PipelineResult",
    "PipelineProgress",
    "PipelineState",
]


def __getattr__(name: str):
    if name in __all__:
        from auto_video.core.pipeline import (
            PipelineProgress,
            PipelineResult,
            PipelineState,
            PipelineStep,
            VideoPipeline,
        )

        namespace = {
            "VideoPipeline": VideoPipeline,
            "PipelineStep": PipelineStep,
            "PipelineResult": PipelineResult,
            "PipelineProgress": PipelineProgress,
            "PipelineState": PipelineState,
        }
        return namespace[name]
    raise AttributeError(name)
