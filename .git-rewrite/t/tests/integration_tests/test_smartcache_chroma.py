"""
Тесты для SmartCacheChroma

Проверяют:
1. Добавление записей
2. Семантический поиск
3. TTL (истечение времени)
4. Negative cache
5. Удаление записей
6. Статистика
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ФИКСТУРЫ
# ============================================================================

@pytest.fixture
def smartcache_chroma():
    """Создаёт тестовый экземпляр SmartCacheChroma"""
    from backend.memory.smartcache_chroma import SmartCacheChroma
    import uuid
    
    # Используем уникальную коллекцию для каждого теста
    collection_name = f"test_sc_{uuid.uuid4().hex[:8]}"
    sc = SmartCacheChroma(collection_name=collection_name)
    
    yield sc
    
    # Очищаем после теста
    sc.clear()


# ============================================================================
# ТЕСТЫ 1: ДОБАВЛЕНИЕ ЗАПИСЕЙ
# ============================================================================

class TestSmartCacheChromaStore:
    """Тесты добавления записей"""

    def test_store_record(self, smartcache_chroma):
        """Проверяет добавление записи"""
        record = smartcache_chroma.store("Тестовая запись")
        
        assert record is not None
        assert record.id.startswith("cache_")
        assert record.text == "Тестовая запись"
        assert record.ttl == 3600  # TTL по умолчанию

    def test_store_with_custom_ttl(self, smartcache_chroma):
        """Проверяет добавление записи с custom TTL"""
        record = smartcache_chroma.store("Временная запись", ttl=60)
        
        assert record is not None
        assert record.ttl == 60

    def test_store_multiple_records(self, smartcache_chroma):
        """Проверяет добавление нескольких записей"""
        records = []
        for i in range(5):
            record = smartcache_chroma.store(f"Запись {i}")
            records.append(record)
        
        assert len(records) == 5
        assert all(r.id.startswith("cache_") for r in records)


# ============================================================================
# ТЕСТЫ 2: ПОИСК
# ============================================================================

class TestSmartCacheChromaSearch:
    """Тесты поиска записей"""

    def test_search_exact(self, smartcache_chroma):
        """Проверяет точный поиск"""
        smartcache_chroma.store("Python — язык программирования")
        
        results = smartcache_chroma.search("Python язык")
        
        assert len(results) >= 1

    def test_search_semantic(self, smartcache_chroma):
        """Проверяет семантический поиск (по смыслу)"""
        smartcache_chroma.store("Столица Франции — Париж")
        
        # Ищем по другому запросу, но тот же смысл
        results = smartcache_chroma.search("В каком городе Эйфелева башня?")
        
        # Должен найти по смыслу
        assert len(results) >= 1

    def test_search_with_confidence_filter(self, smartcache_chroma):
        """Проверяет фильтрацию по confidence"""
        smartcache_chroma.store("Факт 1", confidence=0.9)
        smartcache_chroma.store("Факт 2", confidence=0.3)
        
        # Ищем с высоким порогом
        results = smartcache_chroma.search("Факт", min_confidence=0.5)
        
        assert len(results) >= 1
        assert all(r.confidence >= 0.5 for r in results)

    def test_search_empty(self, smartcache_chroma):
        """Проверяет поиск без результатов"""
        results = smartcache_chroma.search("несуществующий запрос")
        
        assert len(results) == 0

    def test_search_limit(self, smartcache_chroma):
        """Проверяет ограничение количества результатов"""
        for i in range(10):
            smartcache_chroma.store(f"Запись {i}")
        
        results = smartcache_chroma.search("Запись", limit=5)
        
        assert len(results) <= 5


# ============================================================================
# ТЕСТЫ 3: TTL
# ============================================================================

class TestSmartCacheChromaTTL:
    """Тесты TTL (истечение времени)"""

    def test_get_expired_record(self, smartcache_chroma):
        """Проверяет, что истёкшая запись не возвращается"""
        # Добавляем запись с коротким TTL
        record = smartcache_chroma.store("Временная запись", ttl=1)
        
        # Ждём истечения TTL
        import time
        time.sleep(1.5)
        
        # Проверяем, что запись не возвращается
        retrieved = smartcache_chroma.get(record.id)
        assert retrieved is None

    def test_get_valid_record(self, smartcache_chroma):
        """Проверяет, что действительная запись возвращается"""
        record = smartcache_chroma.store("Постоянная запись", ttl=3600)
        
        retrieved = smartcache_chroma.get(record.id)
        
        assert retrieved is not None
        assert retrieved.text == "Постоянная запись"


# ============================================================================
# ТЕСТЫ 4: NEGATIVE CACHE
# ============================================================================

class TestSmartCacheChromaNegative:
    """Тесты отрицательного кэша"""

    def test_add_negative(self, smartcache_chroma):
        """Проверяет добавление отрицательного результата"""
        smartcache_chroma.add_negative("несуществующий запрос")
        
        assert smartcache_chroma.is_negative("несуществующий запрос")

    def test_negative_expires(self, smartcache_chroma):
        """Проверяет, что отрицательный результат истекает"""
        smartcache_chroma.add_negative("несуществующий запрос", ttl=1)
        
        # Проверяем сразу
        assert smartcache_chroma.is_negative("несуществующий запрос")
        
        # Ждём истечения TTL
        import time
        time.sleep(1.5)
        
        # Проверяем после истечения
        assert not smartcache_chroma.is_negative("несуществующий запрос")

    def test_search_with_negative(self, smartcache_chroma):
        """Проверяет поиск с отрицательным результатом"""
        smartcache_chroma.add_negative("отрицательный запрос")
        
        # Проверяем, что отрицательный результат есть
        assert smartcache_chroma.is_negative("отрицательный запрос")


# ============================================================================
# ТЕСТЫ 5: ПОЛУЧЕНИЕ И УДАЛЕНИЕ
# ============================================================================

class TestSmartCacheChromaGetDelete:
    """Тесты получения и удаления записей"""

    def test_get_record(self, smartcache_chroma):
        """Проверяет получение записи по ID"""
        record = smartcache_chroma.store("Тест")
        
        retrieved = smartcache_chroma.get(record.id)
        
        assert retrieved is not None
        assert retrieved.id == record.id
        assert retrieved.text == "Тест"

    def test_get_nonexistent_record(self, smartcache_chroma):
        """Проверяет получение несуществующей записи"""
        retrieved = smartcache_chroma.get("nonexistent_id")
        
        assert retrieved is None

    def test_delete_record(self, smartcache_chroma):
        """Проверяет удаление записи"""
        record = smartcache_chroma.store("Тест")
        
        deleted = smartcache_chroma.delete(record.id)
        assert deleted is True
        
        # Проверяем, что удалена
        retrieved = smartcache_chroma.get(record.id)
        assert retrieved is None

    def test_delete_nonexistent_record(self, smartcache_chroma):
        """Проверяет удаление несуществующей записи"""
        deleted = smartcache_chroma.delete("nonexistent_id")
        assert deleted is True  # ChromaDB не падает


# ============================================================================
# ТЕСТЫ 6: СТАТИСТИКА
# ============================================================================

class TestSmartCacheChromaStats:
    """Тесты статистики"""

    def test_get_stats(self, smartcache_chroma):
        """Проверяет статистику"""
        smartcache_chroma.store("Факт 1", confidence=0.9)
        smartcache_chroma.store("Факт 2", confidence=0.5)
        
        stats = smartcache_chroma.get_stats()
        
        assert stats['total_records'] == 2
        assert stats['average_confidence'] > 0
        # collection_name генерируется случайно в fixture
        assert 'test_sc_' in stats['collection']

    def test_get_stats_empty(self, smartcache_chroma):
        """Проверяет статистику пустого кэша"""
        stats = smartcache_chroma.get_stats()
        
        assert stats['total_records'] == 0
        assert stats['average_confidence'] == 0

    def test_get_stats_with_sources(self, smartcache_chroma):
        """Проверяет статистику по источникам"""
        smartcache_chroma.store("Факт", source="user")
        smartcache_chroma.store("Урок", source="fallback")
        
        stats = smartcache_chroma.get_stats()
        
        assert 'user' in stats['source_distribution']
        assert 'fallback' in stats['source_distribution']


# ============================================================================
# ТЕСТЫ 7: ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

class TestGlobalInstance:
    """Тесты глобального экземпляра"""

    def test_get_smartcache_chroma(self):
        """Проверяет получение глобального экземпляра"""
        from backend.memory.smartcache_chroma import get_smartcache_chroma
        
        sc = get_smartcache_chroma()
        assert sc is not None
        
        # Второй вызов возвращает тот же экземпляр
        sc2 = get_smartcache_chroma()
        assert sc is sc2


# ============================================================================
# СВОДНЫЙ ТЕСТ
# ============================================================================

class TestSmartCacheChromaIntegration:
    """Сводный интеграционный тест"""

    def test_full_workflow(self, smartcache_chroma):
        """
        Полный тест рабочего процесса:
        1. Добавление
        2. Поиск
        3. Получение
        4. Отрицательный кэш
        5. Статистика
        6. Удаление
        """
        # 1. Добавление
        record = smartcache_chroma.store(
            "Python — мощный язык программирования",
            confidence=0.9
        )
        assert record is not None
        
        # 2. Поиск
        results = smartcache_chroma.search("Python программирование")
        assert len(results) >= 1
        
        # 3. Получение
        retrieved = smartcache_chroma.get(record.id)
        assert retrieved is not None
        assert retrieved.confidence == 0.9
        
        # 4. Отрицательный кэш
        smartcache_chroma.add_negative("несуществующий запрос")
        assert smartcache_chroma.is_negative("несуществующий запрос")
        
        # 5. Статистика
        stats = smartcache_chroma.get_stats()
        assert stats['total_records'] >= 1
        assert stats['average_confidence'] >= 0.9
        
        # 6. Удаление
        deleted = smartcache_chroma.delete(record.id)
        assert deleted is True
        
        # Проверяем, что удалён
        retrieved = smartcache_chroma.get(record.id)
        assert retrieved is None
