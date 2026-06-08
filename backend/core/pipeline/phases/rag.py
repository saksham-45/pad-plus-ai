from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class RagPhase(PipelinePhase):
    name = "rag"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from memory.rag import get_rag
            rag = get_rag()
            user_id = ctx.context.get("user_id") if ctx.context else None
            context_data = rag.get_context(ctx.user_message, user_id=user_id)

            sources = {"count": 1 if context_data else 0, "confidence": 0.8 if context_data else 0.0}

            return PhaseResult(
                success=True,
                data={
                    "context": context_data or "",
                    "rag_used": bool(context_data),
                    "sources": sources,
                },
            )
        except Exception:
            return PhaseResult(
                success=True,
                data={"context": "", "rag_used": False, "sources": {"count": 0, "confidence": 0.0}},
            )
