"""
Fixtures for optimization tests
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


@pytest.fixture
def event_loop():
    """Создаёт event loop для тестов"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_cache_manager():
    """Мок для CacheManager"""
    with patch("backend.core.cache_manager.get_cache_manager") as mock:
        cache = AsyncMock()
        cache.connect = AsyncMock()
        cache.disconnect = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        cache.exists = AsyncMock(return_value=False)
        cache.is_rate_limited = AsyncMock(return_value=False)
        mock.return_value = cache
        yield cache


@pytest.fixture
async def mock_litellm_service():
    """Мок для LiteLLMService"""
    from backend.runtime.litellm_service import LLMResponse
    
    with patch("backend.runtime.litellm_service.get_litellm_service") as mock:
        service = AsyncMock()
        service.generate = AsyncMock(return_value=LLMResponse(
            text="Тестовый ответ",
            model="test-model",
            provider="test-provider",
            confidence=0.8
        ))
        service.generate_stream = AsyncMock()
        service.test_connection = AsyncMock(return_value={"success": True})
        mock.return_value = service
        yield service


@pytest.fixture
async def mock_supabase():
    """Мок для Supabase client"""
    with patch("backend.core.supabase_client.get_supabase") as mock:
        supabase = AsyncMock()
        supabase.table = MagicMock()
        mock.return_value = supabase
        yield supabase


@pytest.fixture
def mock_env():
    """Мок для переменных окружения"""
    import os
    original_env = os.environ.copy()
    
    os.environ["TEST_MODE"] = "true"
    os.environ["LLM_TIMEOUT"] = "5"  # Короткий timeout для тестов
    os.environ["ENCRYPTION_KEY"] = "test_key_for_testing_only_32chars!"
    os.environ["ENCRYPTION_SALT"] = "dGVzdF9zYWx0X2Zvcl90ZXN0aW5nX3B1cnBvc2VzX29ubHk="
    
    yield os.environ
    
    # Восстанавливаем оригинальные переменные
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
async def temp_data_dir(tmp_path):
    """Временная директория для данных"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    yield data_dir


@pytest.fixture
def mock_llm_response():
    """Фикстура для создания мок LLMResponse"""
    from backend.runtime.litellm_service import LLMResponse
    
    def create_response(text="Ответ", confidence=0.8, provider="test"):
        return LLMResponse(
            text=text,
            model=f"{provider}-model",
            provider=provider,
            confidence=confidence
        )
    
    return create_response


@pytest.fixture
def circuit_breaker_config():
    """Конфигурация для Circuit Breaker в тестах"""
    return {
        "failure_threshold": 3,      # Меньше порог для тестов
        "recovery_timeout": 1,       # 1 секунда вместо 60
        "half_open_max_calls": 1
    }
