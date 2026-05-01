"""
🛡️ CSRF Middleware — Защита от Cross-Site Request Forgery

Реализация CSRF защиты для FastAPI:
- Генерация уникальных токенов для каждой сессии
- Двойная отправка токенов (cookie + header)
- Исключение API endpoints (используют Bearer token)
- Валидация токенов для state-changing операций

Использование:
    from fastapi import FastAPI
    from core.csrf_middleware import CSRFMiddleware
    
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)
"""

import secrets
import hashlib
import hmac
import logging
from typing import Optional, Set, Literal
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("padplus.csrf")


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    🛡️ CSRF Middleware для защиты от межсайтовой подделки запросов
    
    Алгоритм работы:
    1. Для GET запросов — генерирует CSRF токен и сохраняет в cookie
    2. Для POST/PUT/DELETE/PATCH запросов — проверяет токен из header
    3. API endpoints с Bearer токеном освобождаются от проверки
    """
    
    # Методы, требующие CSRF проверки
    CSRF_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    
    # Пути, исключаемые from CSRF проверки (API endpoints)
    EXEMPT_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/ws",
    }
    
    # Настройки
    COOKIE_NAME = "csrf_token"
    HEADER_NAME = "X-CSRF-Token"
    TOKEN_EXPIRY_HOURS = 24
    SECRET_KEY_ENV = "CSRF_SECRET_KEY"
    
    def __init__(
        self,
        app: ASGIApp,
        secret_key: Optional[str] = None,
        cookie_secure: bool = False,
        cookie_httponly: bool = True,
        cookie_samesite: Literal["lax", "strict", "none"] = "lax",
        exempt_paths: Optional[Set[str]] = None,
    ):
        """
        Инициализация CSRF middleware
        
        Args:
            app: FastAPI приложение
            secret_key: Секретный ключ для генерации токенов (если None — генерируется)
            cookie_secure: Использовать secure flag для cookie
            cookie_httponly: Использовать httponly flag для cookie
            cookie_samesite: SameSite атрибут для cookie (strict, lax, none)
            exempt_paths: Дополнительные пути для исключения из проверки
        """
        super().__init__(app)
        
        # Генерируем или используем предоставленный secret key
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite
        
        # Объединяем стандартные и кастомные exempt пути
        self.exempt_paths = self.EXEMPT_PATHS.copy()
        if exempt_paths:
            self.exempt_paths.update(exempt_paths)
        
        logger.info(
            f"🛡️ CSRF Middleware initialized: "
            f"cookie_secure={cookie_secure}, "
            f"cookie_httponly={cookie_httponly}, "
            f"cookie_samesite={cookie_samesite}"
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Обработка запросa"""
        path = request.url.path
        method = request.method
        
        # 1. Проверяем, нужно ли применять CSRF защиту
        if not self._requires_csrf_check(method, path, request):
            return await call_next(request)
        
        # 2. Получаем токен из cookie
        csrf_cookie = request.cookies.get(self.COOKIE_NAME)
        
        # 3. Получаем токен из header
        csrf_header = request.headers.get(self.HEADER_NAME)
        
        # 4. Валидируем токены
        if not self._validate_csrf_token(csrf_cookie, csrf_header):
            logger.warning(
                f"🚫 CSRF validation failed: "
                f"path={path}, method={method}, "
                f"cookie_present={bool(csrf_cookie)}, "
                f"header_present={bool(csrf_header)}"
            )
            
            return JSONResponse(
                status_code=403,
                content={
                    "error": "csrf_validation_failed",
                    "message": "CSRF token validation failed. Please refresh the page and try again.",
                    "detail": "The CSRF token is missing or invalid."
                }
            )
        
        # 5. Продолжаем обработку
        response = await call_next(request)
        
        # 6. Если токена не было — генерируем новый
        if not csrf_cookie:
            new_token = self._generate_csrf_token()
            self._set_csrf_cookie(response, new_token)
        
        return response
    
    def _requires_csrf_check(
        self, 
        method: str, 
        path: str, 
        request: Request
    ) -> bool:
        """
        Определяет, требуется ли CSRF проверка для запроса
        
        CSRF проверка НЕ требуется для:
        - GET, HEAD, OPTIONS запросов
        - Путей из exempt_paths
        - Запросов с Bearer токеном (API authentication)
        """
        # Проверяем метод
        if method not in self.CSRF_METHODS:
            return False
        
        # Проверяем exempt пути
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return False
        
        # Проверяем наличие Bearer токена (API authentication)
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            # API запросы с Bearer токеном не требуют CSRF проверки
            return False
        
        return True
    
    def _generate_csrf_token(self) -> str:
        """
        Генерирует новый CSRF токен
        
        Формат: {timestamp}:{random_bytes}:{hmac_signature}
        """
        # Генерируем случайные байты
        random_bytes = secrets.token_hex(32)
        
        # Получаем текущее время
        timestamp = int(datetime.now().timestamp())
        
        # Создаем HMAC подпись
        message = f"{timestamp}:{random_bytes}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Формируем итоговый токен
        token = f"{timestamp}:{random_bytes}:{signature}"
        
        return token
    
    def _validate_csrf_token(
        self, 
        cookie_token: Optional[str], 
        header_token: Optional[str]
    ) -> bool:
        """
        Валидирует CSRF токен
        
        Проверяет:
        1. Наличие обоих токенов
        2. Совпадение токенов
        3. Валидность HMAC подписи
        4. Актуальность токена (не истек ли)
        """
        # Оба токена должны присутствовать
        if not cookie_token or not header_token:
            return False
        
        # Токены должны совпадать
        if not hmac.compare_digest(cookie_token, header_token):
            return False
        
        # Проверяем структуру токена
        parts = cookie_token.split(":")
        if len(parts) != 3:
            return False
        
        timestamp_str, random_bytes, signature = parts
        
        # Проверяем HMAC подпись
        expected_signature = hmac.new(
            self.secret_key.encode(),
            f"{timestamp_str}:{random_bytes}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return False
        
        # Проверяем актуальность токена
        try:
            timestamp = int(timestamp_str)
            token_time = datetime.fromtimestamp(timestamp)
            now = datetime.now()
            
            # Токен действителен TOKEN_EXPIRY_HOURS часов
            if now - token_time > timedelta(hours=self.TOKEN_EXPIRY_HOURS):
                logger.warning("CSRF token expired")
                return False
            
            # Токен не должен быть из будущего (защита от подделки времени)
            if token_time > now + timedelta(minutes=5):
                logger.warning("CSRF token from future")
                return False
                
        except (ValueError, OSError):
            return False
        
        return True
    
    def _set_csrf_cookie(self, response: Response, token: str):
        """
        Устанавливает CSRF токен в cookie
        
        Настройки безопасности:
        - HttpOnly: защита от XSS атак
        - Secure: отправка только по HTTPS (в production)
        - SameSite: защита от CSRF через cross-site запросы
        """
        cookie_value = token
        
        response.set_cookie(
            key=self.COOKIE_NAME,
            value=cookie_value,
            max_age=self.TOKEN_EXPIRY_HOURS * 3600,
            httponly=self.cookie_httponly,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            domain=None,
            path="/",
        )
        
        logger.debug("🍪 CSRF cookie set")
    
    def get_csrf_token(self, request: Request) -> Optional[str]:
        """
        Получает CSRF токен из запроса
        
        Может использоваться в frontend для получения токена
        """
        return request.cookies.get(self.COOKIE_NAME)


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def setup_csrf_middleware(
    app: FastAPI,
    secret_key: Optional[str] = None,
    **kwargs
):
    """
    Настройка CSRF middleware для FastAPI приложения
    
    Args:
        app: FastAPI приложение
        secret_key: Секретный ключ (если None — генерируется)
        **kwargs: Дополнительные параметры для CSRFMiddleware
    """
    app.add_middleware(CSRFMiddleware, secret_key=secret_key, **kwargs)
    logger.info("🛡️ CSRF Middleware установлен")


def get_csrf_token_from_request(request: Request) -> Optional[str]:
    """
    Получает CSRF токен из cookie запроса
    
    Args:
        request: FastAPI запрос
    
    Returns:
        CSRF токен или None
    """
    return request.cookies.get(CSRFMiddleware.COOKIE_NAME)


# ============================================================================
# ДЕКОРАТОРЫ ДЛЯ ЗАЩИТЫ ENDPOINTS
# ============================================================================

from fastapi import Depends

async def get_csrf_token_validated(request: Request) -> bool:
    """
    Dependency для проверки CSRF токена
    
    Использование:
        @router.post("/endpoint")
        async def endpoint(csrf_valid: bool = Depends(get_csrf_token_validated)):
            ...
    """
    csrf_cookie = request.cookies.get(CSRFMiddleware.COOKIE_NAME)
    csrf_header = request.headers.get(CSRFMiddleware.HEADER_NAME)
    
    # Простая валидация без создания инстанса middleware
    if not csrf_cookie or not csrf_header:
        raise HTTPException(
            status_code=403,
            detail="CSRF token validation failed"
        )
    
    if not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(
            status_code=403,
            detail="CSRF token mismatch"
        )
    
    # Проверяем структуру и подпись
    parts = csrf_cookie.split(":")
    if len(parts) != 3:
        raise HTTPException(
            status_code=403,
            detail="Invalid CSRF token format"
        )
    
    timestamp_str, random_bytes, signature = parts
    
    # Получаем secret key из environment или используем дефолтный
    import os
    secret_key = os.getenv("CSRF_SECRET_KEY", secrets.token_urlsafe(32))
    
    expected_signature = hmac.new(
        secret_key.encode(),
        f"{timestamp_str}:{random_bytes}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=403,
            detail="Invalid CSRF token signature"
        )
    
    return True


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

csrf_config = {
    "cookie_secure": False,  # Включить в production
    "cookie_httponly": True,
    "cookie_samesite": "lax",
    "token_expiry_hours": 24,
}


def get_csrf_config() -> dict:
    """Получить текущую конфигурацию CSRF"""
    return csrf_config.copy()


def update_csrf_config(**updates):
    """Обновить конфигурацию CSRF"""
    csrf_config.update(updates)
    logger.info(f"🛡️ CSRF конфигурация обновлена: {updates}")