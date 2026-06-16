import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.knowledge_graph")


class KnowledgeGraphPhase(PipelinePhase):
    name = "knowledge_graph"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from knowledge.graph import get_knowledge_graph
            graph = get_knowledge_graph()
            concepts = graph.find_concepts(ctx.user_message, limit=5)

            concept_names = [c.name for c in concepts[:5]] if concepts else []

            return PhaseResult(
                success=True,
                data={
                    "concepts": concept_names,
                    "confidence": 0.7 if concept_names else 0.0,
                },
            )
        except Exception as e:
            logger.warning("Ошибка в KnowledgeGraphPhase: %s", e, exc_info=True)
            return PhaseResult(
                success=True,
                data={"concepts": [], "confidence": 0.0},
            )
