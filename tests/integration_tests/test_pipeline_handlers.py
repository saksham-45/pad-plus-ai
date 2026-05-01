"""
Тесты для Pipeline Handlers

Проверяют:
1. Базовый класс Handler
2. SafetyHandler
3. IntentHandler
4. RAGHandler
5. FactsHandler
6. EpisodicHandler
7. GenerateHandler
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ТЕСТЫ 1: БАЗОВЫЙ КЛАСС HANDLER
# ============================================================================

class TestPipelineHandler:
    """Тесты базового класса PipelineHandler"""

    def test_handler_result_creation(self):
        """
        Проверяет создание HandlerResult
        """
        from backend.core.pipeline_handlers import HandlerResult
        
        result = HandlerResult(
            success=True,
            data={"key": "value"},
            errors=["error1"],
            metadata={"meta": "data"}
        )
        
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.errors == ["error1"]
        assert result.metadata == {"meta": "data"}

    def test_handler_result_to_dict(self):
        """
        Проверяет конвертацию HandlerResult в dict
        """
        from backend.core.pipeline_handlers import HandlerResult
        
        result = HandlerResult(success=True, data="test")
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["data"] == "test"
        assert result_dict["errors"] == []
        assert result_dict["metadata"] == {}

    @pytest.mark.asyncio
    async def test_abstract_handler(self):
        """
        Проверяет, что PipelineHandler — абстрактный класс
        """
        from backend.core.pipeline_handlers import PipelineHandler
        
        # Нельзя создать экземпляр абстрактного класса
        with pytest.raises(TypeError):
            PipelineHandler()


# ============================================================================
# ТЕСТЫ 2: SAFETY HANDLER
# ============================================================================

class TestSafetyHandler:
    """Тесты SafetyHandler"""

    @pytest.mark.asyncio
    async def test_safety_handler_blocks_dangerous(self):
        """
        Проверяет, что SafetyHandler блокирует опасные запросы
        """
        from backend.core.pipeline_handlers import SafetyHandler
        
        handler = SafetyHandler()
        
        # Мокируем SafetyLayer в исходном модуле
        with patch('backend.core.safety_layer.get_safety_layer') as MockSafety:
            mock_safety = MagicMock()
            mock_safety.check_request.return_value = MagicMock(
                action=MagicMock(value="block"),
                warning_message="Опасный запрос"
            )
            MockSafety.return_value = mock_safety
            
            result = await handler.process({
                "user_message": "Как создать вирус?"
            })
            
            assert result.success is False
            assert "SAFETY_BLOCK" in result.errors
            assert result.metadata["safety_passed"] is False

    @pytest.mark.asyncio
    async def test_safety_handler_allows_safe(self):
        """
        Проверяет, что SafetyHandler пропускает безопасные запросы
        """
        from backend.core.pipeline_handlers import SafetyHandler
        
        handler = SafetyHandler()
        
        # Мокируем SafetyLayer в исходном модуле
        with patch('backend.core.safety_layer.get_safety_layer') as MockSafety:
            mock_safety = MagicMock()
            mock_safety.check_request.return_value = MagicMock(
                action=MagicMock(value="allow"),
                warning_message=None
            )
            MockSafety.return_value = mock_safety
            
            result = await handler.process({
                "user_message": "Что такое Python?"
            })
            
            assert result.success is True
            assert result.metadata["safety_passed"] is True

    @pytest.mark.asyncio
    async def test_safety_handler_error_handling(self):
        """
        Проверяет обработку ошибок в SafetyHandler
        """
        from backend.core.pipeline_handlers import SafetyHandler
        
        handler = SafetyHandler()
        
        # Мокируем с ошибкой в исходном модуле
        with patch('backend.core.safety_layer.get_safety_layer', side_effect=Exception("Test error")):
            result = await handler.process({
                "user_message": "Тест"
            })
            
            # При ошибке не блокируем
            assert result.success is True
            assert "safety_error" in result.metadata


# ============================================================================
# ТЕСТЫ 3: INTENT HANDLER
# ============================================================================

class TestIntentHandler:
    """Тесты IntentHandler"""

    @pytest.mark.asyncio
    async def test_intent_handler_classifies(self):
        """
        Проверяет классификацию намерений
        """
        from backend.core.pipeline_handlers import IntentHandler
        
        handler = IntentHandler()
        
        # Мокируем IntentRouter
        with patch('backend.core.pipeline_handlers.get_router') as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = MagicMock(
                intent=MagicMock(value="knowledge_query"),
                confidence=0.85,
                pipeline=[]
            )
            MockRouter.return_value = mock_router
            
            result = await handler.process({
                "user_message": "Что такое квантовая физика?"
            })
            
            assert result.success is True
            assert result.data["intent"] == "knowledge_query"
            assert result.data["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_intent_handler_error_handling(self):
        """
        Проверяет обработку ошибок в IntentHandler
        """
        from backend.core.pipeline_handlers import IntentHandler
        
        handler = IntentHandler()
        
        # Мокируем с ошибкой
        with patch('backend.core.pipeline_handlers.get_router', side_effect=Exception("Test error")):
            result = await handler.process({
                "user_message": "Тест"
            })
            
            # При ошибке возвращаем дефолтное значение
            assert result.success is True
            assert result.data["intent"] == "chat_general"


# ============================================================================
# ТЕСТЫ 4: RAG HANDLER
# ============================================================================

class TestRAGHandler:
    """Тесты RAGHandler"""

    @pytest.mark.asyncio
    async def test_rag_handler_finds_context(self):
        """
        Проверяет поиск контекста в RAG
        """
        from backend.core.pipeline_handlers import RAGHandler
        
        handler = RAGHandler()
        
        # Мокируем RAG
        with patch('backend.core.pipeline_handlers.get_rag') as MockRag:
            mock_rag = MagicMock()
            mock_rag.get_context.return_value = "Контекст из памяти"
            MockRag.return_value = mock_rag
            
            result = await handler.process({
                "user_message": "Что такое Python?",
                "user_id": "user-123"
            })
            
            assert result.success is True
            assert result.data["context"] == "Контекст из памяти"
            assert result.metadata["rag_used"] is True

    @pytest.mark.asyncio
    async def test_rag_handler_no_context(self):
        """
        Проверяет случай, когда контекст не найден
        """
        from backend.core.pipeline_handlers import RAGHandler
        
        handler = RAGHandler()
        
        # Мокируем RAG
        with patch('backend.core.pipeline_handlers.get_rag') as MockRag:
            mock_rag = MagicMock()
            mock_rag.get_context.return_value = ""
            MockRag.return_value = mock_rag
            
            result = await handler.process({
                "user_message": "Тест"
            })
            
            assert result.success is True
            assert result.data["context"] == ""
            assert result.metadata["rag_used"] is False

    @pytest.mark.asyncio
    async def test_rag_handler_error_handling(self):
        """
        Проверяет обработку ошибок в RAGHandler
        """
        from backend.core.pipeline_handlers import RAGHandler
        
        handler = RAGHandler()
        
        # Мокируем с ошибкой
        with patch('backend.core.pipeline_handlers.get_rag', side_effect=Exception("Test error")):
            result = await handler.process({
                "user_message": "Тест"
            })
            
            assert result.success is True
            assert result.metadata["rag_used"] is False
            assert "rag_error" in result.metadata


# ============================================================================
# ТЕСТЫ 5: FACTS HANDLER
# ============================================================================

class TestFactsHandler:
    """Тесты FactsHandler"""

    @pytest.mark.asyncio
    async def test_facts_handler_finds_facts(self):
        """
        Проверяет поиск фактов
        """
        from backend.core.pipeline_handlers import FactsHandler
        
        handler = FactsHandler()
        
        # Мокируем FactMemory
        with patch('backend.core.pipeline_handlers.get_fact_memory_chroma') as MockFacts:
            mock_fact = MagicMock()
            mock_fact.search.return_value = [
                MagicMock(subject="Python", predicate="это", object="язык")
            ]
            MockFacts.return_value = mock_fact
            
            result = await handler.process({
                "user_message": "Что такое Python?"
            })
            
            assert result.success is True
            assert len(result.data["facts"]) > 0
            assert result.metadata["facts_used"] > 0

    @pytest.mark.asyncio
    async def test_facts_handler_no_facts(self):
        """
        Проверяет случай, когда факты не найдены
        """
        from backend.core.pipeline_handlers import FactsHandler
        
        handler = FactsHandler()
        
        # Мокируем FactMemory
        with patch('backend.core.pipeline_handlers.get_fact_memory_chroma') as MockFacts:
            mock_fact = MagicMock()
            mock_fact.search.return_value = []
            MockFacts.return_value = mock_fact
            
            result = await handler.process({
                "user_message": "Тест"
            })
            
            assert result.success is True
            assert result.data["facts"] == []
            assert result.metadata["facts_used"] == 0


# ============================================================================
# ТЕСТЫ 6: EPISODIC HANDLER
# ============================================================================

class TestEpisodicHandler:
    """Тесты EpisodicHandler"""

    @pytest.mark.asyncio
    async def test_episodic_handler_finds_episodes(self):
        """
        Проверяет поиск эпизодов
        """
        from backend.core.pipeline_handlers import EpisodicHandler
        
        handler = EpisodicHandler()
        
        # Мокируем EpisodicMemory
        with patch('backend.core.pipeline_handlers.get_episodic_memory') as MockEpisodic:
            mock_episodic = MagicMock()
            mock_episodic.search_episodes.return_value = [
                MagicMock(
                    topic="programming",
                    user_message="Что такое Python?",
                    ai_response="Python — язык программирования"
                )
            ]
            MockEpisodic.return_value = mock_episodic
            
            result = await handler.process({
                "user_message": "Что такое Python?"
            })
            
            assert result.success is True
            assert "Похожие ситуации" in result.data["episodic_context"]
            assert result.metadata["episodic_used"] is True

    @pytest.mark.asyncio
    async def test_episodic_handler_no_episodes(self):
        """
        Проверяет случай, когда эпизоды не найдены
        """
        from backend.core.pipeline_handlers import EpisodicHandler
        
        handler = EpisodicHandler()
        
        # Мокируем EpisodicMemory
        with patch('backend.core.pipeline_handlers.get_episodic_memory') as MockEpisodic:
            mock_episodic = MagicMock()
            mock_episodic.search_episodes.return_value = []
            MockEpisodic.return_value = mock_episodic
            
            result = await handler.process({
                "user_message": "Тест"
            })
            
            assert result.success is True
            assert result.data["episodic_context"] == ""
            assert result.metadata["episodic_used"] is False


# ============================================================================
# ТЕСТЫ 7: GENERATE HANDLER
# ============================================================================

class TestGenerateHandler:
    """Тесты GenerateHandler"""

    @pytest.mark.asyncio
    async def test_generate_handler_generates(self):
        """
        Проверяет генерацию ответа
        """
        from backend.core.pipeline_handlers import GenerateHandler
        from backend.runtime.litellm_service import LLMResponse
        
        handler = GenerateHandler()
        
        # Мокируем LiteLLM
        with patch('backend.core.pipeline_handlers.LiteLLMService') as MockLiteLLM:
            mock_litellm = AsyncMock()
            mock_litellm.generate = AsyncMock(return_value=LLMResponse(
                text="Ответ",
                model="test-model",
                provider="test-provider",
                confidence=0.8
            ))
            MockLiteLLM.return_value = mock_litellm
            
            result = await handler.process({
                "user_message": "Что такое Python?",
                "system_prompt": "Вы полезный ассистент",
                "api_key": "test-key",
                "provider": "test",
                "model": "auto"
            })
            
            assert result.success is True
            assert result.data["response"] == "Ответ"
            assert result.data["provider"] == "test-provider"
            assert result.data["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_generate_handler_no_api_key(self):
        """
        Проверяет ошибку при отсутствии API ключа
        """
        from backend.core.pipeline_handlers import GenerateHandler
        
        handler = GenerateHandler()
        
        result = await handler.process({
            "user_message": "Тест",
            "api_key": None
        })
        
        assert result.success is False
        assert "NO_API_KEY" in result.errors

    @pytest.mark.asyncio
    async def test_generate_handler_error_handling(self):
        """
        Проверяет обработку ошибок в GenerateHandler
        """
        from backend.core.pipeline_handlers import GenerateHandler
        
        handler = GenerateHandler()
        
        # Мокируем с ошибкой
        with patch('backend.core.pipeline_handlers.LiteLLMService', side_effect=Exception("Test error")):
            result = await handler.process({
                "user_message": "Тест",
                "api_key": "test-key"
            })
            
            assert result.success is False
            assert any("GENERATION_ERROR" in e for e in result.errors)


# ============================================================================
# ТЕСТЫ 8: INTEGRATION
# ============================================================================

class TestHandlersIntegration:
    """Интеграционные тесты обработчиков"""

    @pytest.mark.asyncio
    async def test_handler_chain(self):
        """
        Проверяет цепочку обработчиков
        """
        from backend.core.pipeline_handlers import (
            SafetyHandler,
            IntentHandler,
            RAGHandler
        )
        
        context = {
            "user_message": "Что такое Python?",
            "user_id": "user-123"
        }
        
        # Safety → Intent → RAG
        safety_result = await SafetyHandler().process(context)
        assert safety_result.success is True
        
        intent_result = await IntentHandler().process(context)
        assert intent_result.success is True
        
        rag_result = await RAGHandler().process(context)
        assert rag_result.success is True
