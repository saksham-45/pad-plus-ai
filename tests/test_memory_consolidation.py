"""
Тестирование Memory Consolidation — PAD+ AI
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMemoryConsolidation:
    """Тестирование Memory Consolidation системы"""

    @pytest.fixture
    def consolidator(self):
        from memory.consolidation import MemoryConsolidator
        return MemoryConsolidator()

    def test_consolidator_initialization(self, consolidator):
        """Тест инициализации консолидатора"""
        assert consolidator is not None
        assert hasattr(consolidator, 'episodic')
        assert hasattr(consolidator, 'semantic')
        assert hasattr(consolidator, 'roots')
        assert hasattr(consolidator, 'rag')
        assert 'min_access_count' in consolidator.config

    def test_consolidator_config(self, consolidator):
        """Тест конфигурации консолидатора"""
        assert consolidator.config['min_access_count'] == 3
        assert consolidator.config['min_significance'] == 0.6
        assert consolidator.config['min_age_hours'] == 1

    @pytest.mark.asyncio
    async def test_consolidate_episodes_to_semantic(self, consolidator):
        """Тест консолидации эпизодов в семантическую память"""
        with patch.object(consolidator, '_get_episode_candidates', return_value=[]):
            result = consolidator.consolidate_episodes_to_semantic()
            
            assert result is not None
            assert result.source_type == "episodic"
            assert result.target_type == "semantic"
            assert isinstance(result.items_processed, int)
            assert isinstance(result.items_consolidated, int)
            assert isinstance(result.insights, list)
            assert isinstance(result.duration_seconds, float)

    @pytest.mark.asyncio
    async def test_consolidate_rag_to_semantic(self, consolidator):
        """Тест консолидации RAG в семантическую память"""
        with patch.object(consolidator.rag, 'get_recent', return_value=[]):
            result = consolidator.consolidate_rag_to_semantic()
            
            assert result is not None
            assert result.source_type == "rag"
            assert result.target_type == "semantic"

    @pytest.mark.asyncio
    async def test_consolidate_semantic_to_roots(self, consolidator):
        """Тест консолидации семантической памяти в Roots"""
        with patch.object(consolidator.semantic, 'search_knowledge', return_value=[]):
            result = consolidator.consolidate_semantic_to_roots()
            
            assert result is not None
            assert result.source_type == "semantic"
            assert result.target_type == "roots"

    def test_consolidation_result_dataclass(self):
        """Тест dataclass результата"""
        from memory.consolidation import ConsolidationResult
        from datetime import datetime
        
        result = ConsolidationResult(
            source_type="test",
            target_type="test",
            items_processed=5,
            items_consolidated=3,
            insights=["test insight"],
            duration_seconds=1.5,
            timestamp=datetime.now()
        )
        
        assert result.source_type == "test"
        assert result.target_type == "test"
        assert result.items_processed == 5
        assert result.items_consolidated == 3
        assert len(result.insights) == 1

    def test_consolidation_history(self, consolidator):
        """Тест истории консолидаций"""
        assert isinstance(consolidator._history, list)
        
        consolidator._history.append(Mock())
        assert len(consolidator._history) == 1

    @pytest.mark.asyncio
    async def test_update_knowledge_connections(self, consolidator):
        """Тест обновления связей в графе знаний"""
        result = consolidator.update_knowledge_connections()
        
        assert result is not None
        assert result.source_type == "semantic"
        assert result.target_type == "semantic_connections"


class TestConsolidationConfig:
    """Тестирование конфигурации консолидации"""

    def test_default_config_values(self):
        """Тест значений конфигурации по умолчанию"""
        from memory.consolidation import MemoryConsolidator
        
        consolidator = MemoryConsolidator()
        
        assert consolidator.config['min_access_count'] >= 1
        assert consolidator.config['min_significance'] >= 0
        assert consolidator.config['min_significance'] <= 1
        assert consolidator.config['min_age_hours'] >= 0
        assert consolidator.config['roots_confidence'] >= 0.5
        assert consolidator.config['roots_access_count'] >= 1
        assert consolidator.config['max_consolidation_batch'] >= 1
        assert consolidator.config['similarity_threshold'] >= 0.5
        assert consolidator.config['similarity_threshold'] <= 1

    def test_config_thresholds(self):
        """Тест пороговых значений конфигурации"""
        from memory.consolidation import MemoryConsolidator
        
        consolidator = MemoryConsolidator()
        
        assert consolidator.config['emotion_boost_threshold'] >= 0
        assert consolidator.config['emotion_boost_threshold'] <= 1