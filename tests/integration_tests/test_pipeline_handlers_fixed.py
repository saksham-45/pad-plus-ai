"""
Исправленные тесты для Pipeline Handlers

Мокируем в исходных модулях, а не в pipeline_handlers.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


class TestSafetyHandlerFixed:
    """Исправленные тесты SafetyHandler"""

    @pytest.mark.asyncio
    async def test_safety_handler_blocks(self):
        from backend.core.pipeline_handlers import SafetyHandler
        
        handler = SafetyHandler()
        
        with patch('backend.core.safety_layer.get_safety_layer') as MockSafety:
            mock_safety = MagicMock()
            mock_safety.check_request.return_value = MagicMock(
                action=MagicMock(value="block")
            )
            MockSafety.return_value = mock_safety
            
            result = await handler.process({"user_message": "Тест"})
            
            assert result.success is False

    @pytest.mark.asyncio
    async def test_safety_handler_allows(self):
        from backend.core.pipeline_handlers import SafetyHandler
        
        handler = SafetyHandler()
        
        with patch('backend.core.safety_layer.get_safety_layer') as MockSafety:
            mock_safety = MagicMock()
            mock_safety.check_request.return_value = MagicMock(
                action=MagicMock(value="allow")
            )
            MockSafety.return_value = mock_safety
            
            result = await handler.process({"user_message": "Тест"})
            
            assert result.success is True


class TestIntentHandlerFixed:
    """Исправленные тесты IntentHandler"""

    @pytest.mark.asyncio
    async def test_intent_handler_classifies(self):
        from backend.core.pipeline_handlers import IntentHandler
        
        handler = IntentHandler()
        
        with patch('backend.core.intent_router.get_router') as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = MagicMock(
                intent=MagicMock(value="knowledge_query"),
                confidence=0.85
            )
            MockRouter.return_value = mock_router
            
            result = await handler.process({"user_message": "Тест"})
            
            assert result.success is True
            assert result.data["intent"] == "knowledge_query"


class TestRAGHandlerFixed:
    """Исправленные тесты RAGHandler"""

    @pytest.mark.asyncio
    async def test_rag_handler_finds(self):
        from backend.core.pipeline_handlers import RAGHandler
        
        handler = RAGHandler()
        
        with patch('backend.memory.rag.get_rag') as MockRag:
            mock_rag = MagicMock()
            mock_rag.get_context.return_value = "Контекст"
            MockRag.return_value = mock_rag
            
            result = await handler.process({"user_message": "Тест"})
            
            assert result.success is True
            assert result.metadata["rag_used"] is True


class TestFactsHandlerFixed:
    """Исправленные тесты FactsHandler"""

    @pytest.mark.asyncio
    async def test_facts_handler_finds(self):
        from backend.core.pipeline_handlers import FactsHandler
        
        handler = FactsHandler()
        
        with patch('backend.memory.fact_memory_chroma.get_fact_memory_chroma') as MockFacts:
            mock_fact = MagicMock()
            mock_fact.search.return_value = [MagicMock()]
            MockFacts.return_value = mock_fact
            
            result = await handler.process({"user_message": "Тест"})
            
            assert result.success is True
            assert result.metadata["facts_used"] > 0


class TestEpisodicHandlerFixed:
    """Исправленные тесты EpisodicHandler"""

    @pytest.mark.asyncio
    async def test_episodic_handler_finds(self):
        from backend.core.pipeline_handlers import EpisodicHandler
        
        handler = EpisodicHandler()
        
        with patch('backend.memory.episodic.get_episodic_memory') as MockEpisodic:
            mock_episodic = MagicMock()
            mock_episodic.search_episodes.return_value = [MagicMock()]
            MockEpisodic.return_value = mock_episodic
            
            result = await handler.process({"user_message": "Тест"})
            
            assert result.success is True
            assert result.metadata["episodic_used"] is True


class TestGenerateHandlerFixed:
    """Исправленные тесты GenerateHandler"""

    @pytest.mark.asyncio
    async def test_generate_handler_no_key(self):
        from backend.core.pipeline_handlers import GenerateHandler
        
        handler = GenerateHandler()
        
        result = await handler.process({
            "user_message": "Тест",
            "api_key": None
        })
        
        assert result.success is False
        assert "NO_API_KEY" in result.errors

    @pytest.mark.asyncio
    async def test_generate_handler_with_key(self):
        from backend.core.pipeline_handlers import GenerateHandler
        from backend.runtime.litellm_service import LLMResponse
        
        handler = GenerateHandler()
        
        with patch('backend.core.pipeline_handlers.LiteLLMService') as MockLiteLLM:
            mock_litellm = AsyncMock()
            mock_litellm.generate = AsyncMock(return_value=LLMResponse(
                text="Ответ",
                model="test",
                provider="test",
                confidence=0.8
            ))
            MockLiteLLM.return_value = mock_litellm
            
            result = await handler.process({
                "user_message": "Тест",
                "api_key": "test-key"
            })
            
            assert result.success is True
            assert result.data["response"] == "Ответ"
