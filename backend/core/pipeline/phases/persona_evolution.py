import logging
import os

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.persona_evolution")

REFLECTION_INTERVAL = int(os.getenv("REFLECTION_INTERVAL", "10"))
_reflection_counter = 0


def _reset_reflection_counter():
    global _reflection_counter
    _reflection_counter = 0


class PersonaEvolutionPhase(PipelinePhase):
    name = "persona_evolution"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        global _reflection_counter
        try:
            user_id = ctx.context.get("user_id")
            response = ctx.context.get("response", "")
            user_message = ctx.user_message

            if user_id:
                from memory.user_persona import get_user_persona_manager
                persona_manager = get_user_persona_manager()
                user_persona = persona_manager.get_persona(user_id)
                msg_lower = user_message.lower()

                if any(w in msg_lower for w in ["правда", "факт", "точно", "верно"]):
                    user_persona.adjust_style("technical_level", 0.01, "фактологический вопрос")
                if any(w in msg_lower for w in ["почему", "смысл", "суть", "думаю"]):
                    user_persona.adjust_style("formality", -0.01, "философский вопрос")
                if any(w in msg_lower for w in ["спасибо", "благодар", "помог", "отлично"]):
                    user_persona.adjust_style("verbosity", 0.01, "положительная обратная связь")

                persona_manager.save_persona(user_persona)
            else:
                from memory.persona import get_persona
                persona = get_persona()
                evolution = persona.evolve_from_dialog(
                    user_message=user_message,
                    ai_response=response,
                )

                _reflection_counter += 1
                if _reflection_counter >= REFLECTION_INTERVAL:
                    _reflection_counter = 0
                    await self._run_reflection_cycle(persona)

            return PhaseResult(success=True)
        except Exception as e:
            logger.warning("Ошибка в PersonaEvolutionPhase: %s", e, exc_info=True)
            return PhaseResult(success=True)

    async def _run_reflection_cycle(self, persona) -> None:
        try:
            from core.evolution import Constitution, MetaLearner, ReflectionEngine
            from core.experience import get_store

            store = get_store()
            experiences = store.load_all()

            engine = ReflectionEngine()
            insights = engine.reflect(experiences)

            if not insights:
                return

            learner = MetaLearner()
            decisions = learner.decide(insights)

            if not decisions:
                return

            constitution = Constitution()
            applied = constitution.execute(decisions, persona)

            if applied:
                persona.add_reflection(
                    insight=f"Эволюция: применено {len(applied)} изменений",
                    action="evolution_cycle",
                    confidence=0.6,
                )
                logger.info("Эволюция: применено %d изменений личности", len(applied))
        except Exception as e:
            logger.warning("Ошибка в цикле эволюции: %s", e, exc_info=True)
