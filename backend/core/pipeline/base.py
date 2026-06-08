"""
PipelinePhase — абстрактный базовый класс для всех фаз пайплайна.
"""

from abc import ABC, abstractmethod
from typing import Optional

from .models import PhaseResult, DegradationInfo
from .context import PipelineContext


class PipelinePhase(ABC):
    name: str = ""

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        ...

    def _degraded(
        self,
        component: str,
        error: str,
        severity: str = "medium",
        fallback_applied: bool = False,
    ) -> PhaseResult:
        return PhaseResult(
            success=False,
            errors=[error],
            degradation=DegradationInfo(
                component=component,
                error=error,
                severity=severity,
                fallback_applied=fallback_applied,
            ),
        )
