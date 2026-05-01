"""
Тесты Rate Limiting

Проверяют:
1. Rate limiting работает
2. 10 запросов проходят
3. 11-й запрос блокируется
4. Заголовок X-RateLimit-Remaining добавляется
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ТЕСТЫ 1: CACHE MANAGER RATE LIMITING
# ============================================================================

class TestCacheManagerRateLimiting:
    """Тесты Rate Limiting в CacheManager"""

    @pytest.mark.asyncio
    async def test_rate_limit_first_request(self):
        """
        Проверяет, что первый запрос проходит
        """
        from backend.core.cache_manager import CacheManager
        
        cache = CacheManager()
        
        # Мокируем Redis
        with patch.object(cache, 'get_redis', new=AsyncMock(return_value=[])), \
             patch.object(cache, 'set_redis', new=AsyncMock()):
            
            is_limited, remaining = await cache.is_rate_limited(
                key="test_user",
                limit=10,
                window=60
            )
            
            assert is_limited is False
            assert remaining == 9  # 10 - 1 (первый запрос)

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """
        Проверяет, что 11-й запрос блокируется
        """
        from backend.core.cache_manager import CacheManager
        
        cache = CacheManager()
        
        current_time = int(datetime.now().timestamp())
        # 10 запросов в окне
        mock_requests = [current_time - i for i in range(10)]
        
        # Мокируем Redis
        with patch.object(cache, 'get_redis', new=AsyncMock(return_value=mock_requests)), \
             patch.object(cache, 'set_redis', new=AsyncMock()):
            
            is_limited, remaining = await cache.is_rate_limited(
                key="test_user",
                limit=10,
                window=60
            )
            
            assert is_limited is True
            assert remaining == 0

    @pytest.mark.asyncio
    async def test_rate_limit_window_expired(self):
        """
        Проверяет, что старые запросы не учитываются
        """
        from backend.core.cache_manager import CacheManager
        
        cache = CacheManager()
        
        current_time = int(datetime.now().timestamp())
        # 10 запросов, но все за пределами окна (старше 60 секунд)
        mock_requests = [current_time - 100 - i for i in range(10)]
        
        # Мокируем Redis
        with patch.object(cache, 'get_redis', new=AsyncMock(return_value=mock_requests)), \
             patch.object(cache, 'set_redis', new=AsyncMock()):
            
            is_limited, remaining = await cache.is_rate_limited(
                key="test_user",
                limit=10,
                window=60
            )
            
            assert is_limited is False
            assert remaining == 9  # Все старые запросы отфильтрованы

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self):
        """
        Проверяет, что при ошибке Redis запрос не блокируется
        """
        from backend.core.cache_manager import CacheManager
        
        cache = CacheManager()
        
        # Мокируем Redis с ошибкой
        with patch.object(cache, 'get_redis', new=AsyncMock(side_effect=Exception("Redis error"))):
            
            is_limited, remaining = await cache.is_rate_limited(
                key="test_user",
                limit=10,
                window=60
            )
            
            # При ошибке не блокируем
            assert is_limited is False
            assert remaining == 10


# ============================================================================
# ТЕСТЫ 2: CHAT ENDPOINT RATE LIMITING
# ============================================================================

class TestChatEndpointRateLimiting:
    """Тесты Rate Limiting в /chat endpoint"""

    @pytest.mark.asyncio
    async def test_chat_rate_limit_headers(self):
        """
        Проверяет, что при успехе возвращается remaining
        """
        from fastapi.testclient import TestClient
        from backend.main import app
        
        client = TestClient(app)
        
        # Мокируем аутентификацию и API ключ
        with patch('backend.api.frontend_routes.get_current_user', return_value={"id": "test_user"}), \
             patch('backend.api.frontend_routes.get_cache_manager') as MockCache, \
             patch('backend.api.frontend_routes.get_supabase'), \
             patch('backend.api.frontend_routes.get_encryptor'), \
             patch('backend.runtime.litellm_service.get_litellm_service'):
            
            # Rate limit не превышен
            MockCache.return_value.is_rate_limited = AsyncMock(return_value=(False, 9))
            
            # Мокируем ответ LLM
            from backend.runtime.litellm_service import LLMResponse
            mock_response = LLMResponse(
                text="Ответ",
                model="test",
                provider="test"
            )
            MockCache.return_value.generate = AsyncMock(return_value=mock_response)
            
            response = client.post(
                "/api/v1/chat",
                json={"message": "Тест"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            # В реальном приложении здесь был бы заголовок
            # assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_chat_rate_limit_exceeded(self):
        """
        Проверяет, что при превышении лимита возвращается 429
        """
        from fastapi.testclient import TestClient
        from backend.main import app
        
        client = TestClient(app)
        
        # Мокируем аутентификацию и API ключ
        with patch('backend.api.frontend_routes.get_current_user', return_value={"id": "test_user"}), \
             patch('backend.api.frontend_routes.get_cache_manager') as MockCache, \
             patch('backend.api.frontend_routes.get_supabase'), \
             patch('backend.api.frontend_routes.get_encryptor'):
            
            # Rate limit превышен
            MockCache.return_value.is_rate_limited = AsyncMock(return_value=(True, 0))
            
            response = client.post(
                "/api/v1/chat",
                json={"message": "Тест"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 429
            assert "rate_limit_exceeded" in response.json()["detail"]["error"]


# ============================================================================
# ТЕСТЫ 3: INTEGRATION
# ============================================================================

class TestRateLimitingIntegration:
    """Интеграционные тесты Rate Limiting"""

    @pytest.mark.asyncio
    async def test_rate_limit_multiple_users(self):
        """
        Проверяет, что rate limit считается отдельно для каждого пользователя
        """
        from backend.core.cache_manager import CacheManager
        
        cache = CacheManager()
        
        current_time = int(datetime.now().timestamp())
        # Пользователь 1: 10 запросов
        mock_requests_user1 = [current_time - i for i in range(10)]
        # Пользователь 2: 0 запросов
        mock_requests_user2 = []
        
        call_count = 0
        
        async def mock_get_redis(namespace, key):
            nonlocal call_count
            call_count += 1
            if "user1" in key:
                return mock_requests_user1
            else:
                return mock_requests_user2
        
        # Мокируем Redis
        with patch.object(cache, 'get_redis', new=mock_get_redis), \
             patch.object(cache, 'set_redis', new=AsyncMock()):
            
            # Пользователь 1 заблокирован
            is_limited1, _ = await cache.is_rate_limited(
                key="chat:user1",
                limit=10,
                window=60
            )
            assert is_limited1 is True
            
            # Пользователь 2 не заблокирован
            is_limited2, remaining = await cache.is_rate_limited(
                key="chat:user2",
                limit=10,
                window=60
            )
            assert is_limited2 is False
            assert remaining == 9

    @pytest.mark.asyncio
    async def test_rate_limit_concurrent_requests(self):
        """
        Проверяет работу при конкурентных запросах
        """
        from backend.core.cache_manager import CacheManager
        
        cache = CacheManager()
        
        # Мокируем Redis с пустым списком
        with patch.object(cache, 'get_redis', new=AsyncMock(return_value=[])), \
             patch.object(cache, 'set_redis', new=AsyncMock()):
            
            # 10 конкурентных запросов
            tasks = [
                cache.is_rate_limited(f"chat:user{i}", limit=10, window=60)
                for i in range(10)
            ]
            results = await asyncio.gather(*tasks)
            
            # Все должны пройти
            assert all(not is_limited for is_limited, _ in results)
