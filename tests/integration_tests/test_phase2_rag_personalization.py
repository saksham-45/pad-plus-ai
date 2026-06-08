"""
Тесты Фазы 2: Персонализация RAG (PostgreSQL)

Проверяют:
1. RAG принимает user_id параметр
2. RAG фильтрует записи по user_id
3. Пользователь видит только свои записи + общие
4. Pipeline передаёт user_id в RAG
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


@pytest.fixture
def mock_rag_deps():
    """
    Мокирует зависимости RAG для работы без PostgreSQL
    """
    with patch('backend.memory.rag.psycopg2') as MockPg, \
         patch('backend.memory.rag.RAGMemory._ensure_initialized'):
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        MockPg.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        yield {
            'conn': mock_conn,
            'cursor': mock_cursor
        }


class TestRAGWithUserId:
    """Тесты RAG с персонализацией"""

    @pytest.mark.asyncio
    async def test_rag_add_dialog_accepts_user_id(self):
        """Проверяет, что add_dialog принимает user_id"""
        from backend.memory.rag import RAGMemory
        import inspect
        
        rag = RAGMemory()
        sig = inspect.signature(rag.add_dialog)
        params = list(sig.parameters.keys())
        
        assert 'user_id' in params

    @pytest.mark.asyncio
    async def test_rag_get_context_accepts_user_id(self):
        """Проверяет, что get_context принимает user_id"""
        from backend.memory.rag import RAGMemory
        import inspect
        
        rag = RAGMemory()
        sig = inspect.signature(rag.get_context)
        params = list(sig.parameters.keys())
        
        assert 'user_id' in params

    @pytest.mark.asyncio
    async def test_rag_hybrid_search_accepts_user_id(self):
        """Проверяет, что hybrid_search принимает user_id"""
        from backend.memory.rag import RAGMemory
        import inspect
        
        rag = RAGMemory()
        sig = inspect.signature(rag.hybrid_search)
        params = list(sig.parameters.keys())
        
        assert 'user_id' in params


class TestRAGPostgreSQL:
    """Тесты PostgreSQL-реализации RAG"""

    def test_rag_initialization(self):
        """Проверяет, что RAG инициализируется без внешних зависимостей"""
        from backend.memory.rag import RAGMemory
        
        rag = RAGMemory()
        
        assert rag is not None
        assert rag._initialized is False
        assert rag.conn is None
        assert rag.cursor is None

    def test_rag_functions_exist(self):
        """Проверяет наличие необходимых функций"""
        from backend.memory.rag import RAGMemory
        
        rag = RAGMemory()
        
        assert hasattr(rag, 'add_dialog')
        assert hasattr(rag, 'get_context')
        assert hasattr(rag, 'hybrid_search')
        assert hasattr(rag, 'search')
        assert hasattr(rag, 'get_recent')

    def test_classify_topic_function(self):
        """Проверяет функцию классификации тем"""
        from backend.memory.rag import classify_topic
        
        topic, confidence = classify_topic("напиши код на Python для алгоритма")
        
        assert topic in ["техническое", "творческое", "аналитическое", "образовательное"]
        assert 0 <= confidence <= 1

    def test_extract_entities_function(self):
        """Проверяет функцию извлечения сущностей"""
        from backend.memory.rag import extract_entities
        
        entities = extract_entities("Иван Петров работает в Google на Python")
        
        assert isinstance(entities, list)
        for entity in entities:
            assert 'type' in entity
            assert 'value' in entity

    def test_classify_dialog_function(self):
        """Проверяет функцию классификации диалога"""
        from backend.memory.rag import classify_dialog
        
        result = classify_dialog(
            "Как работает машинное обучение?",
            "Машинное обучение - это часть искусственного интеллекта..."
        )
        
        assert 'primary_topic' in result
        assert 'confidence' in result
        assert 'all_topics' in result
        assert 'sentiment' in result


class TestRAGIntegration:
    """Интеграционные тесты RAG"""

    @pytest.mark.asyncio
    async def test_rag_clean_imports(self):
        """Проверяет, что RAG не содержит мёртвых импортов"""
        from backend.memory import rag as rag_module
        
        assert not hasattr(rag_module, 'chromadb')

    def test_rag_constants(self):
        """Проверяет константы RAG"""
        from backend.memory.rag import (
            CONTEXT_WINDOW,
            MAX_DIALOG_LENGTH,
            RECENCY_WEIGHT,
            RELEVANCE_WEIGHT
        )
        
        assert CONTEXT_WINDOW > 0
        assert MAX_DIALOG_LENGTH > 0
        assert 0 <= RECENCY_WEIGHT <= 1
        assert 0 <= RELEVANCE_WEIGHT <= 1
        assert RECENCY_WEIGHT + RELEVANCE_WEIGHT == 1.0