import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.roots")


class RootsPhase(PipelinePhase):
    name = "roots"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from memory.roots import get_roots_memory
            roots = get_roots_memory()
            context = roots.export_for_context(max_items=10)
            return PhaseResult(success=True, data={"roots_context": context})
        except Exception as e:
            logger.warning("Ошибка в RootsPhase: %s", e, exc_info=True)
            return PhaseResult(success=True, data={"roots_context": ""})
