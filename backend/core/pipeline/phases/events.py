import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.events")


class EventsBroadcastPhase(PipelinePhase):
    name = "events_broadcast"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from core.event_bus import get_event_bus, EventType
            bus = get_event_bus()

            confidence = ctx.context.get("confidence", 0.0)
            rag_used = ctx.context.get("rag_used", False)
            intent = ctx.context.get("intent", "chat_general")

            bus.emit(
                EventType.DIALOGUE_FINISHED,
                data={
                    "intent": intent,
                    "confidence": confidence,
                    "rag_used": rag_used,
                },
                source="pipeline",
            )
            bus.emit(
                EventType.MIND_STATE_UPDATE,
                data={"trigger": "dialogue_finished"},
                source="pipeline",
            )

            return PhaseResult(success=True)
        except Exception as e:
            logger.warning("Ошибка в EventsBroadcastPhase: %s", e, exc_info=True)
            return PhaseResult(success=True)
