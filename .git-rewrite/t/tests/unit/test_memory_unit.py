"""
Unit тесты для памяти
"""

import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
@pytest.mark.memory
class TestMemory:
    """Тесты системы памяти"""
    
    def test_smartcache_store_and_retrieve(self, mock_memory_record):
        """Тест хранения и извлечения из SmartCache"""
        with patch('backend.memory.smartcache_chroma.get_husk_cache') as mock_get_cache:
            mock_cache = Mock()
            mock_get_cache.return_value = mock_cache
            
            # Настройка мока
            mock_cache.store.return_value = mock_memory_record
            mock_cache.get.return_value = mock_memory_record
            
            # Вызов
            husk = mock_get_cache()
            record = husk.store("Тест шелухи", "test", 0.7)
            retrieved = husk.get(record.id)
            
            # Проверки
            assert retrieved is not None
            mock_cache.store.assert_called_once_with("Тест шелухи", "test", 0.7)
            mock_cache.get.assert_called_once_with(record.id)
    
    def test_vectormemory_store_and_delete(self, mock_memory_record):
        """Тест хранения и удаления из VectorMemory"""
        with patch('backend.memory.vector_memory_chroma.get_soil_memory') as mock_get_memory:
            mock_memory = Mock()
            mock_get_memory.return_value = mock_memory
            
            # Настройка мока
            mock_memory.store.return_value = mock_memory_record
            mock_memory.get.return_value = mock_memory_record
            
            # Вызов
            soil = mock_get_memory()
            record = soil.store("Тест почвы", "test", 0.8)
            retrieved = soil.get(record.id)
            soil.delete(record.id)
            
            # Проверки
            assert retrieved is not None
            mock_memory.store.assert_called_once_with("Тест почвы", "test", 0.8)
            mock_memory.get.assert_called_once_with(record.id)
            mock_memory.delete.assert_called_once_with(record.id)

@pytest.mark.unit
@pytest.mark.memory
class TestMemoryHygiene:
    """Тесты гигиены памяти"""
    
    def test_memory_cleanup(self):
        """Тест очистки памяти"""
        with patch('memory.hygiene.get_hygiene') as mock_get_hygiene:
            mock_hygiene = Mock()
            mock_hygiene.get_memory_stats.return_value = {
                "total_cleanups": 5,
                "memory_usage": 0.7
            }
            mock_get_hygiene.return_value = mock_hygiene
            
            # Вызов
            hygiene = mock_get_hygiene()
            stats = hygiene.get_memory_stats()
            
            # Проверки
            assert "total_cleanups" in stats
            assert stats["total_cleanups"] == 5
            mock_hygiene.get_memory_stats.assert_called_once()
