"""
🔒 Security Middleware для PAD+ AI

Обеспечивает базовую безопасность:
- HTTPS принудительное перенаправление
- Rate limiting
- Security headers
- Logging событий безопасности
"""

import time
import logging
from typing import Dict, Optional
from fastapi import Request, Response, HTTPException
try:
    from fastapi.middleware.base import BaseHTTPMiddleware
except ImportError:
    from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse

logger = logging.getLogger("padplus.security")

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware для обеспечения базовой безопасности
    """
    
    def __init__(self, app, https_redirect: bool = True, rate_limit: int = 100):
        super().__init__(app)
        self.https_redirect = https_redirect
        self.rate_limit = rate_limit
        self.rate_limit_storage: Dict[str, Dict] = {}
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Основная логика middleware"""
        
        # 1. HTTPS принудительное перенаправление
        if self.https_redirect and not self._is_https(request):
            return self._redirect_to_https(request)
        
        # 2. Rate limiting
        client_ip = self._get_client_ip(request)
        if not self._check_rate_limit(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"}
            )
        
        # 3. Security headers
        response = await call_next(request)
        self._add_security_headers(response)
        
        # 4. Логирование событий безопасности
        self._log_security_event(request, response)
        
        return response
    
    def _is_https(self, request: Request) -> bool:
        """Проверяет, является ли запрос HTTPS"""
        # Проверяем различные индикаторы HTTPS
        return (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto") == "https" or
            request.headers.get("x-forwarded-ssl") == "on"
        )
    
    def _redirect_to_https(self, request: Request) -> Response:
        """Перенаправляет на HTTPS"""
        https_url = request.url.replace(scheme="https")
        return Response(
            status_code=301,
            headers={"Location": str(https_url)}
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Получает реальный IP клиента"""
        # Проверяем заголовки от прокси
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Проверяет rate limiting"""
        current_time = time.time()
        
        if client_ip not in self.rate_limit_storage:
            self.rate_limit_storage[client_ip] = {
                "requests": [],
                "last_reset": current_time
            }
        
        client_data = self.rate_limit_storage[client_ip]
        
        # Очищаем старые запросы (окно 1 минута)
        client_data["requests"] = [
            req_time for req_time in client_data["requests"]
            if current_time - req_time < 60
        ]
        
        # Проверяем лимит
        if len(client_data["requests"]) >= self.rate_limit:
            logger.warning(f"🚨 Rate limit exceeded for {client_ip}")
            return False
        
        # Добавляем текущий запрос
        client_data["requests"].append(current_time)
        return True
    
    def _add_security_headers(self, response: Response):
        """Добавляет security headers"""
        # Базовые security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP для предотвращения XSS
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://*.supabase.co; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # HSTS для HTTPS
        if self.https_redirect:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    def _log_security_event(self, request: Request, response: Response):
        """Логирует события безопасности"""
        client_ip = self._get_client_ip(request)
        method = request.method
        path = request.url.path
        status_code = response.status_code
        
        # Логируем подозрительные запросы
        if status_code >= 400:
            logger.warning(f"🚨 Security event: {method} {path} - {status_code} from {client_ip}")
        
        # Логируем попытки доступа к чувствительным эндпоинтам
        sensitive_paths = ["/admin", "/keys", "/auth", "/api/v1/keys"]
        if any(sensitive in path for sensitive in sensitive_paths):
            logger.info(f"🔐 Sensitive access: {method} {path} - {status_code} from {client_ip}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Отдельный middleware для rate limiting с настраиваемыми лимитами
    """
    
    def __init__(self, app, requests_per_minute: int = 60, burst_size: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.storage: Dict[str, Dict] = {}
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = self._get_client_ip(request)
        
        if not self._check_rate_limit(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Получает реальный IP клиента"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Проверяет rate limiting с алгоритмом token bucket"""
        current_time = time.time()
        
        if client_ip not in self.storage:
            self.storage[client_ip] = {
                "tokens": self.burst_size,
                "last_update": current_time
            }
        
        bucket = self.storage[client_ip]
        
        # Добавляем токены со временем
        time_passed = current_time - bucket["last_update"]
        tokens_to_add = time_passed * (self.requests_per_minute / 60)
        bucket["tokens"] = min(self.burst_size, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = current_time
        
        # Проверяем наличие токенов
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        
        return False
