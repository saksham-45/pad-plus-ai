"""
Unit тесты для LLM провайдеров
"""

import pytest
import importlib
from unittest.mock import Mock, patch, AsyncMock

# Проверяем наличие модуля llm
llm_available = importlib.util.find_spec("llm") is not None or importlib.util.find_spec("backend.llm") is not None

@pytest.mark.unit
@pytest.mark.llm
@pytest.mark.skipif(not llm_available, reason="Модуль llm отсутствует в проекте")
class TestLLMProvider:
    """Тесты LLM провайдеров"""
    
    def test_provider_manager_status(self):
        """Тест статуса менеджера провайдеров"""
        with patch('llm.provider_manager.get_provider_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_status = {
                "fallback": {"enabled": True},
                "providers": ["openai", "anthropic", "local"],
                "active_provider": "openai"
            }
            mock_manager.get_status.return_value = mock_status
            mock_get_manager.return_value = mock_manager
            
            # Вызов
            manager = mock_get_manager()
            status = manager.get_status()
            
            # Проверки
            assert status["fallback"]["enabled"] is True
            assert len(status["providers"]) > 0
            assert "active_provider" in status
            mock_manager.get_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_generate_response(self, mock_llm_response):
        """Тест генерации ответа LLM"""
        with patch('llm.provider_manager.get_provider_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.generate.return_value = mock_llm_response
            mock_get_manager.return_value = mock_manager
            
            # Вызов
            manager = mock_get_manager()
            response = await manager.generate("Тестовый prompt")
            
            # Проверки
            assert "response" in response
            assert "provider" in response
            assert response["provider"] == "test"
            mock_manager.generate.assert_called_once_with("Тестовый prompt")
    
    def test_fallback_mechanism(self):
        """Тест механизма отката"""
        with patch('llm.provider_manager.get_provider_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_fallback_status.return_value = {
                "enabled": True,
                "fallback_chain": ["openai", "anthropic", "local"],
                "current_provider": "anthropic"
            }
            mock_get_manager.return_value = mock_manager
            
            # Вызов
            manager = mock_get_manager()
            fallback_status = manager.get_fallback_status()
            
            # Проверки
            assert fallback_status["enabled"] is True
            assert len(fallback_status["fallback_chain"]) == 3
            assert fallback_status["current_provider"] == "anthropic"
            mock_manager.get_fallback_status.assert_called_once()
    
    def test_provider_health_check(self):
        """Тест проверки здоровья провайдеров"""
        with patch('llm.provider_manager.get_provider_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.health_check.return_value = {
                "openai": {"status": "healthy", "latency": 150},
                "anthropic": {"status": "healthy", "latency": 200},
                "local": {"status": "degraded", "latency": 500}
            }
            mock_get_manager.return_value = mock_manager
            
            # Вызов
            manager = mock_get_manager()
            health = manager.health_check()
            
            # Проверки
            assert "openai" in health
            assert health["openai"]["status"] == "healthy"
            assert health["local"]["status"] == "degraded"
            mock_manager.health_check.assert_called_once()
