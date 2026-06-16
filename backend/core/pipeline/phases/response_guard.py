import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.response_guard")


class ResponseGuardPhase(PipelinePhase):
    name = "response_guard"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            response = ctx.context.get("response", "")
            call_count = ctx.context.get("call_count", 0)
            confidence = ctx.context.get("confidence", 0.5)

            from core.guard.response_guard import get_response_guard
            from core.guard.self_healing import get_self_healing_guard
            from core.guard.tone_engine import get_tone_engine
            from core.guard.cognitive_layer import get_cognitive_layer, build_cognition

            meta = {
                "is_first_message": call_count <= 1,
                "asked_identity": any(w in ctx.user_message.lower() for w in ["кто ты", "что ты", "как тебя зовут", "ты кто"]),
                "confidence": confidence,
            }

            guard = get_response_guard()
            response = guard.process(response, meta)

            self_healing = get_self_healing_guard()
            self_healing.process_and_learn(response, meta)

            tone_engine = get_tone_engine()
            emotion = tone_engine.get_emotion_from_context(ctx.user_message, response)
            response = tone_engine.apply(response, emotion, meta)

            cognitive_layer = get_cognitive_layer()
            cognition = {}
            if cognitive_layer.enabled:
                from ..models import PipelineResult
                dummy = PipelineResult(success=True, response=response)
                cognition = build_cognition(dummy.to_dict(explain=False))

            return PhaseResult(
                success=True,
                data={
                    "response": response,
                    "cognition": cognition,
                },
            )
        except Exception as e:
            logger.warning("Ошибка в ResponseGuardPhase: %s", e, exc_info=True)
            return PhaseResult(success=True, data={"response": ctx.context.get("response", "")})
