"""
🛡️ Safe Endpoint Decorator

Оборачивает эндпоинты в try/except с логированием.
Заменяет 20+ копий `except Exception: pass`.
"""

import logging
from functools import wraps
from fastapi import HTTPException

logger = logging.getLogger("padplus")


def safe_endpoint(error_msg: str = "Internal server error", status_code: int = 500):
    """
    Декоратор для безопасных эндпоинтов

    Usage:
        @router.get("/stats")
        @safe_endpoint("Failed to get stats")
        async def get_stats():
            return {"count": 42}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"{error_msg}: {type(e).__name__}: {e}")
                raise HTTPException(status_code=status_code, detail=error_msg)
        return wrapper
    return decorator


def safe_sync_endpoint(error_msg: str = "Internal server error", status_code: int = 500):
    """То же для синхронных эндпоинтов"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"{error_msg}: {type(e).__name__}: {e}")
                raise HTTPException(status_code=status_code, detail=error_msg)
        return wrapper
    return decorator
