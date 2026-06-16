"""
Tests for CacheManager module

Проверка системы кэширования:
- In-memory cache (L1)
- Redis cache (L2)
- Multi-level caching
- Rate limiting
- Session management
"""

import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.cache_manager import CacheManager, get_cache_manager


@pytest.fixture
def cache_manager():
    """Создание менеджера кэширования для тестов"""
    with patch('core.cache_manager.get_config', return_value={"cache.ttl": 60}):
        manager = CacheManager()
        manager.redis = None  # Отключаем Redis для тестов
        return manager


class TestCacheManagerBasics:
    """Базовые тесты для CacheManager"""
    
    def test_get_key(self, cache_manager):
        """Генерация ключа для кэша"""
        key = cache_manager._get_key("test", "key123")
        assert key == "padplus:test:key123"
    
    def test_serialize_dict(self, cache_manager):
        """Сериализация словаря"""
        data = {"key": "value", "number": 42}
        result = cache_manager._serialize(data)
        assert isinstance(result, str)
        assert "key" in result
    
    def test_serialize_string(self, cache_manager):
        """Сериализация строки"""
        result = cache_manager._serialize("test")
        assert result == '"test"'
    
    def test_deserialize_json(self, cache_manager):
        """Десериализация JSON"""
        json_str = '{"key": "value"}'
        result = cache_manager._deserialize(json_str)
        assert result == {"key": "value"}
    
    def test_deserialize_non_json(self, cache_manager):
        """Десериализация не-JSON"""
        result = cache_manager._deserialize("plain text")
        assert result == "plain text"


class TestMemoryCache:
    """Тесты для in-memory кэша (L1)"""
    
    def test_memory_set_and_get(self, cache_manager):
        """Сохранение и получение из memory cache"""
        cache_manager.set_memory("test", "key1", "value1")
        result = cache_manager.get_memory("test", "key1")
        assert result == "value1"
    
    def test_memory_get_miss(self, cache_manager):
        """Промах при получении из memory cache"""
        result = cache_manager.get_memory("test", "nonexistent")
        assert result is None
    
    def test_memory_delete(self, cache_manager):
        """Удаление из memory cache"""
        cache_manager.set_memory("test", "key2", "value2")
        cache_manager.delete_memory("test", "key2")
        result = cache_manager.get_memory("test", "key2")
        assert result is None
    
    def test_memory_stats(self, cache_manager):
        """Статистика memory cache"""
        cache_manager.set_memory("test", "k1", "v1")
        cache_manager.get_memory("test", "k1")  # hit
        cache_manager.get_memory("test", "k2")  # miss
        
        assert cache_manager.stats["memory_hits"] == 1
        assert cache_manager.stats["memory_misses"] == 1
        assert cache_manager.stats["sets"] >= 1


