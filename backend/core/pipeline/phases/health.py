import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.health")


class HealthMonitorPhase(PipelinePhase):
    name = "health_monitor"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from core.health_monitor import get_health_monitor
            health = get_health_monitor()

            success = ctx.context.get("pipeline_success", False)
            rag_used = ctx.context.get("rag_used", False)

            if success:
                health.record_event("good_dialog", 1.0)
                if rag_used:
                    health.record_event("learned_fact", 0.5)

            assessment = health.assess_health()
            health_score = assessment.get("overall_score", 0.0)

            return PhaseResult(
                success=True,
                data={"health_score": health_score},
            )
        except Exception as e:
            logger.warning("Ошибка в HealthMonitorPhase: %s", e, exc_info=True)
            return PhaseResult(
                success=True,
                data={"health_score": 0.0},
            )
