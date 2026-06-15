import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.persona")


class PersonaPhase(PipelinePhase):
    name = "persona"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            user_id = ctx.context.get("user_id") if ctx.context else None

            if user_id:
                from memory.user_persona import get_user_persona_manager
                persona_manager = get_user_persona_manager()
                user_persona = persona_manager.get_persona(user_id)
                persona_context = user_persona.get_context_for_prompt() or ""
                user_persona.record_interaction(topic=ctx.context.get("intent", "unknown"))
                persona_manager.save_persona(user_persona)
            else:
                from memory.persona import get_persona
                persona = get_persona()
                persona_context = persona.get_persona_context()

            return PhaseResult(
                success=True,
                data={"persona_context": persona_context, "user_id": user_id},
            )
        except Exception as e:
            logger.warning("Ошибка в PersonaPhase: %s", e, exc_info=True)
            return PhaseResult(
                success=True,
                data={"persona_context": "", "user_id": None},
            )
