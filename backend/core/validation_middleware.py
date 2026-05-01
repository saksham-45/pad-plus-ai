"""
🛡️ ValidationMiddleware — Middleware для валидации и санитизации API запросов

Автоматическая санитизация всех входящих данных:
- Тела запроса (JSON)
- Query параметров
- Заголовков (опционально)

Использование:
    from fastapi import FastAPI
    from core.validation_middleware import ValidationMiddleware
    
    app = FastAPI()
    app.add_middleware(ValidationMiddleware)
"""

import json
import logging
import re
import traceback
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, Request, Response, HTTPException
from starlette.datastructures import QueryParams
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.input_sanitizer import sanitize_input, validate_input, SanitizerSeverity

logger = logging.getLogger("padplus.validation")


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    🛡️ Middleware для автоматической валидации и санитизации запросов
    
    Функции:
    - Санitизация JSON тела запроса
    - Санitизация query параметров
    - Блокировка опасных запросов
    - Логирование подозрительных запросов
    """
    
    def __init__(
        self,
        app: ASGIApp,
        max_body_length: int = 100000,
        max_query_length: int = 1000,
        sanitize_headers: bool = False,
        block_threats: bool = True,
        exclude_paths: Optional[List[str]] = None
    ):
        """
        Инициализация middleware
        
        Args:
            app: FastAPI приложение
            max_body_length: Максимальная длина тела запроса
            max_query_length: Максимальная длина query параметра
            sanitize_headers: Санитизировать ли заголовки
            block_threats: Блокировать ли запросы с угрозами
            exclude_paths: Список путей для исключения из валидации
        """
        super().__init__(app)
        self.max_body_length = max_body_length
        self.max_query_length = max_query_length
        self.sanitize_headers = sanitize_headers
        self.block_threats = block_threats
        self.exclude_paths = exclude_paths or [
            "/metrics",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
        
        logger.info(
            f"🛡️ ValidationMiddleware initialized: "
            f"max_body_length={max_body_length}, block_threats={block_threats}"
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Обработка запроса"""
        path = request.url.path
        
        # ✅ ПОЛНОСТЬЮ ИСКЛЮЧАЕМ WebSocket /ws ИЗ ВСЕХ ПРОВЕРОК
        if path == "/ws":
            return await call_next(request)
        
        # Пропускаем исключенные пути
        if self._should_exclude(path):
            return await call_next(request)
        
        # Проверяем размер тела запроса
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_body_length:
                logger.warning(
                    f"🛡️ Превышен размер тела запроса: {content_length} > {self.max_body_length}, "
                    f"path: {path}"
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "payload_too_large",
                        "message": f"Размер запроса превышает лимит ({self.max_body_length} байт)",
                        "detail": "The request payload is too large"
                    }
                )
        
        # Санитизируем query параметры
        sanitized_query = self._sanitize_query_params(request.query_params)
        request.scope["query_params"] = sanitized_query
        
        # Санитизируем тело запроса (для POST/PUT/PATCH)
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if body:
                    # Проверяем размер
                    if len(body) > self.max_body_length:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": "payload_too_large",
                                "message": f"Размер запроса превышает лимит ({self.max_body_length} байт)"
                            }
                        )
                    
                    # Пытаемся распарсить JSON
                    try:
                        json_body = json.loads(body)
                        sanitized_body = self._sanitize_json(json_body)
                        
                        # Проверяем на угрозы
                        threats = self._check_threats(json_body)
                        if threats and self.block_threats:
                            logger.warning(
                                f"🛡️ Обнаружены угрозы в запросе: {path}, "
                                f"угроз: {len(threats)}"
                            )
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "error": "threat_detected",
                                    "message": "Запрос содержит потенциально опасные данные",
                                    "threats_detected": len(threats),
                                    "detail": "Request contains potentially dangerous data"
                                }
                            )
                        
                        # Сохраняем санированное тело
                        request.scope["_sanitized_body"] = json.dumps(sanitized_body).encode()
                        request.scope["_sanitized_json"] = sanitized_body
                        
                    except json.JSONDecodeError:
                        # Не JSON - просто проверяем на угрозы
                        text_body = body.decode('utf-8', errors='ignore')
                        threats = self._check_text_threats(text_body)
                        if threats and self.block_threats:
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "error": "threat_detected",
                                    "message": "Запрос содержит потенциально опасные данные"
                                }
                            )
                        request.scope["_sanitized_body"] = body
                        
            except Exception as e:
                logger.error(
                    f"🛡️ Ошибка обработки тела запроса: {e}",
                    extra={
                        "path": path,
                        "method": request.method,
                        "traceback": traceback.format_exc()
                    }
                )
        
        # Продолжаем обработку
        response = await call_next(request)
        
        # Добавляем заголовки безопасности
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response
    
    def _should_exclude(self, path: str) -> bool:
        """Проверяет, нужно ли исключать путь из валидации"""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    def _sanitize_query_params(self, query_params: QueryParams) -> Dict[str, str]:
        """Санитизация query параметров"""
        sanitized = {}
        for key, value in query_params.multi_items():
            # Санитизируем ключ и значение
            clean_key = sanitize_input(key, context="general", max_length=100)
            clean_value = sanitize_input(value, context="general", max_length=self.max_query_length)
            sanitized[clean_key] = clean_value
        return sanitized
    
    def _sanitize_json(self, data: Any) -> Any:
        """Рекурсивная санитизация JSON данных"""
        if isinstance(data, str):
            return sanitize_input(data, context="general", max_length=self.max_body_length)
        elif isinstance(data, dict):
            return {
                sanitize_input(str(k), context="general", max_length=100): self._sanitize_json(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_json(item) for item in data]
        elif isinstance(data, (int, float, bool, type(None))):
            return data
        else:
            return sanitize_input(str(data), context="general")
    
    def _check_threats(self, data: Any) -> List[Dict[str, Any]]:
        """Проверка JSON данных на угрозы"""
        threats = []
        
        if isinstance(data, str):
            is_safe, _, warnings = validate_input(data, context="sql")
            if not is_safe:
                threats.append({"type": "input_validation", "warnings": warnings})
        elif isinstance(data, dict):
            for value in data.values():
                threats.extend(self._check_threats(value))
        elif isinstance(data, list):
            for item in data:
                threats.extend(self._check_threats(item))
        
        return threats
    
    def _check_text_threats(self, text: str) -> List[Dict[str, Any]]:
        """Проверка текста на угрозы"""
        is_safe, _, warnings = validate_input(text, context="sql")
        if not is_safe:
            return [{"type": "input_validation", "warnings": warnings}]
        return []


class ValidatedRequest:
    """
    Вспомогательный класс для получения санированных данных запроса
    """
    
    @staticmethod
    async def get_json(request: Request) -> Optional[Dict[str, Any]]:
        """
        Получить санированное JSON тело запроса
        
        Args:
            request: FastAPI запрос
        
        Returns:
            Санированный JSON или None
        """
        # Проверяем, есть ли санированные данные
        if "_sanitized_json" in request.scope:
            return request.scope["_sanitized_json"]
        
        # Если нет - пытаемся распарсить оригинальное тело
        try:
            body = await request.body()
            if body:
                return json.loads(body)
        except (json.JSONDecodeError, Exception):
            pass
        
        return None
    
    @staticmethod
    async def get_body(request: Request) -> Optional[bytes]:
        """
        Получить санированное тело запроса
        
        Args:
            request: FastAPI запрос
        
        Returns:
            Санированное тело или None
        """
        if "_sanitized_body" in request.scope:
            return request.scope["_sanitized_body"]
        
        try:
            return await request.body()
        except Exception:
            return None


def setup_validation_middleware(app: FastAPI, **kwargs):
    """
    Настройка middleware валидации для FastAPI приложения
    
    Args:
        app: FastAPI приложение
        **kwargs: Дополнительные параметры for ValidationMiddleware
    """
    app.add_middleware(ValidationMiddleware, **kwargs)
    logger.info("🛡️ ValidationMiddleware установлен")


# Глобальные настройки валидации
validation_config = {
    "max_body_length": 100000,
    "max_query_length": 1000,
    "sanitize_headers": False,
    "block_threats": True,
    "exclude_paths": [
        "/metrics",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]
}


def get_validation_config() -> Dict[str, Any]:
    """Получить текущую конфигурацию валидации"""
    return validation_config.copy()


def update_validation_config(**updates):
    """Обновить конфигурацию валидации"""
    validation_config.update(updates)
    logger.info(f"🛡️ Конфигурация валидации обновлена: {updates}")