import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.semantic")


class SemanticPhase(PipelinePhase):
    name = "semantic"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from memory import get_semantic_memory
            semantic = get_semantic_memory()
            procedure = semantic.find_applicable_procedure(ctx.user_message)

            procedure_context = ""
            procedure_name = None
            procedure_id = None

            if procedure:
                procedure_name = procedure.name
                procedure_id = procedure.id
                procedure_context = f"\n\n🔧 Процедура '{procedure.name}':\n"
                for i, step in enumerate(procedure.procedure_steps[:3], 1):
                    procedure_context += f"  {i}. {step}\n"

            return PhaseResult(
                success=True,
                data={
                    "procedure_context": procedure_context,
                    "procedure_name": procedure_name,
                    "procedure_id": procedure_id,
                },
            )
        except Exception as e:
            logger.warning("Ошибка в SemanticPhase: %s", e, exc_info=True)
            return PhaseResult(
                success=True,
                data={"procedure_context": "", "procedure_name": None, "procedure_id": None},
            )
