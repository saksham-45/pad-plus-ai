"""
🔌 DB Circuit Breaker — Защита от каскадных сбоев БД

Circuit Breaker паттерн для подключения к Supabase:
- closed: нормальная работа
- open: БД недоступна, используем fallback
- half_open: попытка восстановления

Цель: Система продолжает работать при временных проблемах с БД
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict, List
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("padplus.db_circuit_breaker")


class CircuitState(str, Enum):
    """Состояния Circuit Breaker"""
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # БД недоступна
    HALF_OPEN = "half_open"  # Попытка восстановления


@dataclass
class CircuitStats:
    """Статистика Circuit Breaker"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    fallback_calls: int = 0
    state_transitions: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0


class DBCircuitBreaker:
    """
    Circuit Breaker для подключения к базе данных
    
    Паттерн:
    1. При успехе — сбрасываем счетчик ошибок
    2. При N последовательных ошибках — открываем circuit
    3. В открытом состоянии — используем fallback
    4. Через timeout — пытаемся восстановить (half_open)
    5. При успехе в half_open — закрываем circuit
    """
    
    def __init__(
        self,
        failure_threshold: int = 3,        # Количество ошибок для открытия
        recovery_timeout: int = 30,         # Секунд до попытки восстановления
        fallback_enabled: bool = True,      # Включить fallback
        max_fallback_age: int = 300,        # Макс возраст fallback данных (сек)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.fallback_enabled = fallback_enabled
        self.max_fallback_age = max_fallback_age
        
        # Состояние
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: Optional[datetime] = None
        self._stats = CircuitStats()
        
        # Fallback хранилище (in-memory кэш)
        self._fallback_cache: Dict[str, Dict[str, Any]] = {}
        
        # Блокировка для потокобезопасности
        self._lock = asyncio.Lock()
        
        logger.info(f"🔌 DB Circuit Breaker initialized: threshold={failure_threshold}, "
                   f"timeout={recovery_timeout}s")
    
    @property
    def state(self) -> CircuitState:
        """Текущее состояние с автоматическим переходом в half_open"""
        if self._state == CircuitState.OPEN and self._opened_at:
            elapsed = (datetime.now() - self._opened_at).total_seconds()
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("🔄 DB Circuit Breaker перешел в HALF_OPEN (попытка восстановления)")
                self._stats.state_transitions += 1
        return self._state
    
    @property
    def is_open(self) -> bool:
        """Открыт ли circuit (БД недоступна)"""
        return self._state == CircuitState.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Закрыт ли circuit (нормальная работа)"""
        return self._state == CircuitState.CLOSED
    
    async def execute(
        self,
        operation: str,
        func: Callable,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        Выполняет операцию с Circuit Breaker
        
        Args:
            operation: Название операции для логирования
            func: Асинхронная функция для выполнения
            fallback: Fallback функция (если circuit открыт)
            **kwargs: Аргументы для func и fallback
        
        Returns:
            Результат выполнения func или fallback
        
        Raises:
            Exception: Если операция не удалась и нет fallback
        """
        async with self._lock:
            self._stats.total_calls += 1
            
            # Если circuit открыт — пробуем fallback
            if self.state == CircuitState.OPEN:
                self._stats.fallback_calls += 1
                logger.warning(f"⚠️ DB Circuit Breaker открыт для '{operation}', используем fallback")
                
                if fallback and self.fallback_enabled:
                    return await self._execute_fallback(operation, fallback, **kwargs)
                else:
                    raise Exception(f"DB unavailable for '{operation}', no fallback configured")
            
            # Пытаемся выполнить операцию
            try:
                result = await func(**kwargs)
                await self._on_success(operation)
                return result
                
            except Exception as e:
                await self._on_failure(operation, e)
                
                # Пытаемся fallback
                if fallback and self.fallback_enabled:
                    logger.info(f"🔄 Попытка fallback для '{operation}' после ошибки")
                    return await self._execute_fallback(operation, fallback, **kwargs)
                
                raise
    
    async def _on_success(self, operation: str):
        """Обработка успешного выполнения"""
        self._failure_count = 0
        self._stats.successful_calls += 1
        self._stats.last_success_time = datetime.now()
        self._stats.consecutive_failures = 0
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._opened_at = None
            logger.info(f"✅ DB Circuit Breaker закрыт после успешной операции '{operation}'")
            self._stats.state_transitions += 1
        
        elif self._state == CircuitState.CLOSED:
            logger.debug(f"✅ Операция '{operation}' выполнена успешно")
    
    async def _on_failure(self, operation: str, error: Exception):
        """Обработка ошибки выполнения"""
        self._failure_count += 1
        self._stats.failed_calls += 1
        self._stats.last_failure_time = datetime.now()
        self._stats.consecutive_failures += 1
        
        logger.warning(f"❌ Операция '{operation}' не удалась (ошибок подряд: {self._failure_count}): {error}")
        
        # Открываем circuit при достижении порога
        if self._failure_count >= self.failure_threshold and self._state == CircuitState.CLOSED:
            self._state = CircuitState.OPEN
            self._opened_at = datetime.now()
            logger.error(f"🔥 DB Circuit Breaker ОТКРЫТ после {self._failure_count} ошибок в '{operation}'")
            self._stats.state_transitions += 1
    
    async def _execute_fallback(
        self,
        operation: str,
        fallback: Callable,
        **kwargs
    ) -> Any:
        """Выполняет fallback функцию"""
        try:
            if asyncio.iscoroutinefunction(fallback):
                return await fallback(**kwargs)
            else:
                return fallback(**kwargs)
        except Exception as e:
            logger.error(f"❌ Fallback для '{operation}' не удался: {e}")
            raise
    
    # === Fallback Cache Methods ===
    
    def cache_for_fallback(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Кэширует значение для использования в fallback
        
        Args:
            key: Ключ кэша
            value: Значение
            ttl: Время жизни в секундах (по умолчанию max_fallback_age)
        """
        self._fallback_cache[key] = {
            "value": value,
            "cached_at": datetime.now(),
            "ttl": ttl or self.max_fallback_age,
        }
        logger.debug(f"💾 Кэш для fallback: {key}")
    
    def get_from_fallback(self, key: str) -> Optional[Any]:
        """
        Получает значение из fallback кэша
        
        Args:
            key: Ключ кэша
        
        Returns:
            Значение или None если истекло или не найдено
        """
        if key not in self._fallback_cache:
            return None
        
        entry = self._fallback_cache[key]
        age = (datetime.now() - entry["cached_at"]).total_seconds()
        
        if age > entry["ttl"]:
            # Удаляем истекшее
            del self._fallback_cache[key]
            logger.debug(f"🗑️ Истек срок кэша для '{key}'")
            return None
        
        return entry["value"]
    
    def clear_fallback_cache(self):
        """Очищает весь fallback кэш"""
        self._fallback_cache.clear()
        logger.info("🧹 Fallback кэш очищен")
    
    # === Stats and Monitoring ===
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику Circuit Breaker"""
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "fallback_cache_size": len(self._fallback_cache),
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "fallback_calls": self._stats.fallback_calls,
                "state_transitions": self._stats.state_transitions,
                "consecutive_failures": self._stats.consecutive_failures,
                "last_failure": self._stats.last_failure_time.isoformat() if self._stats.last_failure_time else None,
                "last_success": self._stats.last_success_time.isoformat() if self._stats.last_success_time else None,
            }
        }
    
    def reset(self):
        """Сбрасывает Circuit Breaker в исходное состояние"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
        self._stats = CircuitStats()
        self.clear_fallback_cache()
        logger.info("🔄 DB Circuit Breaker сброшен")
    
    def force_open(self):
        """Принудительно открывает circuit (для тестирования)"""
        self._state = CircuitState.OPEN
        self._opened_at = datetime.now()
        logger.warning("🔥 DB Circuit Breaker принудительно открыт")
    
    def force_close(self):
        """Принудительно закрывает circuit (для тестирования)"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
        logger.info("✅ DB Circuit Breaker принудительно закрыт")


