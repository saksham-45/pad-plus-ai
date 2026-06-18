import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.save_episode")


class SaveEpisodePhase(PipelinePhase):
    name = "save_episode"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from memory import get_episodic_memory
            episodic = get_episodic_memory()

            response = ctx.context.get("response", "")
            intent = ctx.context.get("intent", "unknown")
            rag_used = ctx.context.get("rag_used", False)
            procedure_used = ctx.context.get("procedure_used")
            truth_confidence = ctx.context.get("truth_confidence", 0.5)
            emotion_state = ctx.context.get("emotion_state", {})
            user_id = ctx.context.get("user_id")

            significance = 0.5
            if rag_used:
                significance += 0.1
            if procedure_used:
                significance += 0.15
            if truth_confidence > 0.7:
                significance += 0.1

            emotion_before = {
                "уверенность": float(emotion_state.get("уверенность", 0.5)),
                "удовольствие": float(emotion_state.get("удовольствие", 0.0)),
                "возбуждение": float(emotion_state.get("возбуждение", 0.0)),
            }

            episode = episodic.add_episode(
                user_message=str(ctx.user_message) if ctx.user_message else "",
                ai_response=str(response) if response else "",
                topic=intent,
                intent=intent,
                significance=min(significance, 1.0),
                emotion_before=emotion_before,
                emotion_after={},
                concepts=[intent],
                user_id=user_id,
            )

            return PhaseResult(
                success=True,
                data={"episode_id": episode.id},
            )
        except Exception as e:
            logger.warning("Ошибка в SaveEpisodePhase: %s", e, exc_info=True)
            return PhaseResult(
                success=True,
                data={"episode_id": None},
            )
