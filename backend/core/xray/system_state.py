"""
🧠 SystemState — Состояние системы PAD+ AI

Отслеживает текущее состояние системы для принятия решений:
- Когнитивная нагрузка
- Уверенность системы
- Последние ошибки
- Активные сессии

Используется X-Ray Brain для адаптации стратегий.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
import time
import logging

logger = logging.getLogger("padplus.xray.state")


@dataclass
class SystemState:
    """
    Текущее состояние системы
    
    Отслеживает:
    - load: когнитивная нагрузка (0.0 - 1.0)
    - confidence: уверенность системы (0.0 - 1.0)
    - recent_errors: количество последних ошибок
    - active_sessions: количество активных сессий
    - last_updated: время последнего обновления
    """
    load: float = 0.0              # 0.0 - 1.0
    confidence: float = 1.0        # 0.0 - 1.0
    recent_errors: int = 0         # последние ошибки
    active_sessions: int = 0       # активные сессии
    last_updated: float = field(default_factory=time.time)
    total_requests: int = 0        # всего запросов
    success_count: int = 0         # успешных запросов
    
    def update_from_result(self, result: dict):
        """
        Обновляет состояние из результата pipeline
        
        Args:
            result: результат выполнения запроса (PipelineResult.to_dict())
        """
        self.total_requests += 1
        
        # Обновляем уверенность
        self.confidence = result.get('confidence', 0.5)
        
        # Считаем ошибки
        if not result.get('success', True):
            self.recent_errors += 1
        else:
            self.success_count += 1
        
        # Вычисляем нагрузку на основе времени выполнения
        execution_time = result.get('execution_time_ms', 0)
        if execution_time > 5000:  # > 5 секунд
            self.load = min(1.0, self.load + 0.2)
        elif execution_time > 2000:  # > 2 секунд
            self.load = min(1.0, self.load + 0.1)
        else:
            # Постепенно снижаем нагрузку при быстрых ответах
            self.load = max(0.0, self.load - 0.05)
        
        # Сбрасываем ошибки со временем
        if self.success_count % 10 == 0:
            self.recent_errors = max(0, self.recent_errors - 1)
        
        self.last_updated = time.time()
        
        logger.debug(
            f"SystemState updated: load={self.load:.2f}, "
            f"confidence={self.confidence:.2f}, errors={self.recent_errors}"
        )
    
    def update_load(self, load: float):
        """Прямо обновляет нагрузку"""
        self.load = max(0.0, min(1.0, load))
        self.last_updated = time.time()
    
    def get_snapshot(self) -> dict:
        """
        Возвращает снимок состояния для передачи в Brain
        
        Returns:
            dict с текущими параметрами состояния
        """
        return {
            "load": round(self.load, 3),
            "confidence": round(self.confidence, 3),
            "recent_errors": self.recent_errors,
            "active_sessions": self.active_sessions,
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "success_rate": round(self.success_count / max(1, self.total_requests), 3),
            "last_updated": self.last_updated
        }
    
    def should_simplify(self) -> bool:
        """
        Определяет, нужно ли упростить стратегию
        
        Returns:
            True если система перегружена
        """
        return self.load > 0.8 or self.recent_errors > 5
    
    def should_use_fallback(self) -> bool:
        """
        Определяет, нужно ли использовать fallback стратегию
        
        Returns:
            True если система в критическом состоянии
        """
        return self.load > 0.95 or self.recent_errors > 10
    
    def get_health_status(self) -> str:
        """
        Возвращает статус здоровья системы
        
        Returns:
            "healthy", "degraded", или "critical"
        """
        if self.load > 0.9 or self.recent_errors > 10:
            return "critical"
        elif self.load > 0.7 or self.recent_errors > 5:
            return "degraded"
        else:
            return "healthy"
    
    def to_dict(self) -> dict:
        """Преобразует состояние в словарь"""
        return {
            "load": round(self.load, 3),
            "confidence": round(self.confidence, 3),
            "recent_errors": self.recent_errors,
            "active_sessions": self.active_sessions,
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "success_rate": round(self.success_count / max(1, self.total_requests), 3),
            "health_status": self.get_health_status(),
            "should_simplify": self.should_simplify(),
            "should_use_fallback": self.should_use_fallback(),
            "last_updated": self.last_updated
        }


class SystemStateManager:
    """
    Менеджер управления состоянием системы
    
    Управляет жизненным циклом SystemState,
    предоставляет методы для обновления и получения состояния
    """
    
    def __init__(self):
        """Инициализация менеджера"""
        self._state = SystemState()
        self._history: list = []
        self._max_history = 100
        logger.info("🧠 SystemStateManager инициализирован")
    
    def get_state(self) -> SystemState:
        """
        Возвращает текущее состояние
        
        Returns:
            SystemState: текущее состояние системы
        """
        return self._state
    
    def update(self, result: dict):
        """
        Обновляет состояние из результата
        
        Args:
            result: результат выполнения запроса
        """
        self._state.update_from_result(result)
        
        # Сохраняем в историю
        snapshot = self._state.get_snapshot()
        self._history.append(snapshot)
        
        # Очищаем старую историю
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def update_load(self, load: float):
        """
        Прямо обновляет нагрузку
        
        Args:
            load: значение нагрузки (0.0 - 1.0)
        """
        self._state.update_load(load)
    
    def increment_sessions(self):
        """Увеличивает счётчик активных сессий"""
        self._state.active_sessions += 1
        self._state.last_updated = time.time()
    
    def decrement_sessions(self):
        """Уменьшает счётчик активных сессий"""
        self._state.active_sessions = max(0, self._state.active_sessions - 1)
        self._state.last_updated = time.time()
    
    def get_snapshot(self) -> dict:
        """
        Возвращает снимок текущего состояния
        
        Returns:
            dict с параметрами состояния
        """
        return self._state.get_snapshot()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику менеджера
        
        Returns:
            dict со статистикой
        """
        if not self._history:
            return {
                "current_state": self._state.to_dict(),
                "history_size": 0,
                "avg_load": 0.0,
                "avg_confidence": 0.0
            }
        
        # Вычисляем средние значения
        avg_load = sum(h["load"] for h in self._history) / len(self._history)
        avg_confidence = sum(h["confidence"] for h in self._history) / len(self._history)
        
        return {
            "current_state": self._state.to_dict(),
            "history_size": len(self._history),
            "avg_load": round(avg_load, 3),
            "avg_confidence": round(avg_confidence, 3),
            "health_trend": self._get_health_trend()
        }
    
    def _get_health_trend(self) -> str:
        """
        Определяет тренд здоровья системы
        
        Returns:
            "improving", "declining", или "stable"
        """
        if len(self._history) < 5:
            return "stable"
        
        recent_loads = [h["load"] for h in self._history[-5:]]
        older_loads = [h["load"] for h in self._history[-10:-5]]
        
        if not older_loads:
            return "stable"
        
        recent_avg = sum(recent_loads) / len(recent_loads)
        older_avg = sum(older_loads) / len(older_loads)
        
        diff = recent_avg - older_avg
        
        if diff < -0.1:
            return "improving"
        elif diff > 0.1:
            return "declining"
        else:
            return "stable"
    
    def reset(self):
        """Сбрасывает состояние (для тестов)"""
        self._state = SystemState()
        self._history.clear()
        logger.info("SystemStateManager reset")


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_state_manager: SystemStateManager = None


def get_system_state_manager() -> SystemStateManager:
    """
    Возвращает глобальный менеджер состояния системы
    
    Returns:
        SystemStateManager: единый экземпляр для всей системы
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = SystemStateManager()
        logger.info("✅ SystemStateManager инициализирован")
    return _state_manager


def reset_system_state():
    """Сбрасывает глобальный менеджер (для тестов)"""
    global _state_manager
    _state_manager = None