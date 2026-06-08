from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class PersonaEvolutionPhase(PipelinePhase):
    name = "persona_evolution"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
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

            return PhaseResult(success=True)
        except Exception:
            return PhaseResult(success=True)
