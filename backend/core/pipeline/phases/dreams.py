import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.dreams")


class DreamsPhase(PipelinePhase):
    name = "dreams"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from core.dreams import get_dream_system
            dreams = get_dream_system()
            dreams.record_activity()
            return PhaseResult(success=True)
        except Exception as e:
            logger.warning("Ошибка в DreamsPhase: %s", e, exc_info=True)
            return PhaseResult(success=True, error=str(e))
