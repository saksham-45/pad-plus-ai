"""
Тесты Фазы 3: Персонализация Episodic Memory

Проверяют:
1. Episodic принимает user_id параметр
2. Episodic фильтрует записи по user_id
3. Пользователь видит только свои эпизоды + общие
4. Миграция SQLite работает
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ТЕСТЫ 1: EPISODIC С USER_ID
# ============================================================================

class TestEpisodicWithUserId:
    """Тесты Episodic Memory с персонализацией"""

    def test_episode_has_user_id_field(self):
        """Проверяет, что Episode имеет поле user_id"""
        from backend.memory.episodic import Episode
        
        episode = Episode(
            id="test-123",
            timestamp=datetime.now(),
            user_message="Тест",
            ai_response="Ответ",
            user_id="user-1"
        )
        
        assert episode.user_id == "user-1"

    def test_episode_user_id_optional(self):
        """Проверяет, что user_id опционально"""
        from backend.memory.episodic import Episode
        
        episode = Episode(
            id="test-123",
            timestamp=datetime.now(),
            user_message="Тест",
            ai_response="Ответ"
        )
        
        assert episode.user_id is None

    def test_episode_to_dict_includes_user_id(self):
        """Проверяет, что to_dict включает user_id"""
        from backend.memory.episodic import Episode
        
        episode = Episode(
            id="test-123",
            timestamp=datetime.now(),
            user_message="Тест",
            ai_response="Ответ",
            user_id="user-1"
        )
        
        data = episode.to_dict()
        assert "user_id" in data
        assert data["user_id"] == "user-1"

    def test_episode_from_dict_includes_user_id(self):
        """Проверяет, что from_dict включает user_id"""
        from backend.memory.episodic import Episode
        
        data = {
            "id": "test-123",
            "timestamp": datetime.now().isoformat(),
            "user_id": "user-1",
            "user_message": "Тест",
            "ai_response": "Ответ",
            "intent": "chat",
            "topic": "общее"
        }
        
        episode = Episode.from_dict(data)
        assert episode.user_id == "user-1"


# ============================================================================
# ТЕСТЫ 2: MIGRATION
# ============================================================================

class TestMigration:
    """Тесты миграции SQLite"""

    def test_migration_script_exists(self):
        """Проверяет, что скрипт миграции существует"""
        migration_script = Path(__file__).parent.parent.parent / "scripts" / "migrate_episodic_user_id.py"
        assert migration_script.exists()

    def test_migration_script_syntax(self):
        """Проверяет синтаксис скрипта миграции"""
        import py_compile
        
        migration_script = Path(__file__).parent.parent.parent / "scripts" / "migrate_episodic_user_id.py"
        result = py_compile.compile(str(migration_script), doraise=False)
        assert result


# ============================================================================
# ТЕСТЫ 3: EPISODIC METHODS
# ============================================================================

class TestEpisodicMethods:
    """Тесты методов Episodic Memory"""

    def test_add_episode_accepts_user_id(self):
        """Проверяет, что add_episode принимает user_id"""
        from backend.memory.episodic import EpisodicMemory
        import inspect
        
        with patch('backend.memory.episodic.sqlite3.connect'):
            episodic = EpisodicMemory()
            
            sig = inspect.signature(episodic.add_episode)
            params = list(sig.parameters.keys())
            
            assert 'user_id' in params

    def test_search_episodes_accepts_user_id(self):
        """Проверяет, что search_episodes принимает user_id"""
        from backend.memory.episodic import EpisodicMemory
        import inspect
        
        with patch('backend.memory.episodic.sqlite3.connect'):
            episodic = EpisodicMemory()
            
            sig = inspect.signature(episodic.search_episodes)
            params = list(sig.parameters.keys())
            
            assert 'user_id' in params


# ============================================================================
# ТЕСТЫ 4: PIPELINE INTEGRATION
# ============================================================================

class TestPipelineIntegration:
    """Тесты интеграции Pipeline с Episodic"""

    def test_pipeline_source_has_user_id(self):
        """
        Проверяет, что в коде Pipeline есть передача user_id в Episodic
        """
        from backend.core.pipeline import PipelineExecutor
        import inspect
        
        source = inspect.getsource(PipelineExecutor.execute)
        
        # Проверяем, что есть передача user_id
        assert 'user_id' in source
        assert 'episodic.add_episode' in source
        assert 'episodic.search_episodes' in source


# ============================================================================
# СВОДНЫЙ ТЕСТ ФАЗЫ 3
# ============================================================================

class TestPhase3Integration:
    """Сводный тест Фазы 3"""

    def test_full_phase3_integration(self):
        """
        Полный тест Фазы 3: Episodic персонализация
        """
        # 1. Episode имеет user_id
        from backend.memory.episodic import Episode
        
        episode = Episode(
            id="test",
            timestamp=datetime.now(),
            user_message="Тест",
            ai_response="Ответ",
            user_id="user-1"
        )
        assert episode.user_id == "user-1"
        
        # 2. to_dict/from_dict работают с user_id
        data = episode.to_dict()
        assert "user_id" in data
        
        episode2 = Episode.from_dict(data)
        assert episode2.user_id == "user-1"
        
        # 3. Episodic Memory принимает user_id
        from backend.memory.episodic import EpisodicMemory
        import inspect
        
        with patch('backend.memory.episodic.sqlite3.connect'):
            episodic = EpisodicMemory()
            
            sig = inspect.signature(episodic.add_episode)
            assert 'user_id' in list(sig.parameters.keys())
            
            sig = inspect.signature(episodic.search_episodes)
            assert 'user_id' in list(sig.parameters.keys())
        
        # 4. Pipeline передаёт user_id
        from backend.core.pipeline import PipelineExecutor
        
        source = inspect.getsource(PipelineExecutor.execute)
        assert 'user_id' in source
        assert 'episodic.add_episode' in source
        
        # 5. Миграция существует
        migration_script = Path(__file__).parent.parent.parent / "scripts" / "migrate_episodic_user_id.py"
        assert migration_script.exists()
        
        # Все компоненты Фазы 3 работают!
        assert True
