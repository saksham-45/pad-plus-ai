"""
Общие фикстуры для всех тестов
"""

import sys
import os
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

# Добавляем корень проекта и backend в путь
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))

@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для асинхронных тестов"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_llm_response():
    """Мок ответа LLM"""
    return {
        "response": "Тестовый ответ",
        "provider": "test",
        "quality_score": 0.8,
        "quality_factors": {"relevance": 0.9, "coherence": 0.8},
        "concepts_extracted": ["тест", "концепт"],
        "rag_used": False
    }

@pytest.fixture
def mock_memory_record():
    """Мок записи памяти"""
    record = Mock()
    record.id = "test_id"
    record.content = "Тестовый контент"
    record.metadata = {"type": "test"}
    record.timestamp = "2024-01-01T00:00:00Z"
    return record

@pytest.fixture
def sample_text():
    """Пример текста для тестов"""
    return "Это тестовый текст для проверки функциональности"

@pytest.fixture
def sample_dialog():
    """Пример диалога для тестов"""
    return {
        "prompt": "Тестовый вопрос",
        "response": "Тестовый ответ",
        "timestamp": "2024-01-01T00:00:00Z",
        "metadata": {"provider": "test"}
    }

@pytest.fixture
def temp_dir(tmp_path):
    """Временная директория для тестов"""
    return tmp_path

@pytest.fixture
def mock_http_client():
    """Мок HTTP клиента"""
    client = AsyncMock()
    client.post.return_value = Mock()
    client.post.return_value.status_code = 200
    client.post.return_value.json.return_value = {"status": "ok"}
    client.get.return_value = Mock()
    client.get.return_value.status_code = 200
    client.get.return_value.json.return_value = {"status": "ok"}
    return client

@pytest.fixture
def mock_websocket():
    """Мок WebSocket соединения"""
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock(return_value="test message")
    ws.close = AsyncMock()
    return ws

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Устанавливает тестовые переменные окружения"""
    monkeypatch.setenv("TEST_MODE", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", ":memory:")

@pytest.fixture
def sample_knowledge_graph():
    """Пример графа знаний для тестов"""
    return {
        "nodes": [
            {"id": "concept1", "label": "Концепт 1", "type": "concept"},
            {"id": "concept2", "label": "Концепт 2", "type": "concept"}
        ],
        "edges": [
            {"source": "concept1", "target": "concept2", "relation": "related_to"}
        ]
    }

@pytest.fixture
def sample_persona_traits():
    """Пример черт персоны для тестов"""
    return {
        "openness": 0.8,
        "conscientiousness": 0.7,
        "extraversion": 0.6,
        "agreeableness": 0.9,
        "neuroticism": 0.3
    }

@pytest.fixture
def sample_emotion_state():
    """Пример эмоционального состояния для тестов"""
    return {
        "pleasure": 0.7,
        "arousal": 0.5,
        "dominance": 0.6,
        "mood": "positive"
    }
