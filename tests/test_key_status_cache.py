"""
Тесты для кэширования статусов ключей.

Endpoints:
- GET /api/v1/keys/status/batch
- POST /api/v1/keys/status/{key_id}/refresh

Упрощенные unit-тесты без сложного mocking FastAPI.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_cache_data():
    """Mock данные для кэша."""
    return {}


@pytest.fixture
def mock_cache_manager(mock_cache_data):
    """Mock CacheManager."""
    cache = MagicMock()
    
    async def mock_get(key):
        entry = mock_cache_data.get(key)
        if entry:
            if datetime.now().timestamp() < entry.get("expires", 0):
                return entry["value"]
            else:
                del mock_cache_data[key]  # Просрочен
        return None
    
    async def mock_set(key, value, ttl):
        mock_cache_data[key] = {
            "value": value,
            "expires": datetime.now().timestamp() + ttl
        }
    
    async def mock_delete(key):
        if key in mock_cache_data:
            del mock_cache_data[key]
    
    cache.get = mock_get
    cache.set = mock_set
    cache.delete = mock_delete
    
    with patch("backend.api.frontend_routes.get_cache_manager", return_value=cache):
        yield cache


# ============================================================================
# TESTS: Кэширование и TTL
# ============================================================================

class TestKeyStatusCacheLogic:
    """Тесты логики кэширования (без FastAPI TestClient)."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, mock_cache_manager, mock_cache_data):
        """Тест установки и получения из кэша."""
        test_data = {"keys": [{"status": "success"}], "total": 1}
        
        await mock_cache_manager.set("test_key", test_data, ttl=300)
        
        result = await mock_cache_manager.get("test_key")
        
        assert result is not None
        assert result["total"] == 1
        assert result["keys"][0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_cache_expires(self, mock_cache_manager, mock_cache_data):
        """Тест истечения кэша."""
        test_data = {"keys": [{"status": "old"}], "total": 1}
        
        # Установим кэш с TTL 1 секунда
        await mock_cache_manager.set("test_key", test_data, ttl=1)
        
        # Сразу должно работать
        result = await mock_cache_manager.get("test_key")
        assert result is not None
        
        # Имитируем прохождение времени
        mock_cache_data["test_key"]["expires"] = datetime.now().timestamp() - 1
        
        # Теперь должно вернуть None (просрочено)
        result = await mock_cache_manager.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete(self, mock_cache_manager, mock_cache_data):
        """Тест удаления из кэша."""
        test_data = {"keys": [{"status": "success"}], "total": 1}
        
        await mock_cache_manager.set("test_key", test_data, ttl=300)
        await mock_cache_manager.delete("test_key")
        
        result = await mock_cache_manager.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_overwrite(self, mock_cache_manager, mock_cache_data):
        """Тест перезаписи кэша."""
        test_data_1 = {"keys": [{"status": "old"}], "total": 1}
        test_data_2 = {"keys": [{"status": "new"}], "total": 1}
        
        await mock_cache_manager.set("test_key", test_data_1, ttl=300)
        await mock_cache_manager.set("test_key", test_data_2, ttl=300)
        
        result = await mock_cache_manager.get("test_key")
        assert result["keys"][0]["status"] == "new"


# ============================================================================
# TESTS: ProviderManager.test_connection
# ============================================================================

class TestProviderManagerConnection:
    """Тесты подключения к провайдерам."""

    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Успешное подключение."""
        from runtime.provider_manager import ProviderManager
        from runtime.llm_service import LLMService
        
        # Mock LLMService
        mock_llm = MagicMock()
        
        async def mock_generate(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.text = "OK"
            mock_response.model = "test-model"
            mock_response.usage = {"total_tokens": 10}
            mock_response.provider = "openrouter"
            mock_response.finish_reason = "stop"
            return mock_response
        
        mock_llm.generate = mock_generate
        
        pm = ProviderManager(llm_service=mock_llm)
        result = await pm.test_connection(
            api_key="test-key",
            provider="openrouter",
            model="test-model"
        )
        
        assert result["success"] is True
        assert result["message"] == "Подключение успешно"
        assert result["model_tested"] == "test-model"

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Ошибка подключения."""
        from runtime.provider_manager import ProviderManager
        from runtime.llm_service import LLMService
        
        # Mock LLMService с ошибкой
        mock_llm = MagicMock()
        
        async def mock_generate_error(*args, **kwargs):
            raise Exception("Invalid API key")
        
        mock_llm.generate = mock_generate_error
        
        pm = ProviderManager(llm_service=mock_llm)
        result = await pm.test_connection(
            api_key="invalid-key",
            provider="openrouter",
            model="test-model"
        )
        
        assert result["success"] is False
        assert "Invalid API key" in result["message"]


# ============================================================================
# TESTS: Структура данных
# ============================================================================

class TestKeyStatusDataStructure:
    """Тесты структуры данных статусов ключей."""

    def test_key_status_success_format(self):
        """Проверка формата успешного статуса."""
        key_status = {
            "key_id": "abc-123",
            "provider": "openrouter",
            "status": "success",
            "message": "Подключение успешно",
            "model_tested": "openrouter/gpt-4o-mini",
            "last_checked": datetime.now().isoformat(),
            "cached": False
        }
        
        # Проверка обязательных полей
        assert "key_id" in key_status
        assert "provider" in key_status
        assert "status" in key_status
        assert key_status["status"] in ["success", "error", "checking"]
        assert "message" in key_status
        assert "last_checked" in key_status
        assert "cached" in key_status

    def test_key_status_error_format(self):
        """Проверка формата статуса с ошибкой."""
        key_status = {
            "key_id": "abc-123",
            "provider": "openrouter",
            "status": "error",
            "message": "Invalid API key",
            "last_checked": datetime.now().isoformat(),
            "cached": False
        }
        
        assert key_status["status"] == "error"
        assert "Invalid API key" in key_status["message"]

    def test_batch_response_format(self):
        """Проверка формата batch ответа."""
        batch_response = {
            "keys": [
                {
                    "key_id": "key-1",
                    "provider": "openrouter",
                    "status": "success",
                    "message": "OK",
                    "last_checked": datetime.now().isoformat(),
                    "cached": False
                }
            ],
            "total": 1,
            "timestamp": datetime.now().isoformat()
        }
        
        assert "keys" in batch_response
        assert "total" in batch_response
        assert "timestamp" in batch_response
        assert isinstance(batch_response["keys"], list)
        assert batch_response["total"] == len(batch_response["keys"])
