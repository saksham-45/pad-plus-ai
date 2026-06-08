"""
Pipeline — оркестратор обработки запросов PAD+ AI.

Состоит из последовательных фаз:
Safety → Intent → Retrieve → Generate → Verify → Remember → Emit
"""

from .models import PipelineState, DegradationInfo, PhaseResult, PipelineResult
from .context import PipelineContext
from .base import PipelinePhase
from typing import Optional
from .executor import PipelineExecutor

_pipeline: Optional[PipelineExecutor] = None


def get_pipeline() -> PipelineExecutor:
    global _pipeline
    if _pipeline is None:
        _pipeline = PipelineExecutor()
    return _pipeline


__all__ = [
    "PipelineState",
    "DegradationInfo",
    "PhaseResult",
    "PipelineResult",
    "PipelineContext",
    "PipelinePhase",
    "PipelineExecutor",
    "get_pipeline",
]
