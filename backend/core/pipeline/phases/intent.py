import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.intent")


class IntentPhase(PipelinePhase):
    name = "intent"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from core.intent_router import get_router
            router = get_router()
            routing = router.route(ctx.user_message)
            intent = routing.intent.value
            pipeline_meta = [s.name for s in routing.pipeline[:3]]

            return PhaseResult(
                success=True,
                data={"intent": intent, "pipeline_meta": pipeline_meta},
            )
        except Exception as e:
            logger.warning("Ошибка в IntentPhase: %s", e, exc_info=True)
            return PhaseResult(
                success=True,
                data={"intent": "chat_general", "pipeline_meta": []},
            )
