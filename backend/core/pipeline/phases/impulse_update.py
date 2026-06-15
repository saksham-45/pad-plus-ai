import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.impulse_update")


# Дельта-изменения весов импульсов (умножаются на significance)
# Скорректированы:
#   - criticism/contradiction сильнее — чтобы improve мог догнать understand (0→0.5)
#   - praise усиливает текущий — чтобы закреплять успешные паттерны
#   - error_recovery защищает — переключение на protect
_IMPULSE_DELTAS = {
    "contradiction": {"current": -0.20, "improve": 0.15},
    "criticism":    {"current": -0.25, "improve": 0.20},
    "praise":       {"current":  0.20},
    "exploration":  {"understand": 0.15},
    "error_recovery": {"protect": 0.20, "improve": 0.10},
    "repetition":   {"current": -0.08},
    "new_knowledge": {},
}


class ImpulseUpdatePhase(PipelinePhase):
    name = "impulse_update"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            interaction_type = ctx.context.get("experience_interaction_type", "")
            significance = ctx.context.get("experience_significance", 0.0)

            if not interaction_type or significance < 0.2:
                return PhaseResult(success=True)

            from scripts.impulse import get_impulse_core
            core = get_impulse_core()
            deltas = _IMPULSE_DELTAS.get(interaction_type, {})
            if not deltas:
                return PhaseResult(success=True)

            current_label = core.get_primary_label()
            dims = {d.label: d for d in core.dimensions}

            for target, base_delta in deltas.items():
                if target == "current":
                    if current_label in dims:
                        dims[current_label].weight = max(0.0, dims[current_label].weight + base_delta * significance)
                elif target in dims:
                    dims[target].weight = max(0.0, min(1.0, dims[target].weight + base_delta * significance))

            from scripts.impulse import get_manager
            get_manager().save(core)

            ctx.context["impulse_updated"] = True
            return PhaseResult(success=True)
        except Exception as e:
            logger.warning("Ошибка в ImpulseUpdatePhase: %s", e, exc_info=True)
            return PhaseResult(success=True)
