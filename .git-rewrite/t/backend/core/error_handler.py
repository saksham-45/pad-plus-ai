"""
🔴 Централизованный обработчик ошибок
Исправление тихого поглощения исключений
"""

from dataclasses import dataclass
from enum import Enum
import logging
import time
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger("padplus.error_handler")


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HandledError:
    component: str
    error: Exception
    severity: ErrorSeverity
    timestamp: float
    fallback_applied: bool = False
    fallback_value: Any = None
    user_notification: Optional[str] = None


class CentralErrorHandler:
    """
    Централизованный обработчик ошибок

    Заменяет 27 независимых try/except блоков на единый механизм
    Предотвращает тихое поглощение исключений
    Ведёт учёт всех ошибок
    Применяет соответствующие fallback стратегии
    Уведомляет пользователя о деградации системы
    """

    def __init__(self):
        self._errors: list[HandledError] = []
        self._error_counts: Dict[str, int] = {}
        self._last_clear_time = time.time()
        self._circuit_breakers: Dict[str, dict] = {}

    async def try_execute(
        self,
        component: str,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        fallback_value: Any = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        notify_user: bool = False,
        user_message: Optional[str] = None,
        circuit_breaker_threshold: int = 3,
        **kwargs
    ) -> Any:
        """
        Безопасное выполнение функции с обработкой ошибок

        Args:
            component: Название компонента
            func: Функция для выполнения
            fallback: Функция fallback при ошибке
            fallback_value: Значение по умолчанию
            severity: Важность ошибки
            notify_user: Нужно ли уведомить пользователя
            user_message: Сообщение пользователю
            circuit_breaker_threshold: Порог срабатывания Circuit Breaker
        """

        # Проверяем Circuit Breaker для этого компонента
        if component in self._circuit_breakers:
            cb = self._circuit_breakers[component]
            if cb['failure_count'] >= circuit_breaker_threshold:
                if time.time() - cb['last_failure'] < 60:
                    logger.warning(f"🔴 Circuit Breaker открыт для {component}, сразу возвращаем fallback")
                    return fallback_value if fallback is None else await fallback(*args, **kwargs)
                else:
                    # Сброс Circuit Breaker после таймаута
                    cb['failure_count'] = 0

        try:
            result = await func(*args, **kwargs)

            # Сброс счётчика ошибок при успехе
            if component in self._error_counts:
                self._error_counts[component] = 0
            if component in self._circuit_breakers:
                self._circuit_breakers[component]['failure_count'] = 0

            return result

        except Exception as e:
            # Учёт ошибки
            if component not in self._error_counts:
                self._error_counts[component] = 0
            self._error_counts[component] += 1

            if component not in self._circuit_breakers:
                self._circuit_breakers[component] = {'failure_count': 0, 'last_failure': 0}

            self._circuit_breakers[component]['failure_count'] += 1
            self._circuit_breakers[component]['last_failure'] = time.time()

            # Логирование
            error_count = self._error_counts[component]
            logger.warning(f"🔴 Ошибка в компоненте {component} ({error_count}/{circuit_breaker_threshold}): {str(e)}", exc_info=True)

            # Регистрация ошибки
            handled_error = HandledError(
                component=component,
                error=e,
                severity=severity,
                timestamp=time.time(),
                fallback_applied=fallback is not None or fallback_value is not None,
                user_notification=user_message if notify_user else None
            )
            self._errors.append(handled_error)

            # Применение fallback
            if fallback is not None:
                try:
                    return await fallback(*args, **kwargs)
                except Exception as fallback_error:
                    logger.warning(f"🔴 Fallback для {component} тоже упал: {str(fallback_error)}")

            return fallback_value

    def get_component_status(self, component: str) -> dict:
        """Получить статус компонента"""
        return {
            "error_count": self._error_counts.get(component, 0),
            "circuit_breaker_open": self._circuit_breakers.get(component, {}).get('failure_count', 0) >= 3,
            "last_error_time": self._circuit_breakers.get(component, {}).get('last_failure', 0)
        }

    def get_system_health(self) -> dict:
        """Общее состояние здоровья системы"""
        total_errors = len(self._errors)
        critical_errors = sum(1 for e in self._errors if e.severe == ErrorSeverity.CRITICAL)

        return {
            "total_errors": total_errors,
            "critical_errors": critical_errors,
            "components_affected": len(self._error_counts),
            "components_degraded": [c for c, cb in self._circuit_breakers.items() if cb['failure_count'] >= 3]
        }


# Глобальный экземпляр
_error_handler: Optional[CentralErrorHandler] = None


def get_error_handler() -> CentralErrorHandler:
    """Получить глобальный обработчик ошибок"""
    global _error_handler
    if _error_handler is None:
        _error_handler = CentralErrorHandler()
        logger.info("✅ Централизованный обработчик ошибок инициализирован")
    return _error_handler