"""
Модели данных для Pipeline PAD+ AI.

- PipelineState — состояния пайплайна
- DegradationInfo — информация о деградации компонента
- PhaseResult — результат выполнения одной фазы
- PipelineResult — полный результат выполнения пайплайна
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger("padplus.pipeline.models")


class PipelineState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class DegradationInfo:
    component: str
    error: str
    fallback_applied: bool = False
    severity: str = "medium"

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "error": self.error,
            "fallback_applied": self.fallback_applied,
            "severity": self.severity,
        }


@dataclass
class PhaseResult:
    success: bool
    data: Any = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    degradation: Optional[DegradationInfo] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata,
            "degradation": self.degradation.to_dict() if self.degradation else None,
        }


@dataclass
class PipelineResult:
    success: bool
    response: str = ""
    intent: str = ""
    confidence: float = 0.0
    provider: str = ""
    safety_passed: bool = True
    safety_warning: Optional[str] = None
    truth_confidence: float = 0.5
    claims_verified: int = 0
    emotion_style: Dict = field(default_factory=dict)
    rag_used: bool = False
    facts_used: int = 0
    execution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    strategy: str = "simple"
    cognitive_load: float = 0.0
    health_score: float = 0.0
    episode_id: Optional[str] = None
    procedure_used: Optional[str] = None
    consolidation_triggered: bool = False
    raw_llm_response: Optional[Dict] = None
    llm_metadata: Optional[Dict] = None
    sources: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, explain: bool = False) -> dict:
        result = {
            "answer": self.response,
            "success": self.success,
            "cognitive": {
                "strategy": self.strategy,
                "confidence": round(self.confidence, 3),
                "health_score": round(self.health_score, 3),
                "execution_time_ms": round(self.execution_time_ms, 2),
                "cognitive_load": round(self.cognitive_load, 3),
            },
            "memory": {
                "rag_used": self.rag_used,
                "facts_used": self.facts_used,
                "episode_id": self.episode_id,
                "procedure_used": self.procedure_used,
                "sources": self.sources,
            },
            "emotion": {
                "style": self.emotion_style,
                "truth_confidence": round(self.truth_confidence, 3),
            },
            "meta": {
                "intent": self.intent,
                "provider": self.provider,
                "errors": self.errors,
                "metadata": self.metadata,
            },
            "safety": {
                "passed": self.safety_passed,
                "warning": self.safety_warning,
            },
        }

        result["truth"] = {
            "confidence": round(self.truth_confidence, 3),
            "claims_verified": self.claims_verified,
            "status": self._get_truth_status(),
            "sources_count": self._get_sources_count(),
        }

        if explain:
            result["xray"] = self._generate_xray_insights()

        return result

    def _get_truth_status(self) -> str:
        if self.truth_confidence >= 0.8:
            return "verified"
        elif self.truth_confidence >= 0.5:
            return "partial"
        return "unverified"

    def _get_sources_count(self) -> int:
        count = 0
        if self.sources:
            count += self.sources.get("rag", {}).get("count", 0)
            count += self.sources.get("facts", {}).get("count", 0)
            count += self.sources.get("episodic", {}).get("count", 0)
        return count

    def _generate_xray_insights(self) -> dict:
        strategy_descriptions = {
            "simple": "Прямая генерация ответа",
            "retrieval": "Поиск и синтез информации",
            "reasoning": "Логический анализ",
            "creative": "Творческая генерация",
            "analytical": "Аналитическая обработка",
        }

        pipeline_stages = ["safety", "intent"]
        if self.rag_used:
            pipeline_stages.append("retrieval")
        if self.facts_used > 0:
            pipeline_stages.append("facts")
        if self.episode_id:
            pipeline_stages.append("episodic")
        pipeline_stages.extend(["generate", "verify", "remember"])

        return {
            "strategy": self.strategy,
            "strategy_description": strategy_descriptions.get(
                self.strategy, "Обработка запроса"
            ),
            "pipeline_stages": pipeline_stages,
            "memory_usage": {
                "rag": self.rag_used,
                "facts": self.facts_used > 0,
                "episodic": self.episode_id is not None,
                "procedure": self.procedure_used is not None,
            },
            "verification": {
                "status": self._get_truth_status(),
                "confidence": round(self.truth_confidence, 3),
                "claims_verified": self.claims_verified,
            },
            "performance": {
                "execution_time_ms": round(self.execution_time_ms, 2),
                "health_score": round(self.health_score, 3),
                "cognitive_load": round(self.cognitive_load, 3),
            },
        }
