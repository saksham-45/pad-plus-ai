from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class SafetyPhase(PipelinePhase):
    name = "safety"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        user_message = ctx.user_message
        try:
            from core.safety_layer import get_safety_layer
            safety = get_safety_layer()
            safety_check = safety.check_request(user_message)

            if safety_check.action.value == "block":
                return PhaseResult(
                    success=True,
                    data={
                        "blocked": True,
                        "warning": safety_check.warning_message
                        or "Запрос заблокирован по соображениям безопасности.",
                        "safety_passed": False,
                    },
                )

            sanitized = user_message
            if safety_check.action.value == "sanitize":
                sanitized = safety.sanitize_input(user_message)

            return PhaseResult(
                success=True,
                data={
                    "blocked": False,
                    "sanitized_message": sanitized,
                    "warning": safety_check.warning_message,
                    "safety_passed": True,
                },
                metadata={"safety_action": safety_check.action.value},
            )
        except Exception as e:
            return self._degraded("safety", str(e), severity="high")
