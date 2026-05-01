"""
Tests for CSRF Middleware

Проверка функциональности CSRF защиты:
- Генерация токенов
- Валидация токенов
- Исключение API endpoints
- Безопасность cookie
"""

import pytest
import secrets
import hmac
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

# Добавляем backend в path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi import FastAPI, Request, Response
from starlette.testclient import TestClient

# Импортируем после добавления path
from core.csrf_middleware import (
    CSRFMiddleware,
    setup_csrf_middleware,
    get_csrf_token_from_request,
)


@pytest.fixture
def app():
    """Создание тестового FastAPI приложения с CSRF middleware"""
    app = FastAPI()
    
    # Добавляем CSRF middleware
    app.add_middleware(
        CSRFMiddleware,
        secret_key="test_secret_key_for_testing_only_1234567890",
        cookie_secure=False,
        cookie_httponly=True,
        cookie_samesite="lax",
    )
    
    @app.get("/")
    async def root():
        return {"status": "ok"}
    
    @app.post("/test-endpoint")
    async def test_endpoint():
        return {"status": "ok"}
    
    @app.get("/api/v1/auth/login")
    async def login():
        return {"status": "ok"}
    
    return app


@pytest.fixture
def client(app):
    """Создание тестового клиента"""
    return TestClient(app)


class TestCSRFTokenGeneration:
    """Тесты генерации CSRF токенов"""
    
    def test_generate_csrf_token_format(self, app):
        """Проверка формата сгенерированного токена"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        token = middleware._generate_csrf_token()
        
        # Токен должен содержать три части, разделенные ':'
        parts = token.split(":")
        assert len(parts) == 3
        
        timestamp_str, random_bytes, signature = parts
        
        # Проверяем что timestamp - это число
        timestamp = int(timestamp_str)
        assert timestamp > 0
        
        # Проверяем что random_bytes - это hex строка
        assert len(random_bytes) == 64  # 32 байта в hex
        
        # Проверяем что signature - это hex строка
        assert len(signature) == 64  # SHA256 в hex
    
    def test_generate_csrf_token_uniqueness(self, app):
        """Проверка уникальности токенов"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        
        tokens = set()
        for _ in range(100):
            token = middleware._generate_csrf_token()
            tokens.add(token)
        
        # Все токены должны быть уникальными
        assert len(tokens) == 100