# === Fallback Helpers ===

def create_db_fallback(default_value: Any = None):
    """
    Создает простую fallback функцию с возвратом значения по умолчанию
    
    Usage:
        fallback = create_db_fallback({"data": [], "count": 0})
        result = await cb.execute("query", func, fallback=fallback)
    """
    async def fallback(**kwargs):
        logger.warning(f"🔄 Fallback: возвращаем значение по умолчанию")
        return default_value
    return fallback


def create_empty_result_fallback():
    """Создает fallback, возвращающий пустой результат (как в HARDENING_PLAN)"""
    async def fallback(**kwargs):
        logger.warning("🔄 Fallback: возвращаем пустой результат")
        return type('obj', (object,), {'data': [], 'count': 0, 'error': None})()
    return fallback


# === Global Instance ===

_db_circuit_breaker: Optional[DBCircuitBreaker] = None


def get_db_circuit_breaker() -> DBCircuitBreaker:
    """Возвращает глобальный DB Circuit Breaker"""
    global _db_circuit_breaker
    if _db_circuit_breaker is None:
        _db_circuit_breaker = DBCircuitBreaker()
    return _db_circuit_breaker


def reset_db_circuit_breaker():
    """Сбрасывает глобальный DB Circuit Breaker (для тестов)"""
    global _db_circuit_breaker
    _db_circuit_breaker = None