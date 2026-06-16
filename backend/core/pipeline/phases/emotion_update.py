import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.emotion_update")


class EmotionUpdatePhase(PipelinePhase):
    name = "emotion_update"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            response = ctx.context.get("response", "")
            from emotion.pad_model import get_pad_model
            pad = get_pad_model()
            if "ошибка" in response.lower() or "проблема" in response.lower():
                pad.apply_event("fallback", 0.2)
            else:
                pad.apply_event("new_knowledge", 0.2)
            return PhaseResult(success=True)
        except Exception as e:
            logger.warning("Ошибка в EmotionUpdatePhase: %s", e, exc_info=True)
            return PhaseResult(success=True)
