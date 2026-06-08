"""
DEPRECATED — используйте core.pipeline напрямую.

Переадресация импортов из старого модуля в новый пакет.
"""

from core.pipeline import PipelineState, DegradationInfo, PipelineResult, PipelineExecutor, get_pipeline

__all__ = [
    "PipelineState",
    "DegradationInfo",
    "PipelineResult",
    "PipelineExecutor",
    "get_pipeline",
]
