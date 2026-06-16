import functools
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger("padplus.safe_context")


def safe_execute(
    func: Callable,
    default_return: Any = None,
    log_msg: str = "",
    log_level: str = "warning",
    reraise: bool = False,
) -> Callable:
    """
    Обёртка для функций, которые не должны прерывать выполнение.

    Args:
        func: Функция для обёртки
        default_return: Значение по умолчанию при ошибке
        log_msg: Сообщение для логирования (если пусто — используется имя функции)
        log_level: Уровень логирования (debug, info, warning, error)
        reraise: Пробрасывать исключение дальше

    Returns:
        Обёрнутую функцию
    """
    log_fn = getattr(logger, log_level, logger.warning)
    msg = log_msg or f"{func.__name__} failed"

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            log_fn(f"{msg}: {e}")
            if reraise:
                raise
            return default_return

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_fn(f"{msg}: {e}")
            if reraise:
                raise
            return default_return

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


import asyncio


def safe_endpoint(default: Any = None, log: str = ""):
    """
    Декоратор для API эндпоинтов: ловит исключения, логирует, возвращает default.

    Args:
        default: Значение по умолчанию при ошибке
        log: Сообщение для логирования
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                msg = log or f"Endpoint {func.__name__} failed"
                logger.error(f"{msg}: {e}", exc_info=True)
                return default
        return wrapper
    return decorator


def safe_phase(default: Any = None):
    """
    Декоратор для pipeline phases: ловит исключения, логирует, возвращает default.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Phase {func.__name__} failed: {e}")
                return default
        return wrapper
    return decorator
