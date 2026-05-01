"""
🧠 ThoughtVisualizer — Визуализация мыслей для X-Ray

Преобразует внутренние процессы AI в понятные "мысли",
которые можно показать пользователю.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger("padplus.xray")


class ThoughtType(Enum):
    """Типы мыслей"""
    SAFETY_CHECK = "safety_check"
    INTENT_CLASSIFICATION = "intent_classification"
    MEMORY_SEARCH = "memory_search"
    FACT_RETRIEVAL = "fact_retrieval"
    EPISODE_RECALL = "episode_recall"
    PROCEDURE_APPLICATION = "procedure_application"
    EMOTION_UPDATE = "emotion_update"
    STRATEGY_DECISION = "strategy_decision"
    MODEL_SELECTION = "model_selection"
    CLAIM_EXTRACTION = "claim_extraction"
    CLAIM_VERIFICATION = "claim_verification"
    MEMORY_STORAGE = "memory_storage"
    PERSONA_ADJUSTMENT = "persona_adjustment"
    EVENT_EMISSION = "event_emission"


@dataclass
class Thought:
    """
    Отдельная "мысль" — атомарный процесс мышления
    
    Каждая мысль имеет:
    - Тип (что происходит)
    - Содержимое (что именно)
    - Уверенность (насколько система уверена)
    - Источники (откуда взята информация)
    """
    id: str
    type: ThoughtType
    content: str
    timestamp: datetime
    confidence: float = 0.5
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "confidence": round(self.confidence, 2),
            "sources": self.sources,
            "metadata": self.metadata
        }


class ThoughtVisualizer:
    """
    🧠 Визуализатор мыслей
    
    Преобразует сырые данные пайплайна в понятные мысли,
    которые можно показать в UI.
    """
    
    def __init__(self):
        self._thought_buffer: List[Thought] = []
        self._max_buffer_size = 50  # Последние 50 мыслей
        self._request_thoughts: Dict[str, List[Thought]] = {}
        
        logger.info("✅ ThoughtVisualizer инициализирован")
    
    def create_thought(
        self,
        thought_type: ThoughtType,
        content: str,
        request_id: str = None,
        confidence: float = 0.5,
        sources: List[str] = None,
        metadata: Dict = None
    ) -> Thought:
        """
        Создает новую мысль
        
        Args:
            thought_type: Тип мысли
            content: Содержимое (человекочитаемое)
            request_id: ID запроса (опционально)
            confidence: Уверенность (0.0 - 1.0)
            sources: Источники информации
            metadata: Дополнительные данные
        
        Returns:
            Thought: Созданная мысль
        """
        thought = Thought(
            id=str(hash(f"{datetime.now().timestamp()}_{content[:20]}")),
            type=thought_type,
            content=content,
            timestamp=datetime.now(),
            confidence=confidence,
            sources=sources or [],
            metadata=metadata or {}
        )
        
        # Добавляем в буфер
        self._thought_buffer.append(thought)
        if len(self._thought_buffer) > self._max_buffer_size:
            self._thought_buffer.pop(0)
        
        # Добавляем в запрос-специфичные мысли
        if request_id:
            if request_id not in self._request_thoughts:
                self._request_thoughts[request_id] = []
            self._request_thoughts[request_id].append(thought)
        
        logger.debug(f"🧠 Мысль: {thought_type.value} — {content[:50]}...")
        return thought
    
    # === Методы для создания мыслей разных типов ===
    
    def safety_check(self, passed: bool, warning: str = None) -> Thought:
        """Мысль о проверке безопасности"""
        if passed:
            content = "✅ Проверка безопасности пройдена"
        else:
            content = f"⚠️ Блокировка: {warning or 'Запрос заблокирован'}"
        
        return self.create_thought(
            ThoughtType.SAFETY_CHECK,
            content,
            confidence=1.0 if passed else 0.9
        )
    
    def intent_classification(
        self, 
        intent: str, 
        confidence: float,
        pipeline: List[str] = None
    ) -> Thought:
        """Мысль о классификации намерения"""
        content = f"🎯 Намерение: {intent} (уверенность: {confidence:.0%})"
        
        if pipeline:
            content += f" → Пайплайн: {' → '.join(pipeline[:3])}"
        
        return self.create_thought(
            ThoughtType.INTENT_CLASSIFICATION,
            content,
            confidence=confidence,
            metadata={"intent": intent, "pipeline": pipeline}
        )
    
    def memory_search(
        self, 
        memory_type: str, 
        results_count: int,
        query: str = None
    ) -> Thought:
        """Мысль о поиске в памяти"""
        memory_names = {
            "rag": "📚 RAG",
            "facts": "📝 Факты",
            "episodic": "📜 Эпизоды",
            "semantic": "🔧 Процедур",
            "vector": "🧠 Векторная"
        }
        
        name = memory_names.get(memory_type, memory_type)
        content = f"{name}: найдено {results_count} записей"
        
        return self.create_thought(
            ThoughtType.MEMORY_SEARCH,
            content,
            confidence=0.8 if results_count > 0 else 0.3,
            sources=[memory_type],
            metadata={"count": results_count, "query": query}
        )
    
    def fact_retrieval(self, facts: List[str]) -> Thought:
        """Мысль об извлечении фактов"""
        content = f"📝 Факты: {len(facts)} найдено"
        if facts:
            content += f" — {facts[0][:50]}..."
        
        return self.create_thought(
            ThoughtType.FACT_RETRIEVAL,
            content,
            confidence=0.7,
            sources=["fact_memory"],
            metadata={"facts_count": len(facts), "sample": facts[0] if facts else None}
        )
    
    def episode_recall(self, episodes: List[Dict]) -> Thought:
        """Мысль о вспоминании эпизодов"""
        content = f"📜 Эпизоды: {len(episodes)} похожих ситуаций"
        
        if episodes:
            ep = episodes[0]
            content += f" — {ep.get('topic', 'unknown')}: {ep.get('user_message', '')[:30]}..."
        
        return self.create_thought(
            ThoughtType.EPISODE_RECALL,
            content,
            confidence=0.6,
            sources=["episodic_memory"],
            metadata={"episodes_count": len(episodes)}
        )
    
    def procedure_application(self, procedure_name: str, steps: List[str]) -> Thought:
        """Мысль о применении процедуры"""
        content = f"🔧 Процедура '{procedure_name}' применена"
        if steps:
            content += f" ({len(steps)} шагов)"
        
        return self.create_thought(
            ThoughtType.PROCEDURE_APPLICATION,
            content,
            confidence=0.8,
            sources=["semantic_memory"],
            metadata={"procedure": procedure_name, "steps": steps}
        )
    
    def emotion_update(self, emotion_state: Dict) -> Thought:
        """Мысль об обновлении эмоций"""
        # Форматируем эмоции в читаемый вид
        emotions = []
        for key, value in emotion_state.items():
            if isinstance(value, (int, float)):
                emotions.append(f"{key}: {value:.2f}")
        
        content = f"😊 Эмоции: {', '.join(emotions[:3])}"
        
        return self.create_thought(
            ThoughtType.EMOTION_UPDATE,
            content,
            confidence=0.9,
            metadata=emotion_state
        )
    
    def strategy_decision(
        self, 
        strategy: str, 
        reason: str,
        confidence: float
    ) -> Thought:
        """Мысль о выборе стратегии"""
        strategy_names = {
            "simple": "⚡ Простая",
            "deep": "🧠 Глубокая",
            "creative": "🎨 Творческая",
            "reflective": "🤔 Рефлексивная",
            "safety": "🛡️ Безопасная",
            "learning": "📚 Обучающая"
        }
        
        name = strategy_names.get(strategy, strategy)
        content = f"{name} стратегия: {reason[:60]}"
        
        return self.create_thought(
            ThoughtType.STRATEGY_DECISION,
            content,
            confidence=confidence,
            metadata={"strategy": strategy, "reason": reason}
        )
    
    def model_selection(self, model: str, provider: str) -> Thought:
        """Мысль о выборе модели"""
        content = f"🤖 Модель: {provider} ({model})"
        
        return self.create_thought(
            ThoughtType.MODEL_SELECTION,
            content,
            confidence=0.95,
            metadata={"model": model, "provider": provider}
        )
    
    def claim_extraction(self, claims_count: int) -> Thought:
        """Мысль об извлечении утверждений"""
        content = f"🔍 Утверждения: {claims_count} извлечено"
        
        return self.create_thought(
            ThoughtType.CLAIM_EXTRACTION,
            content,
            confidence=0.8,
            metadata={"claims_count": claims_count}
        )
    
    def claim_verification(
        self, 
        verified_count: int, 
        total_count: int,
        confidence: float
    ) -> Thought:
        """Мысль о верификации утверждений"""
        pct = (verified_count / total_count * 100) if total_count > 0 else 0
        content = f"✅ Верификация: {verified_count}/{total_count} ({pct:.0f}%) "
        content += f"(уверенность: {confidence:.0%})"
        
        return self.create_thought(
            ThoughtType.CLAIM_VERIFICATION,
            content,
            confidence=confidence,
            metadata={
                "verified": verified_count,
                "total": total_count,
                "confidence": confidence
            }
        )
    
    def memory_storage(self, memory_type: str, success: bool) -> Thought:
        """Мысль о сохранении в память"""
        memory_names = {
            "episodic": "📜 Эпизод",
            "rag": "📚 RAG",
            "vector": "🧠 Векторная",
            "smartcache": "⚡ Кэш"
        }
        
        name = memory_names.get(memory_type, memory_type)
        icon = "✅" if success else "⚠️"
        content = f"{icon} Сохранено в {name}"
        
        return self.create_thought(
            ThoughtType.MEMORY_STORAGE,
            content,
            confidence=1.0 if success else 0.5,
            sources=[memory_type]
        )
    
    def persona_adjustment(self, adjustments: Dict[str, float]) -> Thought:
        """Мысль о корректировке персоны"""
        changes = []
        for key, value in adjustments.items():
            direction = "+" if value > 0 else ""
            changes.append(f"{key}: {direction}{value:.2f}")
        
        content = f"👤 Персона: {', '.join(changes[:3])}"
        
        return self.create_thought(
            ThoughtType.PERSONA_ADJUSTMENT,
            content,
            confidence=0.7,
            metadata=adjustments
        )
    
    def event_emission(self, event_type: str) -> Thought:
        """Мысль об испускании события"""
        content = f"📡 Событие: {event_type}"
        
        return self.create_thought(
            ThoughtType.EVENT_EMISSION,
            content,
            confidence=0.9,
            metadata={"event_type": event_type}
        )
    
    # === Методы доступа ===
    
    def get_recent_thoughts(self, limit: int = 20) -> List[Thought]:
        """Возвращает последние мысли"""
        return self._thought_buffer[-limit:]
    
    def get_request_thoughts(self, request_id: str) -> List[Thought]:
        """Возвращает мысли для конкретного запроса"""
        return self._request_thoughts.get(request_id, [])
    
    def clear_request_thoughts(self, request_id: str):
        """Очищает мысли для запроса"""
        if request_id in self._request_thoughts:
            del self._request_thoughts[request_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        type_counts = {}
        for thought in self._thought_buffer:
            type_counts[thought.type.value] = \
                type_counts.get(thought.type.value, 0) + 1
        
        return {
            "total_thoughts": len(self._thought_buffer),
            "type_distribution": type_counts,
            "active_requests": len(self._request_thoughts)
        }


# Глобальный экземпляр
_visualizer: Optional[ThoughtVisualizer] = None


def get_thought_visualizer() -> ThoughtVisualizer:
    """Возвращает глобальный визуализатор мыслей"""
    global _visualizer
    if _visualizer is None:
        _visualizer = ThoughtVisualizer()
    return _visualizer