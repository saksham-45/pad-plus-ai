from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class AntiLoopPhase(PipelinePhase):
    name = "anti_loop"

    def __init__(self, executor):
        self._executor = executor

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        loop_warning = self._executor._check_anti_loop(ctx.user_message)
        if loop_warning:
            return PhaseResult(
                success=True,
                data={"blocked": True, "warning": loop_warning},
                metadata={"anti_loop_warning": loop_warning},
            )
        return PhaseResult(success=True, data={"blocked": False})
