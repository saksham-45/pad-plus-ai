import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.emotion")


class EmotionPhase(PipelinePhase):
    name = "emotion"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from emotion.pad_model import get_pad_model
            pad = get_pad_model()
            state = pad.get_state()
            return PhaseResult(
                success=True,
                data={
                    "emotion_state": state.to_dict(),
                    "emotion_style": state.get_style(),
                },
            )
        except Exception as e:
            logger.warning("Ошибка в EmotionPhase: %s", e, exc_info=True)
            return PhaseResult(
                success=True,
                data={"emotion_state": {}, "emotion_style": {}},
            )