class TestMultiLevelCache:
    """Тесты для многоуровневого кэширования"""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_manager):
        """Сохранение и получение через multi-level cache"""
        await cache_manager.set("namespace", "key", {"data": "test"})
        result = await cache_manager.get("namespace", "key")
        assert result == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_get_miss(self, cache_manager):
        """Промах при получении"""
        result = await cache_manager.get("namespace", "nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete(self, cache_manager):
        """Удаление из multi-level cache"""
        await cache_manager.set("ns", "k", "v")
        await cache_manager.delete("ns", "k")
        result = await cache_manager.get("ns", "k")
        assert result is None


class TestLLMCache:
    """Тесты для кэширования LLM ответов"""
    
    @pytest.mark.asyncio
    async def test_cache_llm_response(self, cache_manager):
        """Кэширование ответа LLM"""
        await cache_manager.cache_llm_response(
            "What is AI?",
            "AI is artificial intelligence",
            "openai"
        )
        
        result = await cache_manager.get_cached_llm_response("What is AI?", "openai")
        assert result == "AI is artificial intelligence"
    
    @pytest.mark.asyncio
    async def test_cache_llm_response_miss(self, cache_manager):
        """Промах при получении кэшированного ответа LLM"""
        result = await cache_manager.get_cached_llm_response("Unknown", "openai")
        assert result is None


class TestRAGCache:
    """Тесты для кэширования RAG результатов"""
    
    @pytest.mark.asyncio
    async def test_cache_rag_result(self, cache_manager):
        """Кэширование результата RAG"""
        rag_result = [
            {"text": "Document 1", "score": 0.9},
            {"text": "Document 2", "score": 0.8}
        ]
        
        await cache_manager.cache_rag_result("test query", rag_result)
        result = await cache_manager.get_cached_rag_result("test query")
        
        assert result == rag_result
    
    @pytest.mark.asyncio
    async def test_cache_rag_result_miss(self, cache_manager):
        """Промах при получении кэшированного RAG результата"""
        result = await cache_manager.get_cached_rag_result("unknown query")
        assert result is None


class TestSessionManagement:
    """Тесты для управления сессиями"""
    
    @pytest.mark.asyncio
    async def test_store_and_get_session(self, cache_manager):
        """Сохранение и получение сессии"""
        session_data = {"user_id": "123", "username": "test"}
        
        await cache_manager.store_session("session123", session_data)
        result = await cache_manager.get_session("session123")
        
        assert result == session_data
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, cache_manager):
        """Получение несуществующей сессии"""
        result = await cache_manager.get_session("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_session(self, cache_manager):
        """Удаление сессии"""
        await cache_manager.store_session("session456", {"data": "test"})
        await cache_manager.delete_session("session456")
        result = await cache_manager.get_session("session456")
        assert result is None


class TestRateLimiting:
    """Тесты для rate limiting"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_not_exceeded(self, cache_manager):
        """Rate limit не превышен"""
        # С моком Redis
        cache_manager.redis = AsyncMock()
        cache_manager.redis.get = AsyncMock(return_value=None)
        cache_manager.set_redis = AsyncMock()
        
        is_limited, remaining = await cache_manager.is_rate_limited(
            "user1", limit=10, window=60
        )
        
        assert is_limited is False
        assert remaining == 9
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, cache_manager):
        """Rate limit превышен"""
        import time
        
        # С моком Redis - возвращаем текущие timestamps в пределах окна
        current_time = int(time.time())
        recent_requests = [current_time - i for i in range(10)]  # 10 последних запросов
        
        cache_manager.redis = AsyncMock()
        cache_manager.redis.get = AsyncMock(return_value=recent_requests)
        cache_manager.set_redis = AsyncMock()
        
        is_limited, remaining = await cache_manager.is_rate_limited(
            "user2", limit=10, window=60
        )
        
        assert is_limited is True
        assert remaining == 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, cache_manager):
        """Обработка ошибок rate limiting"""
        cache_manager.redis = AsyncMock()
        cache_manager.redis.get = AsyncMock(side_effect=Exception("Redis error"))
        
        is_limited, remaining = await cache_manager.is_rate_limited("user3")
        
        # При ошибке не блокируем
        assert is_limited is False


class TestStatistics:
    """Тесты для статистики кэширования"""
    
    def test_get_stats(self, cache_manager):
        """Получение статистики"""
        stats = cache_manager.get_stats()
        
        assert "memory" in stats
        assert "redis" in stats
        assert "total" in stats
        
        assert "hit_rate" in stats["memory"]
        assert "hits" in stats["memory"]
        assert "misses" in stats["memory"]
        assert "size" in stats["memory"]


class TestNamespaceOperations:
    """Тесты для операций с namespace"""
    
    @pytest.mark.asyncio
    async def test_clear_namespace(self, cache_manager):
        """Очистка namespace"""
        # Сохраняем несколько записей
        await cache_manager.set("test_ns", "key1", "value1")
        await cache_manager.set("test_ns", "key2", "value2")
        await cache_manager.set("other_ns", "key3", "value3")
        
        # Очищаем test_ns
        await cache_manager.clear_namespace("test_ns")
        
        # Проверяем что test_ns очищен
        result1 = await cache_manager.get("test_ns", "key1")
        result2 = await cache_manager.get("test_ns", "key2")
        result3 = await cache_manager.get("other_ns", "key3")
        
        assert result1 is None
        assert result2 is None
        assert result3 == "value3"  # other_ns не тронут


class TestCacheManagerSingleton:
    """Тесты для синглтона CacheManager"""
    
    def test_get_cache_manager_singleton(self):
        """Проверка что get_cache_manager возвращает один экземпляр"""
        # Сбрасываем кэш
        import core.cache_manager as cm
        cm._cache_manager = None
        
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        
        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])