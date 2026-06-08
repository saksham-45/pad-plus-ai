from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class DreamsPhase(PipelinePhase):
    name = "dreams"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from core.dreams import get_dream_system
            dreams = get_dream_system()
            dreams.record_activity()
            return PhaseResult(success=True)
        except Exception:
            return PhaseResult(success=True)
