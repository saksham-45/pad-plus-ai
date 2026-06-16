"""
Интеграционные тесты: ChromaDB модули в Pipeline

Проверяют интеграцию через inspect кода:
1. FactMemoryChroma в Pipeline
2. VectorMemoryChroma в Pipeline
3. SmartCacheChroma в Pipeline
"""

import pytest
import inspect
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ТЕСТЫ 1: ПРОВЕРКА ИНТЕГРАЦИИ ЧЕРЕЗ INSPECT
# ============================================================================

class TestChromaDBIntegrationInPipeline:
    """Тесты интеграции ChromaDB модулей через inspect"""

    def test_fact_memory_chroma_integrated(self):
        """
        Проверяет, что FactMemoryChroma интегрирован в Pipeline
        """
        from backend.core import pipeline
        
        source = inspect.getsource(pipeline)
        
        # Проверяем, что импорт есть в коде
        assert 'from memory.fact_memory_chroma import get_fact_memory_chroma' in source
        assert 'get_fact_memory_chroma()' in source
        assert 'facts.search' in source

    def test_vector_memory_chroma_integrated(self):
        """
        Проверяет, что VectorMemoryChroma интегрирован в Pipeline
        """
        from backend.core import pipeline
        
        source = inspect.getsource(pipeline)
        
        # Проверяем, что импорт есть в коде
        assert 'from memory.vector_memory_chroma import get_vector_memory_chroma' in source
        assert 'get_vector_memory_chroma()' in source
        assert 'vector_mem.search' in source
        assert 'vector_memory_used' in source

    def test_smartcache_chroma_integrated(self):
        """
        Проверяет, что SmartCacheChroma интегрирован в Pipeline
        """
        from backend.core import pipeline
        
        source = inspect.getsource(pipeline)
        
        # Проверяем, что импорт есть в коде
        assert 'from memory.smartcache_chroma import get_smartcache_chroma' in source
        assert 'get_smartcache_chroma()' in source
        assert 'smartcache.search' in source
        assert 'smartcache.is_negative' in source
        assert 'smartcache_used' in source

    def test_vector_memory_save_integrated(self):
        """
        Проверяет, что сохранение в VectorMemory интегрировано
        """
        from backend.core import pipeline
        
        source = inspect.getsource(pipeline)
        
        # Проверяем сохранение
        assert 'vector_mem.store' in source
        assert 'VectorMemory save' in source

    def test_smartcache_save_integrated(self):
        """
        Проверяет, что сохранение в SmartCache интегрировано
        """
        from backend.core import pipeline
        
        source = inspect.getsource(pipeline)
        
        # Проверяем сохранение
        assert 'smartcache.store' in source
        assert 'SmartCache save' in source

    def test_all_chromadb_modules_integrated(self):
        """
        Проверяет, что все ChromaDB модули интегрированы
        """
        from backend.core import pipeline
        
        source = inspect.getsource(pipeline)
        
        # Проверяем все модули
        assert 'fact_memory_chroma' in source
        assert 'vector_memory_chroma' in source
        assert 'smartcache_chroma' in source
        
        # Проверяем fallback
        assert 'except (ImportError, Exception)' in source
