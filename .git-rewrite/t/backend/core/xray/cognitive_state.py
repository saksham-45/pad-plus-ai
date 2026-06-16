"""
🧠 Cognitive State — Состояние когнитивной системы

Отслеживает внутреннюю динамику системы:
- uncertainty: неопределённость
- cognitive_load: когнитивная нагрузка
- decision_path: путь принятия решений
- strategy: текущая стратегия
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import logging

logger = logging.getLogger("padplus.xray")


@dataclass
class CognitiveMetrics:
    """Метрики когнитивного состояния"""
    uncertainty: float = 0.0        # 0.0 - 1.0 (1.0 = максимальная неопределённость)
    cognitive_load: float = 0.0     # 0.0 - 1.0 (1.0 = максимальная нагрузка)
    confidence: float = 1.0         # 0.0 - 1.0 (1.0 = максимальная уверенность)
    complexity: float = 0.0         # 0.0 - 1.0 (сложность запроса)
    verification_needed: bool = False
    fallback_triggered: bool = False
    
    def to_dict(self) -> dict:
        return {
            "uncertainty": round(self.uncertainty, 3),
            "cognitive_load": round(self.cognitive_load, 3),
            "confidence": round(self.confidence, 3),
            "complexity": round(self.complexity, 3),
            "verification_needed": self.verification_needed,
            "fallback_triggered": self.fallback_triggered
        }


@dataclass
class DecisionNode:
    """Узел в дереве решений"""
    name: str
    decision_type: str  # "strategy", "model", "memory", "verification"
    options: List[str]
    selected: str
    confidence: float
    reasoning: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "decision_type": self.decision_type,
            "options": self.options,
            "selected": self.selected,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class SourceWeight:
    """Вес источника информации"""
    source: str  # "rag", "facts", "memory", "llm"
    weight: float  # 0.0 - 1.0
    confidence: float  # уверенность в источнике
    contribution: float  # фактический вклад в ответ
    
    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "weight": round(self.weight, 3),
            "confidence": round(self.confidence, 3),
            "contribution": round(self.contribution, 3)
        }


class CognitiveState:
    """
    🧠 Когнитивное состояние системы
    
    Отслеживает внутреннюю динамику во время обработки запроса
    """
    
    def __init__(self):
        self.trace_id: Optional[str] = None
        self.user_message: str = ""
        self.start_time: float = time.time()
        
        # Метрики
        self.metrics = CognitiveMetrics()
        
        # Дерево решений
        self.decision_path: List[DecisionNode] = []
        
        # Источники информации
        self.source_weights: Dict[str, SourceWeight] = {}
        
        # Стратегия
        self.strategy: str = "simple"
        self.strategy_reason: str = ""
        
        # Состояние обработки
        self.current_stage: str = "idle"
        self.stages_completed: List[str] = []
        
        # Метка времени последнего обновления
        self.last_updated: float = time.time()
    
    def record_decision(
        self,
        name: str,
        decision_type: str,
        options: List[str],
        selected: str,
        confidence: float,
        reasoning: str,
        metadata: Dict = None
    ) -> DecisionNode:
        """Записывает принятое решение"""
        node = DecisionNode(
            name=name,
            decision_type=decision_type,
            options=options,
            selected=selected,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata or {}
        )
        
        self.decision_path.append(node)
        self.last_updated = time.time()
        
        logger.debug(f"🧠 Decision: {name} → {selected}")
        return node
    
    def update_metrics(
        self,
        uncertainty: float = None,
        cognitive_load: float = None,
        confidence: float = None,
        complexity: float = None
    ):
        """Обновляет метрики"""
        if uncertainty is not None:
            self.metrics.uncertainty = max(0.0, min(1.0, uncertainty))
        if cognitive_load is not None:
            self.metrics.cognitive_load = max(0.0, min(1.0, cognitive_load))
        if confidence is not None:
            self.metrics.confidence = max(0.0, min(1.0, confidence))
        if complexity is not None:
            self.metrics.complexity = max(0.0, min(1.0, complexity))
        
        self.last_updated = time.time()
    
    def set_source_weight(
        self,
        source: str,
        weight: float,
        confidence: float,
        contribution: float = None
    ):
        """Устанавливает вес источника"""
        self.source_weights[source] = SourceWeight(
            source=source,
            weight=weight,
            confidence=confidence,
            contribution=contribution if contribution is not None else weight
        )
        self.last_updated = time.time()
    
    def calculate_final_confidence(self) -> float:
        """
        Вычисляет итоговую уверенность на основе всех источников
        
        Формула:
        final = Σ(source_weight × source_confidence × contribution)
        """
        if not self.source_weights:
            return self.metrics.confidence
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for sw in self.source_weights.values():
            weight = sw.weight * sw.contribution
            weighted_sum += weight * sw.confidence
            total_weight += weight
        
        if total_weight == 0:
            return self.metrics.confidence
        
        return weighted_sum / total_weight
    
    def get_cognitive_load_score(self) -> float:
        """
        Вычисляет общий score когнитивной нагрузки
        
        Формула:
        load = complexity × uncertainty × (1 + steps_count × 0.1)
        """
        steps_factor = 1 + len(self.stages_completed) * 0.1
        return min(1.0, 
            self.metrics.complexity * 
            self.metrics.uncertainty * 
            steps_factor
        )
    
    def should_verify(self) -> bool:
        """Определяет, нужна ли верификация"""
        return (
            self.metrics.uncertainty > 0.5 or
            self.metrics.confidence < 0.6 or
            len(self.source_weights) == 0
        )
    
    def should_simplify(self) -> bool:
        """Определяет, нужно ли упростить стратегию"""
        return self.get_cognitive_load_score() > 0.8
    
    def set_strategy(self, strategy: str, reason: str):
        """Устанавливает стратегию обработки"""
        self.strategy = strategy
        self.strategy_reason = reason
        self.last_updated = time.time()
    
    def complete_stage(self, stage: str):
        """Отмечает стадию как завершённую"""
        if stage not in self.stages_completed:
            self.stages_completed.append(stage)
        self.current_stage = stage
        self.last_updated = time.time()
    
    def get_elapsed_time(self) -> float:
        """Время с начала обработки"""
        return time.time() - self.start_time
    
    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "user_message": self.user_message,
            "start_time": self.start_time,
            "elapsed_time": self.get_elapsed_time(),
            "strategy": self.strategy,
            "strategy_reason": self.strategy_reason,
            "current_stage": self.current_stage,
            "stages_completed": self.stages_completed,
            "metrics": self.metrics.to_dict(),
            "decision_path": [d.to_dict() for d in self.decision_path],
            "source_weights": {k: v.to_dict() for k, v in self.source_weights.items()},
            "final_confidence": self.calculate_final_confidence(),
            "cognitive_load_score": self.get_cognitive_load_score(),
            "should_verify": self.should_verify(),
            "should_simplify": self.should_simplify(),
            "last_updated": self.last_updated
        }
    
    def get_summary(self) -> str:
        """Возвращает краткую сводку состояния"""
        parts = [
            f"Strategy: {self.strategy}",
            f"Load: {self.get_cognitive_load_score():.2f}",
            f"Confidence: {self.calculate_final_confidence():.2f}",
            f"Sources: {len(self.source_weights)}",
            f"Decisions: {len(self.decision_path)}"
        ]
        return " | ".join(parts)


class CognitiveStateManager:
    """
    Менеджер когнитивных состояний
    
    Управляет жизненным циклом CognitiveState
    """
    
    def __init__(self):
        self._active_states: Dict[str, CognitiveState] = {}
        self._state_history: List[CognitiveState] = []
        self._max_history = 100
    
    def create_state(
        self, 
        trace_id: str,
        user_message: str
    ) -> CognitiveState:
        """Создаёт новое когнитивное состояние"""
        state = CognitiveState()
        state.trace_id = trace_id
        state.user_message = user_message
        
        self._active_states[trace_id] = state
        
        logger.debug(f"🧠 Cognitive state created: {trace_id}")
        return state
    
    def get_state(self, trace_id: str) -> Optional[CognitiveState]:
        """Получает состояние по trace_id"""
        return self._active_states.get(trace_id)
    
    def complete_state(self, trace_id: str):
        """Завершает состояние и сохраняет в историю"""
        state = self._active_states.pop(trace_id, None)
        if state:
            self._state_history.append(state)
            
            # Очищаем старую историю
            if len(self._state_history) > self._max_history:
                self._state_history = self._state_history[-self._max_history:]
        
        logger.debug(f"🧠 Cognitive state completed: {trace_id}")
    
    def get_active_count(self) -> int:
        """Количество активных состояний"""
        return len(self._active_states)
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика менеджера"""
        if not self._state_history:
            return {
                "active_states": len(self._active_states),
                "total_processed": 0
            }
        
        # Анализируем историю
        avg_confidence = sum(
            s.calculate_final_confidence() 
            for s in self._state_history
        ) / len(self._state_history)
        
        avg_load = sum(
            s.get_cognitive_load_score() 
            for s in self._state_history
        ) / len(self._state_history)
        
        strategy_counts = {}
        for state in self._state_history:
            strategy_counts[state.strategy] = \
                strategy_counts.get(state.strategy, 0) + 1
        
        return {
            "active_states": len(self._active_states),
            "total_processed": len(self._state_history),
            "avg_confidence": round(avg_confidence, 3),
            "avg_cognitive_load": round(avg_load, 3),
            "strategy_distribution": strategy_counts
        }


# Глобальный экземпляр
_cognitive_state_manager: Optional[CognitiveStateManager] = None


def get_cognitive_state_manager() -> CognitiveStateManager:
    """Возвращает глобальный менеджер когнитивных состояний"""
    global _cognitive_state_manager
    if _cognitive_state_manager is None:
        _cognitive_state_manager = CognitiveStateManager()
    return _cognitive_state_manager