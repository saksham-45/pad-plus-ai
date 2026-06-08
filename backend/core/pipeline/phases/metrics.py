from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class MetricsPhase(PipelinePhase):
    name = "metrics"

    def __init__(self, executor):
        self._executor = executor

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            start_time = ctx.context.get("start_time", 0)
            result = ctx.context.get("pipeline_result")
            if result is not None:
                self._executor._record_metrics(start_time, result)
            return PhaseResult(success=True)
        except Exception:
            return PhaseResult(success=True)
