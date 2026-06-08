from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult


class EpisodicPhase(PipelinePhase):
    name = "episodic"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from memory.episodic import get_episodic_memory
            episodic = get_episodic_memory()
            user_id = ctx.context.get("user_id") if ctx.context else None
            similar = episodic.search_episodes(ctx.user_message, limit=2, user_id=user_id)

            context_text = ""
            if similar:
                context_text = "\n\n📜 Похожие ситуации из прошлого:\n"
                for ep in similar[:2]:
                    context_text += f"- {ep.topic}: {ep.user_message[:50]}... "
                    context_text += f"→ {ep.ai_response[:50]}...\n"

            return PhaseResult(
                success=True,
                data={
                    "context": context_text,
                    "count": len(similar) if similar else 0,
                },
            )
        except Exception:
            return PhaseResult(
                success=True,
                data={"context": "", "count": 0},
            )
