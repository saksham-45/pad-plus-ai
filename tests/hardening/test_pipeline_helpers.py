"""
Tests for Pipeline Helpers module

Проверка вспомогательных функций для pipeline:
- extract_context_data
- format_rag_context
- process_safety_check
- detect_intent
- gather_memory_context
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.pipeline_helpers import (
    extract_context_data,
    format_rag_context,
    process_safety_check,
    detect_intent,
    gather_memory_context,
)


class TestExtractContextData:
    """Тесты для extract_context_data"""
    
    def test_extract_with_valid_context(self):
        """Извлечение данных из валидного контекста"""
        context = {
            "user_id": "user123",
            "session_id": "session456"
        }
        user_id, session_id = extract_context_data(context)
        assert user_id == "user123"
        assert session_id == "session456"
    
    def test_extract_with_none_context(self):
        """Извлечение данных из None контекста"""
        user_id, session_id = extract_context_data(None)
        assert user_id is None
        assert session_id is None
    
    def test_extract_with_empty_context(self):
        """Извлечение данных из пустого контекста"""
        user_id, session_id = extract_context_data({})
        assert user_id is None
        assert session_id is None
    
    def test_extract_partial_context(self):
        """Извлечение данных из частичного контекста"""
        context = {"user_id": "user123"}
        user_id, session_id = extract_context_data(context)
        assert user_id == "user123"
        assert session_id is None


class TestFormatRagContext:
    """Тесты для format_rag_context"""
    
    def test_format_basic_context(self):
        """Форматирование базового контекста"""
        result = format_rag_context(
            rag_context="RAG data",
            facts_context=[],
            episodic_context="",
            procedure_context="",
            persona_context="Persona info",
            emotion_style={"tone": "friendly"},
            emotion_state={"уверенность": 0.8},
            strategy="simple",
            roots_context="Roots data",
            persona_prompt="Be helpful"
        )
        
        assert "Ты — PAD+ AI" in result
        assert "Roots data" in result
        assert "Be helpful" in result
        assert "Persona info" in result
        assert "friendly" in result
        assert "0.80" in result
        assert "simple" in result
    
    def test_format_context_with_empty_values(self):
        """Форматирование контекста с пустыми значениями"""
        result = format_rag_context(
            rag_context="",
            facts_context=[],
            episodic_context="",
            procedure_context="",
            persona_context="",
            emotion_style={},
            emotion_state={},
            strategy="simple",
            roots_context="",
            persona_prompt=""
        )
        
        assert "neutral" in result
        assert "0.50" in result


class TestProcessSafetyCheck:
    """Тесты для process_safety_check"""
    
    def test_safety_check_pass(self):
        """Проверка безопасности проходит"""
        safety_layer = MagicMock()
        safety_layer.check_request.return_value = MagicMock(
            action=MagicMock(value="pass"),
            warning_message=None
        )
        
        is_safe, warning, message = process_safety_check("Hello", safety_layer)
        assert is_safe is True
        assert warning is None
        assert message == "Hello"
    
    def test_safety_check_block(self):
        """Проверка безопасности блокирует"""
        safety_layer = MagicMock()
        safety_layer.check_request.return_value = MagicMock(
            action=MagicMock(value="block"),
            warning_message="Blocked!"
        )
        
        is_safe, warning, message = process_safety_check("Bad request", safety_layer)
        assert is_safe is False
        assert warning == "Blocked!"
        assert message == "Bad request"
    
    def test_safety_check_sanitize(self):
        """Проверка безопасности с санитизацией"""
        safety_layer = MagicMock()
        safety_layer.check_request.return_value = MagicMock(
            action=MagicMock(value="sanitize"),
            warning_message=None
        )
        safety_layer.sanitize_input.return_value = "Sanitized"
        
        is_safe, warning, message = process_safety_check("Unsafe", safety_layer)
        assert is_safe is True
        assert warning is None
        assert message == "Sanitized"
    
    def test_safety_check_warn(self):
        """Проверка безопасности с предупреждением"""
        safety_layer = MagicMock()
        safety_layer.check_request.return_value = MagicMock(
            action=MagicMock(value="warn"),
            warning_message="Be careful"
        )
        
        is_safe, warning, message = process_safety_check("Risky", safety_layer)
        assert is_safe is True
        assert warning == "Be careful"
    
    def test_safety_check_error(self):
        """Обработка ошибки проверки безопасности"""
        safety_layer = MagicMock()
        safety_layer.check_request.side_effect = Exception("Error")
        
        is_safe, warning, message = process_safety_check("Test", safety_layer)
        assert is_safe is True
        assert warning is None
        assert message == "Test"


class TestDetectIntent:
    """Тесты для detect_intent"""
    
    def test_detect_intent_success(self):
        """Определение намерения успешно"""
        # Создаем моки с правильным атрибутом name
        stage1 = MagicMock()
        type(stage1).name = property(lambda self: "safety")
        stage2 = MagicMock()
        type(stage2).name = property(lambda self: "retrieve")
        
        intent_router = MagicMock()
        intent_router.route.return_value = MagicMock(
            intent=MagicMock(value="question"),
            pipeline=[stage1, stage2]
        )
        
        intent, pipeline = detect_intent("What is AI?", intent_router)
        assert intent == "question"
        assert pipeline == ["safety", "retrieve"]
    
    def test_detect_intent_error(self):
        """Обработка ошибки определения намерения"""
        intent_router = MagicMock()
        intent_router.route.side_effect = Exception("Error")
        
        intent, pipeline = detect_intent("Test", intent_router)
        assert intent == "chat_general"
        assert pipeline is None


class TestGatherMemoryContext:
    """Тесты для gather_memory_context"""
    
    def test_gather_all_sources(self):
        """Сбор контекста из всех источников"""
        user_message = "Test query"
        user_id = "user123"
        
        # Создаем моки для всех источников памяти
        rag = MagicMock()
        rag.get_context.return_value = "RAG context"
        
        facts_memory = MagicMock()
        facts_memory.search.return_value = ["fact1", "fact2"]
        
        episodic_memory = MagicMock()
        episodic_memory.search_episodes.return_value = [
            MagicMock(topic="topic1", user_message="msg1", ai_response="resp1")
        ]
        
        semantic_memory = MagicMock()
        semantic_memory.find_applicable_procedure.return_value = None
        
        vector_memory = MagicMock()
        vector_memory.search.return_value = []
        
        smartcache = MagicMock()
        smartcache.is_negative.return_value = False
        smartcache.search.return_value = []
        
        result = gather_memory_context(
            user_message, user_id,
            rag, facts_memory, episodic_memory,
            semantic_memory, vector_memory, smartcache
        )
        
        assert result["rag_context"] == "RAG context"
        assert result["sources"]["rag"]["count"] == 1
        assert result["sources"]["facts"]["count"] == 2
        assert result["sources"]["episodic"]["count"] == 1
        assert result["facts_context"] == ["fact1", "fact2"]
    
    def test_gather_empty_sources(self):
        """Сбор контекста с пустыми источниками"""
        user_message = "Test query"
        user_id = None
        
        rag = MagicMock()
        rag.get_context.return_value = ""
        
        facts_memory = MagicMock()
        facts_memory.search.return_value = []
        
        episodic_memory = MagicMock()
        episodic_memory.search_episodes.return_value = []
        
        semantic_memory = MagicMock()
        semantic_memory.find_applicable_procedure.return_value = None
        
        vector_memory = MagicMock()
        vector_memory.search.return_value = []
        
        smartcache = MagicMock()
        smartcache.is_negative.return_value = False
        smartcache.search.return_value = []
        
        result = gather_memory_context(
            user_message, user_id,
            rag, facts_memory, episodic_memory,
            semantic_memory, vector_memory, smartcache
        )
        
        assert result["rag_context"] == ""
        assert result["sources"]["rag"]["count"] == 0
        assert result["sources"]["facts"]["count"] == 0
    
    def test_gather_with_errors(self):
        """Сбор контекста с ошибками в источниках"""
        user_message = "Test query"
        user_id = None
        
        rag = MagicMock()
        rag.get_context.side_effect = Exception("RAG error")
        
        facts_memory = MagicMock()
        facts_memory.search.side_effect = Exception("Facts error")
        
        episodic_memory = MagicMock()
        episodic_memory.search_episodes.side_effect = Exception("Episodic error")
        
        semantic_memory = MagicMock()
        semantic_memory.find_applicable_procedure.side_effect = Exception("Semantic error")
        
        vector_memory = MagicMock()
        vector_memory.search.side_effect = Exception("Vector error")
        
        smartcache = MagicMock()
        smartcache.is_negative.side_effect = Exception("SmartCache error")
        
        # Не должно выбрасывать исключение
        result = gather_memory_context(
            user_message, user_id,
            rag, facts_memory, episodic_memory,
            semantic_memory, vector_memory, smartcache
        )
        
        assert isinstance(result, dict)
        assert "rag_context" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])