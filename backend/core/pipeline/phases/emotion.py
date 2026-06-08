from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


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
                    "state": state.to_dict(),
                    "style": state.get_style(),
                },
            )
        except Exception:
            return PhaseResult(
                success=True,
                data={"state": {}, "style": {}},
            )
