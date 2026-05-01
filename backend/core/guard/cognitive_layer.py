"""
🧠 Cognitive Layer — Объяснение процесса мышления

Генерирует мета-данные о процессе принятия решений:
- Стратегия обработки
- Уровень уверенности
- Использованные источники
- Память и её влияние

Режимы:
- basic: только ответ
- debug: ответ + cognition данные
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("padplus.guard.cognitive_layer")


# ============================================================================
# ТИПЫ СТРАТЕГИЙ
# ============================================================================

class StrategyType(str, Enum):
    """Типы стратегий обработки"""
    SIMPLE = "simple"              # Прямая генерация
    RETRIEVAL = "retrieval"        # Поиск и синтез
    REASONING = "reasoning"        # Логический анализ
    CREATIVE = "creative"          # Творческая генерация
    ANALYTICAL = "analytical"      # Аналитическая обработка


# Описания стратегий
STRATEGY_DESCRIPTIONS: Dict[str, str] = {
    StrategyType.SIMPLE.value: "Прямая генерация ответа на основе общих знаний",
    StrategyType.RETRIEVAL.value: "Поиск и синтез информации из источников",
    StrategyType.REASONING.value: "Логический анализ и построение выводов",
    StrategyType.CREATIVE.value: "Творческая генерация с элементами импровизации",
    StrategyType.ANALYTICAL.value: "Аналитическая обработка с разбором компонентов",
}


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

@dataclass
class SourceInfo:
    """Информация об источнике"""
    name: str                      # RAG, facts, episodic, llm
    count: int = 0                 # Количество использований
    confidence: float = 0.0        # Уверенность источника
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "count": self.count,
            "confidence": round(self.confidence, 3),
            "details": self.details
        }


@dataclass
class CognitionData:
    """Данные о процессе мышления"""
    strategy: str = "simple"
    strategy_description: str = ""
    confidence: float = 0.0
    health_score: float = 0.0
    execution_time_ms: float = 0.0
    cognitive_load: float = 0.0
    
    # Использованные источники
    sources: List[SourceInfo] = field(default_factory=list)
    
    # Память
    memory_usage: Dict[str, bool] = field(default_factory=dict)
    
    # Верификация
    verification: Dict[str, Any] = field(default_factory=dict)
    
    # Ошибки и предупреждения
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Преобразует в словарь для API ответа"""
        return {
            "strategy": self.strategy,
            "strategy_description": self.strategy_description or STRATEGY_DESCRIPTIONS.get(self.strategy, "Обработка запроса"),
            "confidence": round(self.confidence, 3),
            "health_score": round(self.health_score, 3),
            "execution_time_ms": round(self.execution_time_ms, 2),
            "cognitive_load": round(self.cognitive_load, 3),
            "sources": [s.to_dict() for s in self.sources],
            "memory_usage": self.memory_usage,
            "verification": self.verification,
            "errors": self.errors,
            "warnings": self.warnings
        }


# ============================================================================
# COGNITIVE LAYER
# ============================================================================

