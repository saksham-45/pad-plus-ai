import asyncio
import logging
import os

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.dreams")

DREAM_INTERVAL = int(os.getenv("DREAM_INTERVAL", "20"))
_dialogs_since_dream = 0


def _reset_dream_counter():
    global _dialogs_since_dream
    _dialogs_since_dream = 0


class DreamsPhase(PipelinePhase):
    name = "dreams"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        global _dialogs_since_dream
        try:
            from core.dreams import get_dream_system
            dreams = get_dream_system()
            dreams.record_activity()

            _dialogs_since_dream += 1
            if _dialogs_since_dream >= DREAM_INTERVAL:
                _dialogs_since_dream = 0
                asyncio.create_task(dreams.dream())

            return PhaseResult(success=True)
        except Exception as e:
            logger.warning("Ошибка в DreamsPhase: %s", e, exc_info=True)
            return PhaseResult(success=True, errors=[str(e)])
