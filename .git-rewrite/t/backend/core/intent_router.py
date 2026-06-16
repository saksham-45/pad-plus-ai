"""
🎯 IntentRouter — Главный оркестратор PAD+ AI

Определяет режим обработки запроса и собирает пайплайн.

Intent Types:
- CHAT_GENERAL — обычный диалог
- CHAT_RAG — нужен поиск по памяти/знаниям
- CLARIFY — нужно уточнение
- TASK_CREATE — пользователь ставит задачу
- TASK_EXECUTE — продолжение автономной задачи
- MEMORY_WRITE — явная запись в память
- KNOWLEDGE_QUERY — вопрос к графу знаний
- SYSTEM_ADMIN — настройки/отладка
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
import re
import logging

logger = logging.getLogger("PAD+.router")


class IntentType(Enum):
    """Типы намерений пользователя"""
    CHAT_GENERAL = "chat_general"           # Обычный диалог
    CHAT_RAG = "chat_rag"                   # Нужен RAG контекст
    CLARIFY = "clarify"                     # Нужно уточнение
    TASK_CREATE = "task_create"             # Создание задачи
    TASK_EXECUTE = "task_execute"           # Выполнение задачи
    MEMORY_WRITE = "memory_write"           # Запись в память
    KNOWLEDGE_QUERY = "knowledge_query"     # Вопрос к графу знаний
    SYSTEM_ADMIN = "system_admin"           # Настройки системы
    UNKNOWN = "unknown"                     # Неопределённый


@dataclass
class PipelineStep:
    """Шаг пайплайна обработки"""
    name: str
    module: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    optional: bool = False


@dataclass
class ProviderStrategy:
    """Стратегия выбора провайдера"""
    primary: str
    fallback: List[str] = field(default_factory=list)
    reason: str = ""
    
    def to_dict(self) -> dict:
        return {
            "primary": self.primary,
            "fallback": self.fallback,
            "reason": self.reason
        }


@dataclass
class RoutingResult:
    """Результат маршрутизации"""
    intent: IntentType
    confidence: float
    pipeline: List[PipelineStep]
    provider: ProviderStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "pipeline": [
                {"name": s.name, "module": s.module, "action": s.action}
                for s in self.pipeline
            ],
            "provider": self.provider.to_dict(),
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class IntentRouter:
    """
    🎯 IntentRouter — главный диспетчер системы
    
    Решает:
    - Что делать с запросом
    - Какие модули включить
    - Какой провайдер выбрать
    """
    
    # Паттерны для классификации намерений
    INTENT_PATTERNS = {
        IntentType.KNOWLEDGE_QUERY: [
            r"что ты знаешь о",
            r"расскажи про",
            r"что такое",
            r"кто такой",
            r"какой смысл",
            r"в чём разница между",
            r"сравни",
            r"объясни (мне |как )?",
        ],
        IntentType.MEMORY_WRITE: [
            r"запомни",
            r"сохрани в память",
            r"запиши",
            r"мне нужно",
            r"важно:",
            r"не забудь",
            r"заметка:",
        ],
        IntentType.TASK_CREATE: [
            r"составь план",
            r"создай задачу",
            r"сделай план",
            r"организуй",
            r"разработай план",
            r"мне нужен план",
            r"поставь цель",
        ],
        IntentType.TASK_EXECUTE: [
            r"продолжи",
            r"следующий шаг",
            r"выполни задачу",
            r"что дальше",
            r"автономный режим",
        ],
        IntentType.CLARIFY: [
            r"\?$",  # Заканчивается вопросом
            r"почему",
            r"зачем",
            r"каким образом",
            r"что если",
            r"а что насчёт",
        ],
        IntentType.SYSTEM_ADMIN: [
            r"покажи состояние",
            r"статус системы",
            r"настройки",
            r"очисти память",
            r"режим",
            r"debug",
            r"admin",
        ],
        IntentType.CHAT_RAG: [
            r"помнишь",
            r"мы говорили",
            r"раньше ты сказал",
            r"в прошлый раз",
            r"по твоим словам",
            r"что ты (думаешь|знаешь) о",
        ],
    }
    
    # Слова-индикаторы для RAG
    RAG_INDICATORS = [
        "факт", "информация", "данные", "знание", "известно",
        "согласно", "по данным", "исследование", "источник"
    ]
    
    def __init__(self):
        self._routing_history: List[RoutingResult] = []
    
    def classify_intent(
        self,
        user_message: str,
        conversation_state: Dict = None,
        emotion_state: Dict = None,
        memory_snapshot: Dict = None
    ) -> Tuple[IntentType, float]:
        """
        Классифицирует намерение пользователя
        
        Returns:
            (intent_type, confidence)
        """
        text = user_message.lower().strip()
        
        # Проверяем паттерны
        scores = {}
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[intent] = min(score / len(patterns), 1.0)
        
        # Дополнительные проверки
        
        # RAG indicators
        rag_score = sum(1 for ind in self.RAG_INDICATORS if ind in text) / len(self.RAG_INDICATORS)
        if rag_score > 0.1:
            scores[IntentType.CHAT_RAG] = scores.get(IntentType.CHAT_RAG, 0) + rag_score
        
        # Вопросительный знак в конце = CLARIFY или KNOWLEDGE_QUERY
        if text.endswith("?"):
            if IntentType.KNOWLEDGE_QUERY not in scores:
                scores[IntentType.CLARIFY] = scores.get(IntentType.CLARIFY, 0) + 0.3
        
        # Если длинный запрос = скорее всего KNOWLEDGE_QUERY или CHAT_RAG
        if len(text.split()) > 10:
            scores[IntentType.CHAT_RAG] = scores.get(IntentType.CHAT_RAG, 0) + 0.2
        
        # Если ничего не определено = CHAT_GENERAL
        if not scores:
            return (IntentType.CHAT_GENERAL, 0.6)
        
        # Выбираем лучший
        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] * 2, 1.0)  # Масштабируем
        
        return (best_intent, round(confidence, 2))
    
    def build_pipeline(
        self,
        intent: IntentType,
        user_message: str,
        context: Dict = None
    ) -> List[PipelineStep]:
        """
        Строит пайплайн обработки для данного намерения
        """
        pipelines = {
            IntentType.CHAT_GENERAL: [
                PipelineStep("check_cache", "memory.smartcache", "get"),
                PipelineStep("get_emotion", "emotion.pad_model", "get_state"),
                PipelineStep("compose_prompt", "core.dialogue", "format"),
                PipelineStep("call_llm", "llm.litellm_service", "generate"),
                PipelineStep("update_emotion", "emotion.pad_model", "apply_event"),
                PipelineStep("track_analytics", "analytics.metrics", "track"),
            ],
            IntentType.CHAT_RAG: [
                PipelineStep("check_cache", "memory.smartcache", "get"),
                PipelineStep("retrieve_rag", "memory.rag", "hybrid_search"),
                PipelineStep("get_emotion", "emotion.pad_model", "get_state"),
                PipelineStep("compose_prompt", "core.dialogue", "format_with_context"),
                PipelineStep("call_llm", "llm.litellm_service", "generate"),
                PipelineStep("truth_verify", "core.truth_loop", "verify"),
                PipelineStep("memory_update", "memory.rag", "add_dialog"),
                PipelineStep("update_emotion", "emotion.pad_model", "apply_event"),
                PipelineStep("track_analytics", "analytics.metrics", "track"),
            ],
            IntentType.KNOWLEDGE_QUERY: [
                PipelineStep("retrieve_rag", "memory.rag", "hybrid_search"),
                PipelineStep("query_graph", "knowledge.graph", "query"),
                PipelineStep("get_emotion", "emotion.pad_model", "get_state"),
                PipelineStep("compose_prompt", "core.dialogue", "format_with_knowledge"),
                PipelineStep("call_llm", "llm.litellm_service", "generate"),
                PipelineStep("truth_verify", "core.truth_loop", "verify"),
                PipelineStep("knowledge_update", "knowledge.graph", "add_from_dialog"),
                PipelineStep("memory_update", "memory.rag", "add_dialog"),
            ],
            IntentType.CLARIFY: [
                PipelineStep("retrieve_rag", "memory.rag", "search"),
                PipelineStep("get_emotion", "emotion.pad_model", "get_state"),
                PipelineStep("compose_prompt", "core.dialogue", "format_clarify"),
                PipelineStep("call_llm", "llm.litellm_service", "generate"),
                PipelineStep("memory_update", "memory.rag", "add_dialog"),
            ],
            IntentType.MEMORY_WRITE: [
                PipelineStep("parse_fact", "core.truth_loop", "extract_claims"),
                PipelineStep("write_fact", "memory.fact_memory", "add"),
                PipelineStep("update_graph", "knowledge.graph", "add_concept"),
                PipelineStep("confirm", "core.dialogue", "format_confirm"),
                PipelineStep("call_llm", "llm.litellm_service", "generate"),
            ],
            IntentType.TASK_CREATE: [
                PipelineStep("parse_task", "autonomy.task_engine", "parse"),
                PipelineStep("create_task", "autonomy.task_engine", "create"),
                PipelineStep("get_emotion", "emotion.pad_model", "get_state"),
                PipelineStep("compose_prompt", "core.dialogue", "format_task"),
                PipelineStep("call_llm", "llm.litellm_service", "generate"),
            ],
            IntentType.TASK_EXECUTE: [
                PipelineStep("get_task", "autonomy.task_engine", "get_current"),
                PipelineStep("execute_step", "autonomy.task_engine", "execute_step"),
                PipelineStep("compose_prompt", "core.dialogue", "format_progress"),
                PipelineStep("call_llm", "llm.litellm_service", "generate"),
            ],
            IntentType.SYSTEM_ADMIN: [
                PipelineStep("get_status", "core.system", "get_status"),
                PipelineStep("format_response", "core.dialogue", "format_admin"),
            ],
        }
        
        return pipelines.get(intent, pipelines[IntentType.CHAT_GENERAL])
    
    def select_provider(
        self,
        intent: IntentType,
        emotion_state: Dict = None,
        complexity: str = "medium"
    ) -> ProviderStrategy:
        """
        Выбирает стратегию провайдера
        """
        # Базовая стратегия
        strategies = {
            IntentType.CHAT_GENERAL: ProviderStrategy(
                primary="litellm",
                fallback=["fallback"],
                reason="Стандартный диалог"
            ),
            IntentType.CHAT_RAG: ProviderStrategy(
                primary="litellm",
                fallback=["fallback"],
                reason="RAG требует качественного ответа"
            ),
            IntentType.KNOWLEDGE_QUERY: ProviderStrategy(
                primary="litellm",
                fallback=["fallback"],
                reason="Сложный запрос к знаниям"
            ),
            IntentType.CLARIFY: ProviderStrategy(
                primary="litellm",
                fallback=["fallback"],
                reason="Уточнение требует понимания"
            ),
            IntentType.MEMORY_WRITE: ProviderStrategy(
                primary="litellm",
                fallback=["fallback"],
                reason="Запись в память важна"
            ),
            IntentType.TASK_CREATE: ProviderStrategy(
                primary="litellm",
                fallback=["fallback"],
                reason="Планирование требует качества"
            ),
            IntentType.SYSTEM_ADMIN: ProviderStrategy(
                primary="local",
                fallback=[],
                reason="Системные команды локальные"
            ),
        }
        
        strategy = strategies.get(intent, strategies[IntentType.CHAT_GENERAL])
        
        # Корректируем на основе эмоций
        if emotion_state:
            тревога = emotion_state.get("тревога", 0.5)
            if тревога > 0.7:
                strategy.reason += " (высокая тревога — нужен качественный ответ)"
        
        return strategy
    
    def route(
        self,
        user_message: str,
        conversation_state: Dict = None,
        emotion_state: Dict = None,
        memory_snapshot: Dict = None,
        user_profile: Dict = None
    ) -> RoutingResult:
        """
        Главный метод маршрутизации
        
        Возвращает полный результат маршрутизации
        """
        # 1. Классифицируем намерение
        intent, confidence = self.classify_intent(
            user_message,
            conversation_state,
            emotion_state,
            memory_snapshot
        )
        
        # 2. Строим пайплайн
        pipeline = self.build_pipeline(intent, user_message, conversation_state)
        
        # 3. Выбираем провайдера
        provider = self.select_provider(intent, emotion_state)
        
        # 4. Формируем результат
        result = RoutingResult(
            intent=intent,
            confidence=confidence,
            pipeline=pipeline,
            provider=provider,
            metadata={
                "message_length": len(user_message),
                "has_context": conversation_state is not None,
                "emotion_influence": emotion_state is not None
            }
        )
        
        # Сохраняем в историю
        self._routing_history.append(result)
        
        logger.info(
            f"🎯 Маршрутизация: {intent.value} "
            f"(confidence: {confidence}, provider: {provider.primary})"
        )
        
        return result
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Статистика маршрутизации"""
        if not self._routing_history:
            return {"total": 0}
        
        intent_counts = {}
        provider_counts = {}
        
        for r in self._routing_history:
            intent_counts[r.intent.value] = intent_counts.get(r.intent.value, 0) + 1
            provider_counts[r.provider.primary] = provider_counts.get(r.provider.primary, 0) + 1
        
        return {
            "total_routes": len(self._routing_history),
            "intent_distribution": intent_counts,
            "provider_distribution": provider_counts,
            "last_routing": self._routing_history[-1].to_dict() if self._routing_history else None
        }


# Глобальный экземпляр
_router: Optional[IntentRouter] = None


def get_router() -> IntentRouter:
    """Возвращает глобальный маршрутизатор"""
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router