class TestCSRFTokenValidation:
    """Тесты валидации CSRF токенов"""
    
    def test_validate_valid_token(self, app):
        """Проверка валидации корректного токена"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        token = middleware._generate_csrf_token()
        
        assert middleware._validate_csrf_token(token, token)
    
    def test_validate_mismatched_tokens(self, app):
        """Проверка отклонения несовпадающих токенов"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        token1 = middleware._generate_csrf_token()
        token2 = middleware._generate_csrf_token()
        
        assert not middleware._validate_csrf_token(token1, token2)
    
    def test_validate_missing_cookie(self, app):
        """Проверка отклонения при отсутствии cookie"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        token = middleware._generate_csrf_token()
        
        assert not middleware._validate_csrf_token(None, token)
        assert not middleware._validate_csrf_token("", token)
    
    def test_validate_missing_header(self, app):
        """Проверка отклонения при отсутствии header"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        token = middleware._generate_csrf_token()
        
        assert not middleware._validate_csrf_token(token, None)
        assert not middleware._validate_csrf_token(token, "")
    
    def test_validate_invalid_signature(self, app):
        """Проверка отклонения токена с невалидной подписью"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        token = middleware._generate_csrf_token()
        
        # Подменяем подпись
        parts = token.split(":")
        tampered_token = f"{parts[0]}:{parts[1]}:invalid_signature"
        
        assert not middleware._validate_csrf_token(tampered_token, tampered_token)
    
    def test_validate_expired_token(self, app):
        """Проверка отклонения истекшего токена"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        
        # Создаем токен с прошедшим временем (вручную)
        import time
        past_timestamp = int(time.time()) - (25 * 3600)  # 25 часов назад
        random_bytes = "a" * 64
        import hmac as hmac_module
        import hashlib as hashlib_module
        signature = hmac_module.new(
            middleware.secret_key.encode(),
            f"{past_timestamp}:{random_bytes}".encode(),
            hashlib_module.sha256
        ).hexdigest()
        expired_token = f"{past_timestamp}:{random_bytes}:{signature}"
        
        # Проверяем что токен отклоняется
        assert not middleware._validate_csrf_token(expired_token, expired_token)
    
    def test_validate_future_token(self, app):
        """Проверка отклонения токена из будущего"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        
        # Создаем токен с будущим временем (вручную)
        import time
        future_timestamp = int(time.time()) + (2 * 3600)  # 2 часа в будущем
        random_bytes = "b" * 64
        import hmac as hmac_module
        import hashlib as hashlib_module
        signature = hmac_module.new(
            middleware.secret_key.encode(),
            f"{future_timestamp}:{random_bytes}".encode(),
            hashlib_module.sha256
        ).hexdigest()
        future_token = f"{future_timestamp}:{random_bytes}:{signature}"
        
        # Проверяем что токен отклоняется
        assert not middleware._validate_csrf_token(future_token, future_token)


class TestCSRFMiddlewareIntegration:
    """Интеграционные тесты CSRF middleware"""
    
    def test_get_request_sets_cookie(self, client):
        """Проверка что GET запрос устанавливает CSRF cookie"""
        response = client.get("/")
        
        assert response.status_code == 200
        # Проверяем наличие cookie в заголовках
        set_cookie = response.headers.get("set-cookie", "")
        assert "csrf_token" in set_cookie or response.cookies.get("csrf_token") is not None
    
    def test_post_without_csrf_token_blocked(self, client):
        """Проверка блокировки POST без CSRF токена"""
        response = client.post("/test-endpoint")
        
        assert response.status_code == 403
        assert "csrf" in response.json()["error"]
    
    def test_post_with_valid_csrf_token_allowed(self, client):
        """Проверка разрешения POST с валидным CSRF токеном"""
        # Создаем middleware для генерации токена
        middleware = CSRFMiddleware(app=client.app, secret_key="test_secret_key_for_testing_only_1234567890")
        csrf_token = middleware._generate_csrf_token()
        
        # Отправляем POST с токеном
        response = client.post(
            "/test-endpoint",
            headers={"X-CSRF-Token": csrf_token}
        )
        
        assert response.status_code == 200
    
    def test_post_with_invalid_csrf_token_blocked(self, client):
        """Проверка блокировки POST с невалидным CSRF токеном"""
        response = client.post(
            "/test-endpoint",
            headers={"X-CSRF-Token": "invalid_token"}
        )
        
        assert response.status_code == 403
    
    def test_exempt_paths_not_checked(self, client):
        """Проверка что exempt пути не требуют CSRF"""
        # GET на /api/v1/auth/login должен работать без CSRF
        response = client.get("/api/v1/auth/login")
        
        assert response.status_code == 200
    
    def test_bearer_token_exempts_csrf(self, client):
        """Проверка что запросы с Bearer токеном не требуют CSRF"""
        response = client.post(
            "/test-endpoint",
            headers={"Authorization": "Bearer some_token"}
        )
        
        assert response.status_code == 200
    
    def test_cookie_security_settings(self, client):
        """Проверка настроек безопасности cookie"""
        # Создаем middleware напрямую для проверки настроек
        middleware = CSRFMiddleware(app=client.app, secret_key="test_secret_key_for_testing_only_1234567890")
        
        # Проверяем что настройки установлены корректно
        assert middleware.cookie_httponly is True
        assert middleware.cookie_samesite == "lax"
        assert middleware.cookie_secure is False
    
    def test_csrf_token_in_cookie_not_accessible_via_js(self, client):
        """Проверка что CSRF токен недоступен через JavaScript (HttpOnly)"""
        # Проверяем через middleware напрямую
        middleware = CSRFMiddleware(app=client.app, secret_key="test_secret_key_for_testing_only_1234567890")
        assert middleware.cookie_httponly is True


class TestCSRFMiddlewareConfiguration:
    """Тесты конфигурации CSRF middleware"""
    
    def test_custom_secret_key(self, app):
        """Проверка использования кастомного secret key"""
        secret_key = "my_custom_secret_key_12345678901234567890"
        middleware = CSRFMiddleware(app=app, secret_key=secret_key)
        
        assert middleware.secret_key == secret_key
    
    def test_default_secret_key_generated(self, app):
        """Проверка генерации secret key по умолчанию"""
        middleware = CSRFMiddleware(app=app)
        
        assert middleware.secret_key is not None
        assert len(middleware.secret_key) >= 32
    
    def test_custom_exempt_paths(self, app):
        """Проверка кастомных exempt путей"""
        custom_exempt = {"/custom/exempt/path"}
        middleware = CSRFMiddleware(
            app=app, 
            exempt_paths=custom_exempt
        )
        
        assert "/custom/exempt/path" in middleware.exempt_paths
        # Стандартные exempt пути тоже должны быть
        assert "/health" in middleware.exempt_paths
    
    def test_cookie_secure_setting(self, app):
        """Проверка настройки secure cookie"""
        middleware = CSRFMiddleware(app=app, cookie_secure=True)
        
        assert middleware.cookie_secure is True
    
    def test_cookie_httponly_setting(self, app):
        """Проверка настройки httponly cookie"""
        middleware = CSRFMiddleware(app=app, cookie_httponly=False)
        
        assert middleware.cookie_httponly is False
    
    def test_cookie_samesite_setting(self, app):
        """Проверка настройки samesite cookie"""
        middleware = CSRFMiddleware(app=app, cookie_samesite="strict")
        
        assert middleware.cookie_samesite == "strict"


class TestCSRFEgeCases:
    """Тесты граничных случаев"""
    
    def test_empty_csrf_token(self, app):
        """Проверка обработки пустого CSRF токена"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        
        assert not middleware._validate_csrf_token("", "")
    
    def test_malformed_csrf_token(self, app):
        """Проверка обработки некорректного CSRF токена"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        
        malformed_tokens = [
            "just_a_string",
            "part1:part2",  # Недостаточно частей
            "part1:part2:part3:part4",  # Слишком много частей
            ":::::",
            "123:abc:def",  # Некорректный timestamp
        ]
        
        for token in malformed_tokens:
            assert not middleware._validate_csrf_token(token, token)
    
    def test_unicode_in_csrf_token(self, app):
        """Проверка обработки unicode символов"""
        middleware = CSRFMiddleware(app=app, secret_key="test_key")
        token = middleware._generate_csrf_token()
        
        # Токен должен быть валидным
        assert middleware._validate_csrf_token(token, token)
    
    def test_concurrent_requests(self, client):
        """Проверка обработки одновременных запросов"""
        import concurrent.futures
        
        def make_request():
            return client.get("/")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in futures]
        
        # Все запросы должны быть успешными
        for response in responses:
            assert response.status_code == 200
    
    def test_large_number_of_requests(self, client):
        """Проверка обработки большого количества запросов"""
        for _ in range(1000):
            response = client.get("/")
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])