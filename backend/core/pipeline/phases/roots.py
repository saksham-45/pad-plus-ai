from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class RootsPhase(PipelinePhase):
    name = "roots"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from memory.roots import get_roots_memory
            roots = get_roots_memory()
            context = roots.export_for_context(max_items=10)
            return PhaseResult(success=True, data={"context": context})
        except Exception:
            return PhaseResult(success=True, data={"context": ""})
