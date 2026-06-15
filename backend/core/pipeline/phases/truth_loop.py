import logging

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult

logger = logging.getLogger("padplus.pipeline.truth_loop")


class TruthLoopPhase(PipelinePhase):
    name = "truth_loop"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            from core.truth_loop import get_truth_loop
            truth = get_truth_loop()

            response = ctx.context.get("response", "")
            sources = ctx.context.get("sources", {})

            if not response:
                return PhaseResult(success=True, data={"truth_confidence": 0.5, "claims_verified": 0, "sources_info": []})

            claims = truth.extractor.extract_claims(response)

            truth_confidence = 0.5
            claims_verified = 0
            sources_info = []

            if claims:
                verified = truth.verify_claims(claims)
                truth_confidence = verified.get("overall_confidence", 0.5)
                claims_verified = len(verified.get("verified_claims", []))

                rag_s = sources.get("rag", {})
                if rag_s.get("count", 0) > 0:
                    sources_info.append(f"📚 RAG: {rag_s['count']} источников (уверенность: {rag_s.get('confidence', 0):.0%})")
                facts_s = sources.get("facts", {})
                if facts_s.get("count", 0) > 0:
                    sources_info.append(f"📝 Факты: {facts_s['count']} найдено")
                ep_s = sources.get("episodic", {})
                if ep_s.get("count", 0) > 0:
                    sources_info.append(f"📜 Эпизоды: {ep_s['count']} найдено")
                llm_s = sources.get("llm", {})
                if llm_s.get("model"):
                    sources_info.append(f"🤖 LLM: {llm_s.get('provider', '')} ({llm_s.get('model', '')})")

            return PhaseResult(
                success=True,
                data={
                    "truth_confidence": truth_confidence,
                    "claims_verified": claims_verified,
                    "sources_info": sources_info,
                    "add_disclaimer": truth_confidence < 0.5,
                },
            )
        except Exception as e:
            logger.warning("Ошибка в TruthLoopPhase: %s", e, exc_info=True)
            return PhaseResult(
                success=True,
                data={"truth_confidence": 0.5, "claims_verified": 0, "sources_info": [], "add_disclaimer": False},
            )
