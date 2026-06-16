"""
📡 EventBus — Шина событий PAD+ AI

Внутренняя коммуникация между модулями.

События:
- dialogue.finished
- memory.updated
- emotion.changed
- knowledge.new_entity
- autonomy.task_created
- truth.claim_verified
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import asyncio
import logging
from collections import defaultdict

logger = logging.getLogger("PAD+.events")


class EventType(Enum):
    """Типы событий системы"""
    # Диалог
    DIALOGUE_STARTED = "dialogue.started"
    DIALOGUE_FINISHED = "dialogue.finished"
    DIALOGUE_ERROR = "dialogue.error"

    # Mind State
    MIND_STATE_UPDATE = "mind_state.update"

    # Память
    MEMORY_UPDATED = "memory.updated"
    MEMORY_CLEARED = "memory.cleared"
    MEMORY_DECAY = "memory.decay"
    
    # Эмоции
    EMOTION_CHANGED = "emotion.changed"
    EMOTION_EXTREME = "emotion.extreme"
    
    # Знания
    KNOWLEDGE_NEW_ENTITY = "knowledge.new_entity"
    KNOWLEDGE_NEW_RELATION = "knowledge.new_relation"
    KNOWLEDGE_CONTRADICTION = "knowledge.contradiction"
    
    # Автономия
    AUTONOMY_TASK_CREATED = "autonomy.task_created"
    AUTONOMY_TASK_COMPLETED = "autonomy.task_completed"
    AUTONOMY_REFLECTION = "autonomy.reflection"
    
    # Истина
    TRUTH_CLAIM_VERIFIED = "truth.claim_verified"
    TRUTH_CONTRADICTION_FOUND = "truth.contradiction_found"
    
    # Система
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"
    
    # Роутинг
    ROUTER_INTENT_CLASSIFIED = "router.intent_classified"
    ROUTER_PIPELINE_EXECUTED = "router.pipeline_executed"


@dataclass
class Event:
    """
    Событие в системе
    
    Каждое событие имеет:
    - type: тип события
    - data: полезная нагрузка
    - source: источник события
    - timestamp: время
    - priority: приоритет (0-10)
    """
    type: EventType
    data: Dict[str, Any]
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 5
    id: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = f"{self.type.value}_{int(self.timestamp.timestamp())}"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority
        }


# Тип обработчика событий
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]


class EventBus:
    """
    📡 EventBus — шина событий для внутренней коммуникации
    
    Особенности:
    - Sync и Async обработчики
    - Приоритеты событий
    - История событий
    - Подписка на типы событий
    """
    
    def __init__(self, history_size: int = 100):
        self._sync_handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._async_handlers: Dict[EventType, List[AsyncEventHandler]] = defaultdict(list)
        self._global_handlers: List[EventHandler] = []
        self._history: List[Event] = []
        self._history_size = history_size
        self._event_count = 0
    
    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
        priority: int = 5
    ) -> None:
        """
        Подписывает обработчик на тип события
        
        Args:
            event_type: тип события
            handler: функция-обработчик
            priority: приоритет (меньше = раньше)
        """
        self._sync_handlers[event_type].append(handler)
        logger.debug(
            f"📡 Подписка: {handler.__name__} -> {event_type.value}"
        )
    
    def subscribe_async(
        self,
        event_type: EventType,
        handler: AsyncEventHandler
    ) -> None:
        """Подписывает async обработчик"""
        self._async_handlers[event_type].append(handler)
        logger.debug(
            f"📡 Async подписка: {handler.__name__} -> {event_type.value}"
        )
    
    def subscribe_global(self, handler: EventHandler) -> None:
        """Подписывает на все события"""
        self._global_handlers.append(handler)
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> bool:
        """Отписывает обработчик"""
        if handler in self._sync_handlers[event_type]:
            self._sync_handlers[event_type].remove(handler)
            return True
        return False
    
    def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any] = None,
        source: str = "unknown",
        priority: int = 5
    ) -> Event:
        """
        Отправляет событие
        
        Sync обработчики вызываются сразу,
        Async нужно обрабатывать отдельно
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source,
            priority=priority
        )
        
        # Сохраняем в историю
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history.pop(0)
        
        self._event_count += 1
        
        # Вызываем sync обработчики
        handlers = self._sync_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"Ошибка в обработчике {handler.__name__}: {e}"
                )
        
        # Вызываем глобальные обработчики
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Ошибка в global handler: {e}")
        
        logger.debug(f"📡 Событие: {event_type.value} от {source}")
        
        return event
    
    async def emit_async(
        self,
        event_type: EventType,
        data: Dict[str, Any] = None,
        source: str = "unknown"
    ) -> Event:
        """Отправляет событие и ждёт async обработчиков"""
        event = self.emit(event_type, data, source)
        
        # Вызываем async обработчики
        handlers = self._async_handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Ошибка в async handler: {e}")
        
        return event
    
    def get_history(
        self,
        event_type: EventType = None,
        limit: int = 20
    ) -> List[Event]:
        """Возвращает историю событий"""
        if event_type:
            events = [e for e in self._history if e.type == event_type]
        else:
            events = self._history.copy()
        
        return events[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика шины событий"""
        type_counts = defaultdict(int)
        for event in self._history:
            type_counts[event.type.value] += 1
        
        return {
            "total_events": self._event_count,
            "history_size": len(self._history),
            "handlers_count": sum(
                len(h) for h in self._sync_handlers.values()
            ),
            "async_handlers_count": sum(
                len(h) for h in self._async_handlers.values()
            ),
            "event_distribution": dict(type_counts)
        }
    
    def clear_history(self):
        """Очищает историю"""
        self._history.clear()
        logger.info("📡 История событий очищена")


# === ДЕКОРАТОРЫ ===

def on_event(event_type: EventType):
    """
    Декоратор для подписки на события
    
    @on_event(EventType.DIALOGUE_FINISHED)
    def handle_dialogue(event: Event):
        print(f"Диалог завершён: {event.data}")
    """
    def decorator(func: EventHandler) -> EventHandler:
        # Регистрируем при импорте модуля
        # (нужен глобальный event_bus)
        func._event_subscription = event_type
        return func
    return decorator


# Глобальный экземпляр
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Возвращает глобальную шину событий"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def emit(event_type: EventType, data: Dict = None, source: str = "") -> Event:
    """Удобная функция для отправки событий"""
    return get_event_bus().emit(event_type, data, source)


# === СТАНДАРТНЫЕ ОБРАБОТЧИКИ ===

def setup_default_handlers():
    """Устанавливает стандартные обработчики"""
    bus = get_event_bus()
    
    def log_dialogue(event: Event):
        logger.info(
            f"💬 Диалог завершён: "
            f"{event.data.get('prompt', '')[:50]}..."
        )
    
    def log_emotion(event: Event):
        emotion = event.data.get('state', {})
        logger.info(
            f"😊 Эмоция изменена: "
            f"радость={emotion.get('радость', 0):.2f}"
        )
    
    def log_knowledge(event: Event):
        entity = event.data.get('entity', '')
        logger.info(f"🕸️ Новая сущность: {entity}")
    
    def log_autonomy(event: Event):
        task = event.data.get('task', '')
        logger.info(f"🤖 Задача создана: {task}")
    
    bus.subscribe(EventType.DIALOGUE_FINISHED, log_dialogue)
    bus.subscribe(EventType.EMOTION_CHANGED, log_emotion)
    bus.subscribe(EventType.KNOWLEDGE_NEW_ENTITY, log_knowledge)
    bus.subscribe(EventType.AUTONOMY_TASK_CREATED, log_autonomy)