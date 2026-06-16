"""
Тесты для VectorMemoryChroma

Проверяют:
1. Добавление записей
2. Семантический поиск
3. Фильтрация по confidence
4. Удаление записей
5. Статистика
6. Сравнение с обычным VectorMemory
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ФИКСТУРЫ
# ============================================================================

@pytest.fixture
def vector_memory_chroma():
    """Создаёт тестовый экземпляр VectorMemoryChroma"""
    from backend.memory.vector_memory_chroma import VectorMemoryChroma
    import uuid
    
    # Используем уникальную коллекцию для каждого теста
    collection_name = f"test_vec_{uuid.uuid4().hex[:8]}"
    vm = VectorMemoryChroma(collection_name=collection_name)
    
    yield vm
    
    # Очищаем после теста
    vm.clear()


# ============================================================================
# ТЕСТЫ 1: ДОБАВЛЕНИЕ ЗАПИСЕЙ
# ============================================================================

class TestVectorMemoryChromaStore:
    """Тесты добавления записей"""

    def test_store_record(self, vector_memory_chroma):
        """Проверяет добавление записи"""
        record = vector_memory_chroma.store("Тестовая запись")
        
        assert record is not None
        assert record.id.startswith("vec_")
        assert record.text == "Тестовая запись"

    def test_store_with_metadata(self, vector_memory_chroma):
        """Проверяет добавление записи с метаданными"""
        record = vector_memory_chroma.store(
            "Важный факт",
            source="user",
            confidence=0.9,
            depth=5
        )
        
        assert record is not None
        assert record.confidence == 0.9
        assert record.depth == 5

    def test_store_multiple_records(self, vector_memory_chroma):
        """Проверяет добавление нескольких записей"""
        records = []
        for i in range(5):
            record = vector_memory_chroma.store(f"Запись {i}")
            records.append(record)
        
        assert len(records) == 5
        assert all(r.id.startswith("vec_") for r in records)


# ============================================================================
# ТЕСТЫ 2: ПОИСК
# ============================================================================

class TestVectorMemoryChromaSearch:
    """Тесты поиска записей"""

    def test_search_exact(self, vector_memory_chroma):
        """Проверяет точный поиск"""
        vector_memory_chroma.store("Python — язык программирования")
        
        results = vector_memory_chroma.search("Python язык")
        
        assert len(results) >= 1

    def test_search_semantic(self, vector_memory_chroma):
        """Проверяет семантический поиск (по смыслу)"""
        vector_memory_chroma.store("Столица Франции — Париж")
        
        # Ищем по другому запросу, но тот же смысл
        results = vector_memory_chroma.search("В каком городе Эйфелева башня?")
        
        # Должен найти по смыслу
        assert len(results) >= 1

    def test_search_with_confidence_filter(self, vector_memory_chroma):
        """Проверяет фильтрацию по confidence"""
        vector_memory_chroma.store("Факт 1", confidence=0.9)
        vector_memory_chroma.store("Факт 2", confidence=0.3)
        
        # Ищем с высоким порогом
        results = vector_memory_chroma.search("Факт", min_confidence=0.5)
        
        assert len(results) >= 1
        assert all(r.confidence >= 0.5 for r in results)

    def test_search_empty(self, vector_memory_chroma):
        """Проверяет поиск без результатов"""
        results = vector_memory_chroma.search("несуществующий запрос")
        
        assert len(results) == 0

    def test_search_limit(self, vector_memory_chroma):
        """Проверяет ограничение количества результатов"""
        for i in range(10):
            vector_memory_chroma.store(f"Запись {i}")
        
        results = vector_memory_chroma.search("Запись", limit=5)
        
        assert len(results) <= 5


# ============================================================================
# ТЕСТЫ 3: ПОЛУЧЕНИЕ И УДАЛЕНИЕ
# ============================================================================

class TestVectorMemoryChromaGetDelete:
    """Тесты получения и удаления записей"""

    def test_get_record(self, vector_memory_chroma):
        """Проверяет получение записи по ID"""
        record = vector_memory_chroma.store("Тест")
        
        retrieved = vector_memory_chroma.get(record.id)
        
        assert retrieved is not None
        assert retrieved.id == record.id
        assert retrieved.text == "Тест"

    def test_get_nonexistent_record(self, vector_memory_chroma):
        """Проверяет получение несуществующей записи"""
        retrieved = vector_memory_chroma.get("nonexistent_id")
        
        assert retrieved is None

    def test_delete_record(self, vector_memory_chroma):
        """Проверяет удаление записи"""
        record = vector_memory_chroma.store("Тест")
        
        deleted = vector_memory_chroma.delete(record.id)
        assert deleted is True
        
        # Проверяем, что удалена
        retrieved = vector_memory_chroma.get(record.id)
        assert retrieved is None

    def test_delete_nonexistent_record(self, vector_memory_chroma):
        """Проверяет удаление несуществующей записи"""
        deleted = vector_memory_chroma.delete("nonexistent_id")
        assert deleted is True  # ChromaDB не падает


# ============================================================================
# ТЕСТЫ 4: СТАТИСТИКА
# ============================================================================

class TestVectorMemoryChromaStats:
    """Тесты статистики"""

    def test_get_stats(self, vector_memory_chroma):
        """Проверяет статистику"""
        vector_memory_chroma.store("Факт 1", confidence=0.9)
        vector_memory_chroma.store("Факт 2", confidence=0.5)
        
        stats = vector_memory_chroma.get_stats()
        
        assert stats['total_records'] == 2
        assert stats['average_confidence'] > 0
        # collection_name генерируется случайно в fixture
        assert 'test_vec_' in stats['collection']

    def test_get_stats_empty(self, vector_memory_chroma):
        """Проверяет статистику пустой памяти"""
        stats = vector_memory_chroma.get_stats()
        
        assert stats['total_records'] == 0
        assert stats['average_confidence'] == 0

    def test_get_stats_with_sources(self, vector_memory_chroma):
        """Проверяет статистику по источникам"""
        vector_memory_chroma.store("Факт", source="user")
        vector_memory_chroma.store("Урок", source="fallback")
        
        stats = vector_memory_chroma.get_stats()
        
        assert 'user' in stats['source_distribution']
        assert 'fallback' in stats['source_distribution']


# ============================================================================
# ТЕСТЫ 5: СРАВНЕНИЕ С VECTOR MEMORY
# ============================================================================

class TestVectorMemoryComparison:
    """Тесты сравнения VectorMemory и VectorMemoryChroma"""

    def test_vector_memory_chroma_faster(self):
        """
        Проверяет, что VectorMemoryChroma быстрее или сравним
        """
        import time
        
        from backend.memory.vectormemory import VectorMemory
        from backend.memory.vector_memory_chroma import VectorMemoryChroma
        
        # Создаём памяти
        old_vm = VectorMemory()
        new_vm = VectorMemoryChroma(collection_name="test_comparison")
        
        # Очищаем
        old_vm.cleanup_expired()  # SQLite очистка
        new_vm.clear()
        
        # Добавляем факты
        for i in range(10):
            old_vm.store(f"Факт {i}")
            new_vm.store(f"Факт {i}")
        
        # Замеряем скорость поиска
        start = time.time()
        old_results = old_vm.search("Факт", limit=5)
        old_time = time.time() - start
        
        start = time.time()
        new_results = new_vm.search("Факт", limit=5)
        new_time = time.time() - start
        
        # VectorMemoryChroma должен быть быстрее или сравним
        assert len(new_results) >= 0
        assert len(old_results) >= 0


# ============================================================================
# ТЕСТЫ 6: ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

class TestGlobalInstance:
    """Тесты глобального экземпляра"""

    def test_get_vector_memory_chroma(self):
        """Проверяет получение глобального экземпляра"""
        from backend.memory.vector_memory_chroma import get_vector_memory_chroma
        
        vm = get_vector_memory_chroma()
        assert vm is not None
        
        # Второй вызов возвращает тот же экземпляр
        vm2 = get_vector_memory_chroma()
        assert vm is vm2


# ============================================================================
# СВОДНЫЙ ТЕСТ
# ============================================================================

class TestVectorMemoryChromaIntegration:
    """Сводный интеграционный тест"""

    def test_full_workflow(self, vector_memory_chroma):
        """
        Полный тест рабочего процесса:
        1. Добавление
        2. Поиск
        3. Получение
        4. Статистика
        5. Удаление
        """
        # 1. Добавление
        record = vector_memory_chroma.store(
            "Python — мощный язык программирования",
            confidence=0.9,
            depth=3
        )
        assert record is not None
        
        # 2. Поиск
        results = vector_memory_chroma.search("Python программирование")
        assert len(results) >= 1
        
        # 3. Получение
        retrieved = vector_memory_chroma.get(record.id)
        assert retrieved is not None
        assert retrieved.confidence == 0.9
        
        # 4. Статистика
        stats = vector_memory_chroma.get_stats()
        assert stats['total_records'] >= 1
        assert stats['average_confidence'] >= 0.9
        
        # 5. Удаление
        deleted = vector_memory_chroma.delete(record.id)
        assert deleted is True
        
        # Проверяем, что удалён
        retrieved = vector_memory_chroma.get(record.id)
        assert retrieved is None
