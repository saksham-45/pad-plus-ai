"""
🔬 XRayTraceCollector — Сборщик трассировок для X-Ray

Собирает данные со всех стадий пайплайна и преобразует их
в формат, пригодный для визуализации.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import logging
import uuid

logger = logging.getLogger("padplus.xray")


class TraceStage(Enum):
    """Стадии пайплайна для трассировки"""
    SAFETY = "safety"
    INTENT = "intent"
    RETRIEVE = "retrieve"
    PERSONA = "persona"
    GENERATE = "generate"
    VERIFY = "verify"
    REMEMBER = "remember"
    EMIT = "emit"
    COMPLETE = "complete"


@dataclass
class TraceEvent:
    """Событие трассировки"""
    id: str
    request_id: str
    stage: TraceStage
    timestamp: datetime
    duration_ms: float
    data: Dict[str, Any]
    status: str = "success"  # success, error, warning
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "stage": self.stage.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": round(self.duration_ms, 2),
            "data": self.data,
            "status": self.status,
            "error": self.error
        }


@dataclass
class TraceSession:
    """Сессия трассировки — все события для одного запроса"""
    request_id: str
    user_message: str
    start_time: datetime
    events: List[TraceEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed: bool = False
    
    def add_event(self, event: TraceEvent):
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)
    
    def get_summary(self) -> Dict[str, Any]:
        """Возвращает краткую сводку сессии"""
        total_time = 0.0
        stage_times = {}
        
        for event in self.events:
            stage_times[event.stage.value] = event.duration_ms
            total_time += event.duration_ms
        
        return {
            "request_id": self.request_id,
            "user_message": self.user_message,
            "start_time": self.start_time.isoformat(),
            "total_time_ms": round(total_time, 2),
            "stage_times": stage_times,
            "event_count": len(self.events),
            "metadata": self.metadata,
            "completed": self.completed
        }


class XRayTraceCollector:
    """
    🔬 Сборщик трассировок X-Ray
    
    Собирает данные со всех стадий пайплайна и предоставляет
    их для визуализации в реальном времени.
    """
    
    def __init__(self, max_sessions: int = 100):
        self._sessions: Dict[str, TraceSession] = {}
        self._max_sessions = max_sessions
        self._active_sessions: set = set()
        self._event_subscribers: List[callable] = []
        
        logger.info("✅ XRayTraceCollector инициализирован")
    
    def start_session(self, user_message: str, metadata: Dict = None, request_id: str = None) -> str:
        """
        Начинает новую сессию трассировки
        
        Args:
            user_message: Исходное сообщение пользователя
            metadata: Дополнительные метаданные
            request_id: ID сессии (если не указан, генерируется новый)
        
        Returns:
            request_id: Уникальный идентификатор сессии
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        session = TraceSession(
            request_id=request_id,
            user_message=user_message,
            start_time=datetime.now(),
            metadata=metadata or {}
        )
        
        self._sessions[request_id] = session
        self._active_sessions.add(request_id)
        
        # Уведомляем подписчиков
        self._notify_subscribers("session_started", {
            "request_id": request_id,
            "user_message": user_message,
            "timestamp": session.start_time.isoformat()
        })
        
        logger.debug(f"🔬 X-Ray сессия начата: {request_id}")
        return request_id
    
    def record_event(
        self,
        request_id: str,
        stage: TraceStage,
        data: Dict[str, Any],
        duration_ms: float,
        status: str = "success",
        error: str = None
    ) -> TraceEvent:
        """
        Записывает событие трассировки
        
        Args:
            request_id: ID сессии
            stage: Стадия пайплайна
            data: Данные стадии
            duration_ms: Время выполнения стадии
            status: Статус (success, error, warning)
            error: Сообщение об ошибке (если есть)
        
        Returns:
            TraceEvent: Созданное событие
        """
        if request_id not in self._sessions:
            logger.warning(f"🔬 X-Ray: Сессия {request_id} не найдена")
            return None
        
        event = TraceEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            stage=stage,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            data=data,
            status=status,
            error=error
        )
        
        self._sessions[request_id].add_event(event)
        
        # Уведомляем подписчиков
        self._notify_subscribers("event_recorded", event.to_dict())
        
        logger.debug(f"🔬 X-Ray событие: {stage.value} ({duration_ms:.0f}ms)")
        return event
    
    def complete_session(self, request_id: str, final_data: Dict = None):
        """
        Завершает сессию трассировки
        
        Args:
            request_id: ID сессии
            final_data: Финальные данные (ответ, метрики)
        """
        if request_id not in self._sessions:
            logger.warning(f"🔬 X-Ray: Сессия {request_id} не найдена")
            return
        
        session = self._sessions[request_id]
        session.completed = True
        
        if final_data:
            session.metadata.update(final_data)
        
        self._active_sessions.discard(request_id)
        
        # Уведомляем подписчиков
        self._notify_subscribers("session_completed", session.get_summary())
        
        # Очищаем старые сессии
        self._cleanup_old_sessions()
        
        logger.debug(f"🔬 X-Ray сессия завершена: {request_id}")
    
    def get_session(self, request_id: str) -> Optional[TraceSession]:
        """Возвращает сессию по ID"""
        return self._sessions.get(request_id)
    
    def get_active_sessions(self) -> List[TraceSession]:
        """Возвращает активные сессии"""
        return [
            self._sessions[rid] 
            for rid in self._active_sessions 
            if rid in self._sessions
        ]
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Возвращает последние завершенные сессии"""
        completed = [
            s for s in self._sessions.values() 
            if s.completed
        ]
        completed.sort(key=lambda s: s.start_time, reverse=True)
        return [s.get_summary() for s in completed[:limit]]
    
    def subscribe(self, callback: callable):
        """
        Подписывает обработчик на события трассировки
        
        Args:
            callback: Функция, принимающая (event_type, data)
        """
        self._event_subscribers.append(callback)
    
    def unsubscribe(self, callback: callable):
        """Отписывает обработчик"""
        if callback in self._event_subscribers:
            self._event_subscribers.remove(callback)
    
    def _notify_subscribers(self, event_type: str, data: Dict):
        """Уведомляет всех подписчиков о событии"""
        for callback in self._event_subscribers:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"🔬 X-Ray ошибка в подписчике: {e}")
    
    def _cleanup_old_sessions(self):
        """Очищает старые сессии"""
        if len(self._sessions) > self._max_sessions:
            # Оставляем только последние N сессий
            sessions_list = list(self._sessions.values())
            sessions_list.sort(key=lambda s: s.start_time, reverse=True)
            
            to_remove = sessions_list[self._max_sessions:]
            for session in to_remove:
                if session.request_id in self._active_sessions:
                    continue  # Не удаляем активные
                del self._sessions[session.request_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику сборщика"""
        total_sessions = len(self._sessions)
        active_sessions = len(self._active_sessions)
        completed_sessions = sum(1 for s in self._sessions.values() if s.completed)
        
        # Статистика по стадиям
        stage_stats = {}
        for session in self._sessions.values():
            for event in session.events:
                if event.stage.value not in stage_stats:
                    stage_stats[event.stage.value] = {
                        "count": 0,
                        "total_duration_ms": 0.0,
                        "errors": 0
                    }
                stage_stats[event.stage.value]["count"] += 1
                stage_stats[event.stage.value]["total_duration_ms"] += event.duration_ms
                if event.status == "error":
                    stage_stats[event.stage.value]["errors"] += 1
        
        # Среднее время по стадиям
        for stage in stage_stats.values():
            if stage["count"] > 0:
                stage["avg_duration_ms"] = stage["total_duration_ms"] / stage["count"]
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "stage_stats": stage_stats
        }


# Глобальный экземпляр
_trace_collector: Optional[XRayTraceCollector] = None


def get_trace_collector() -> XRayTraceCollector:
    """Возвращает глобальный сборщик трассировок"""
    global _trace_collector
    if _trace_collector is None:
        _trace_collector = XRayTraceCollector()
    return _trace_collector