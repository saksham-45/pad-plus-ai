from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class ReflectionPhase(PipelinePhase):
    name = "reflection"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from core.xray.reflection import get_reflection_loop
            from core.xray.system_state import get_system_state_manager

            reflection = get_reflection_loop()
            state_manager = get_system_state_manager()
            state_manager.update(ctx.context.get("result_dict", {}))
        except Exception:
            pass

        try:
            from core.meta_controller import get_meta_controller, CognitiveState
            meta = get_meta_controller()
            meta.adapt({
                "success": ctx.context.get("pipeline_success", False),
                "strategy": ctx.context.get("strategy", "simple"),
                "response_time": ctx.context.get("execution_time_ms", 0) / 1000,
            })
            meta.set_state(CognitiveState.IDLE)
        except Exception:
            pass

        return PhaseResult(success=True)