class CognitiveLayer:
    """
    🧠 Cognitive Layer — генерация мета-данных о мышлении
    
    Анализирует процесс обработки запроса и генерирует
    объяснимые мета-данные.
    """
    
    def __init__(self):
        """Инициализация CognitiveLayer"""
        self.enabled = True
        self.default_mode = "basic"  # basic или debug
        
        logger.info("🧠 CognitiveLayer инициализирован")
    
    def build_cognition(self, meta: Dict[str, Any]) -> CognitionData:
        """
        Строит CognitionData из мета-данных pipeline
        
        Args:
            meta: Мета-данные от pipeline
        
        Returns:
            CognitionData с информацией о процессе мышления
        """
        cognition = CognitionData()
        
        # Стратегия
        strategy = meta.get("strategy", "simple")
        cognition.strategy = strategy
        cognition.strategy_description = STRATEGY_DESCRIPTIONS.get(str(strategy), "Обработка запроса")
        
        # Уверенность
        cognition.confidence = meta.get("confidence", 0.0)
        
        # Здоровье системы
        cognition.health_score = meta.get("health_score", 0.0)
        
        # Время выполнения
        cognition.execution_time_ms = meta.get("execution_time_ms", 0.0)
        
        # Когнитивная нагрузка
        cognition.cognitive_load = meta.get("cognitive_load", 0.0)
        
        # Источники
        sources = meta.get("sources", {})
        cognition.sources = self._parse_sources(sources)
        
        # Память
        memory = meta.get("memory", {})
        cognition.memory_usage = {
            "rag": memory.get("rag_used", False),
            "facts": memory.get("facts_used", 0) > 0,
            "episodic": memory.get("episode_id") is not None,
            "procedure": memory.get("procedure_used") is not None,
        }
        
        # Верификация
        truth = meta.get("truth", {})
        cognition.verification = {
            "status": truth.get("status", "unverified"),
            "confidence": truth.get("confidence", 0.0),
            "claims_verified": truth.get("claims_verified", 0),
        }
        
        # Ошибки
        errors = meta.get("errors", [])
        cognition.errors = errors if isinstance(errors, list) else []
        
        return cognition
    
    def _parse_sources(self, sources: Dict[str, Any]) -> List[SourceInfo]:
        """Парсит информацию об источниках"""
        source_list = []
        
        if not sources:
            return source_list
        
        # RAG
        if "rag" in sources:
            rag = sources["rag"]
            source_list.append(SourceInfo(
                name="RAG",
                count=rag.get("count", 0),
                confidence=rag.get("confidence", 0.0),
                details={"type": "retrieval"}
            ))
        
        # Facts
        if "facts" in sources:
            facts = sources["facts"]
            source_list.append(SourceInfo(
                name="FactMemory",
                count=facts.get("count", 0),
                confidence=0.7,  # Default для фактов
                details={"type": "factual"}
            ))
        
        # Episodic
        if "episodic" in sources:
            episodic = sources["episodic"]
            source_list.append(SourceInfo(
                name="EpisodicMemory",
                count=episodic.get("count", 0),
                confidence=0.6,  # Default для эпизодов
                details={"type": "experiential"}
            ))
        
        # LLM
        if "llm" in sources:
            llm = sources["llm"]
            source_list.append(SourceInfo(
                name="LLM",
                count=1,
                confidence=0.8,  # Default для LLM
                details={
                    "model": llm.get("model", "unknown"),
                    "provider": llm.get("provider", "unknown"),
                    "type": "generative"
                }
            ))
        
        # Graph
        if "graph" in sources:
            graph = sources["graph"]
            source_list.append(SourceInfo(
                name="KnowledgeGraph",
                count=len(graph.get("concepts", [])),
                confidence=graph.get("confidence", 0.0),
                details={
                    "concepts": graph.get("concepts", []),
                    "type": "semantic"
                }
            ))
        
        return source_list
    
    def format_for_response(self, answer: str, cognition: CognitionData,
                           mode: str = "basic") -> Dict[str, Any]:
        """
        Форматирует ответ для API
        
        Args:
            answer: Основной ответ
            cognition: Данные о мышлении
            mode: Режим (basic или debug)
        
        Returns:
            Словарь для API ответа
        """
        if mode == "basic":
            return {
                "answer": answer,
                "success": True
            }
        
        elif mode == "debug":
            return {
                "answer": answer,
                "success": True,
                "cognition": cognition.to_dict(),
                "explanation": self._generate_explanation(cognition)
            }
        
        else:
            # По умолчанию - basic
            return {
                "answer": answer,
                "success": True
            }
    
    def _generate_explanation(self, cognition: CognitionData) -> str:
        """
        Генерирует текстовое объяснение процесса мышления
        
        Args:
            cognition: Данные о мышлении
        
        Returns:
            Текстовое объяснение
        """
        parts = []
        
        # Стратегия
        parts.append(f"🧠 **Стратегия:** {cognition.strategy_description}")
        
        # Источники
        if cognition.sources:
            source_names = [s.name for s in cognition.sources if s.count > 0]
            if source_names:
                parts.append(f"📚 **Источники:** {', '.join(source_names)}")
        
        # Память
        memory_parts = []
        if cognition.memory_usage.get("rag"):
            memory_parts.append("RAG")
        if cognition.memory_usage.get("facts"):
            memory_parts.append("факты")
        if cognition.memory_usage.get("episodic"):
            memory_parts.append("эпизоды")
        if cognition.memory_usage.get("procedure"):
            memory_parts.append("процедуры")
        
        if memory_parts:
            parts.append(f"💾 **Память:** {', '.join(memory_parts)}")
        
        # Уверенность
        confidence_text = self._confidence_to_text(cognition.confidence)
        parts.append(f"📊 **Уверенность:** {confidence_text}")
        
        # Верификация
        if cognition.verification.get("status") == "verified":
            parts.append("✅ **Верификация:** подтверждено")
        elif cognition.verification.get("status") == "partial":
            parts.append("⚠️ **Верификация:** частично подтверждено")
        
        return "\n".join(parts)
    
    def _confidence_to_text(self, confidence: float) -> str:
        """Преобразует числовую уверенность в текст"""
        if confidence >= 0.9:
            return "очень высокая"
        elif confidence >= 0.7:
            return "высокая"
        elif confidence >= 0.5:
            return "средняя"
        elif confidence >= 0.3:
            return "низкая"
        else:
            return "очень низкая"
    
    def configure(self, enabled: Optional[bool] = None, default_mode: Optional[str] = None):
        """
        Настройка слоя
        
        Args:
            enabled: Включён ли слой
            default_mode: Режим по умолчанию (basic/debug)
        """
        if enabled is not None:
            self.enabled = enabled
        if default_mode is not None:
            self.default_mode = default_mode
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        return {
            "enabled": self.enabled,
            "default_mode": self.default_mode,
            "version": "1.0"
        }


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def build_cognition(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Быстрое построение cognition данных
    
    Args:
        meta: Мета-данные от pipeline
    
    Returns:
        Словарь с cognition данными
    """
    layer = CognitiveLayer()
    cognition = layer.build_cognition(meta)
    return cognition.to_dict()


def explain_thinking(answer: str, meta: Dict[str, Any], 
                     mode: str = "debug") -> Dict[str, Any]:
    """
    Генерирует ответ с объяснением мышления
    
    Args:
        answer: Основной ответ
        meta: Мета-данные от pipeline
        mode: Режим (basic/debug)
    
    Returns:
        Словарь для API ответа
    """
    layer = CognitiveLayer()
    cognition = layer.build_cognition(meta)
    return layer.format_for_response(answer, cognition, mode)


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_cognitive_layer: Optional[CognitiveLayer] = None


def get_cognitive_layer() -> CognitiveLayer:
    """Возвращает глобальный CognitiveLayer"""
    global _cognitive_layer
    if _cognitive_layer is None:
        _cognitive_layer = CognitiveLayer()
    return _cognitive_layer


def reset_cognitive_layer():
    """Сбрасывает глобальный CognitiveLayer (для тестов)"""
    global _cognitive_layer
    _cognitive_layer = None