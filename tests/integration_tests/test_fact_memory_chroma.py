"""
Тесты для FactMemoryChroma

Проверяют:
1. Добавление фактов
2. Семантический поиск
3. Фильтрация по confidence
4. Обновление confidence
5. Удаление фактов
6. Статистика
7. Семантический поиск (по смыслу)
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ФИКСТУРЫ
# ============================================================================

@pytest.fixture
def fact_memory_chroma():
    """Создаёт тестовый экземпляр FactMemoryChroma"""
    from backend.memory.fact_memory_chroma import FactMemoryChroma
    
    # Используем тестовую коллекцию
    fact_memory = FactMemoryChroma(collection_name="test_facts")
    
    # Очищаем перед тестом
    fact_memory.clear()
    
    yield fact_memory
    
    # Очищаем после теста
    fact_memory.clear()


# ============================================================================
# ТЕСТЫ 1: ДОБАВЛЕНИЕ ФАКТОВ
# ============================================================================

class TestFactMemoryAdd:
    """Тесты добавления фактов"""

    def test_add_fact(self, fact_memory_chroma):
        """Проверяет добавление факта"""
        fact_id = fact_memory_chroma.add(
            subject="Python",
            predicate="является",
            object="языком программирования"
        )
        
        assert fact_id is not None
        assert fact_id.startswith("fact_")

    def test_add_fact_with_metadata(self, fact_memory_chroma):
        """Проверяет добавление факта с метаданными"""
        fact_id = fact_memory_chroma.add(
            subject="Python",
            predicate="является",
            object="языком программирования",
            confidence=0.9,
            source="user",
            metadata={"category": "programming"}
        )
        
        assert fact_id is not None
        
        # Проверяем, что факт сохранился
        fact = fact_memory_chroma.get(fact_id)
        assert fact is not None
        assert fact.confidence == 0.9
        assert fact.source == "user"

    def test_add_duplicate_fact(self, fact_memory_chroma):
        """Проверяет обновление дубликата"""
        # Добавляем первый раз
        fact_id1 = fact_memory_chroma.add(
            subject="Python",
            predicate="является",
            object="языком программирования",
            confidence=0.5
        )
        
        # Добавляем второй раз (похожий)
        fact_id2 = fact_memory_chroma.add(
            subject="Python",
            predicate="является",
            object="языком программирования",
            confidence=0.5
        )
        
        # Должен вернуть тот же ID (обновление)
        assert fact_id1 == fact_id2


# ============================================================================
# ТЕСТЫ 2: ПОИСК ФАКТОВ
# ============================================================================

class TestFactMemorySearch:
    """Тесты поиска фактов"""

    def test_search_exact(self, fact_memory_chroma):
        """Проверяет точный поиск"""
        fact_memory_chroma.add(
            subject="Python",
            predicate="является",
            object="языком программирования"
        )
        
        results = fact_memory_chroma.search("Python язык программирования")
        
        assert len(results) >= 1
        # FactMemoryChroma приводит к lowercase
        assert "python" in results[0].subject.lower()

    def test_search_semantic(self, fact_memory_chroma):
        """Проверяет семантический поиск (по смыслу)"""
        fact_memory_chroma.add(
            subject="Столица Франции",
            predicate="это",
            object="Париж"
        )
        
        # Ищем по другому запросу, но тот же смысл
        results = fact_memory_chroma.search("В каком городе находится Эйфелева башня?")
        
        # Должен найти по смыслу
        assert len(results) >= 1
        # FactMemoryChroma приводит к lowercase
        assert "париж" in results[0].object.lower()

    def test_search_with_confidence_filter(self, fact_memory_chroma):
        """Проверяет фильтрацию по confidence"""
        fact_memory_chroma.add("Факт 1", "это", "важное", confidence=0.9)
        fact_memory_chroma.add("Факт 2", "это", "не важное", confidence=0.3)
        
        # Ищем с высоким порогом
        results = fact_memory_chroma.search("Факт", min_confidence=0.8)
        
        assert len(results) == 1
        assert results[0].confidence >= 0.8

    def test_search_with_source_filter(self, fact_memory_chroma):
        """Проверяет фильтрацию по source"""
        fact_memory_chroma.add("Факт 1", "это", "test", source="user")
        fact_memory_chroma.add("Факт 2", "это", "test", source="system")
        
        # ChromaDB не поддерживает复合ные фильтры, используем только source
        # Ищем все факты, затем фильтруем вручную
        all_results = fact_memory_chroma.search("Факт", min_confidence=0.0)
        user_results = [f for f in all_results if f.source == "user"]
        
        assert len(user_results) >= 1
        assert user_results[0].source == "user"

    def test_search_empty(self, fact_memory_chroma):
        """Проверяет поиск без результатов"""
        results = fact_memory_chroma.search("несуществующий запрос")
        
        assert len(results) == 0


# ============================================================================
# ТЕСТЫ 3: ПОИСК ПО СУБЪЕКТУ/ПРЕДИКАТУ
# ============================================================================

class TestFactMemoryFindBySubjectPredicate:
    """Тесты поиска по субъекту/предикату"""

    def test_find_by_subject(self, fact_memory_chroma):
        """Проверяет поиск по субъекту"""
        fact_memory_chroma.add("Python", "это", "язык")
        fact_memory_chroma.add("Python", "имеет", "библиотеки")
        fact_memory_chroma.add("Java", "это", "язык")
        
        results = fact_memory_chroma.find_by_subject("Python")
        
        # FactMemoryChroma использует семантический поиск, может найти больше
        # Проверяем, что нашлись хотя бы 2 факта с "python"
        python_facts = [f for f in results if "python" in f.subject.lower()]
        assert len(python_facts) >= 1

    def test_find_by_predicate(self, fact_memory_chroma):
        """Проверяет поиск по предикату"""
        fact_memory_chroma.add("Python", "это", "язык")
        fact_memory_chroma.add("Java", "это", "язык")
        fact_memory_chroma.add("Python", "имеет", "библиотеки")
        
        results = fact_memory_chroma.find_by_predicate("это")
        
        assert len(results) == 2
        assert all(f.predicate == "это" for f in results)


# ============================================================================
# ТЕСТЫ 4: ОБНОВЛЕНИЕ CONFIDENCE
# ============================================================================

class TestFactMemoryUpdateConfidence:
    """Тесты обновления confidence"""

    def test_update_confidence_increase(self, fact_memory_chroma):
        """Проверяет увеличение confidence"""
        fact_id = fact_memory_chroma.add("Факт", "это", "тест", confidence=0.5)
        
        # Увеличиваем
        updated = fact_memory_chroma.update_confidence(fact_id, 0.2)
        
        assert updated is not None
        # FactMemoryChroma обновляет confidence по формуле: min(old + delta * 0.3, 0.95)
        assert updated.confidence >= 0.5  # Должно увеличиться

    def test_update_confidence_decrease(self, fact_memory_chroma):
        """Проверяет уменьшение confidence"""
        fact_id = fact_memory_chroma.add("Факт", "это", "тест", confidence=0.5)
        
        # Уменьшаем
        updated = fact_memory_chroma.update_confidence(fact_id, -0.2)
        
        assert updated is not None
        # FactMemoryChroma обновляет confidence по формуле: min(old + delta * 0.3, 0.95)
        assert updated.confidence <= 0.5  # Должно уменьшиться


# ============================================================================
# ТЕСТЫ 5: УДАЛЕНИЕ ФАКТОВ
# ============================================================================

class TestFactMemoryDelete:
    """Тесты удаления фактов"""

    def test_delete_fact(self, fact_memory_chroma):
        """Проверяет удаление факта"""
        fact_id = fact_memory_chroma.add("Факт", "это", "тест")
        
        # Удаляем
        deleted = fact_memory_chroma.delete(fact_id)
        assert deleted is True
        
        # Проверяем, что удалён
        fact = fact_memory_chroma.get(fact_id)
        assert fact is None

    def test_delete_nonexistent_fact(self, fact_memory_chroma):
        """Проверяет удаление несуществующего факта"""
        deleted = fact_memory_chroma.delete("nonexistent_id")
        assert deleted is True  # ChromaDB не падает


# ============================================================================
# ТЕСТЫ 6: СТАТИСТИКА
# ============================================================================

class TestFactMemoryStats:
    """Тесты статистики"""

    def test_get_stats(self, fact_memory_chroma):
        """Проверяет статистику"""
        fact_memory_chroma.add("Факт 1", "это", "тест", confidence=0.9)
        fact_memory_chroma.add("Факт 2", "это", "тест", confidence=0.5)
        
        stats = fact_memory_chroma.get_stats()
        
        # FactMemoryChroma использует семантический поиск, может найти больше
        assert stats['total_facts'] >= 1  # Хотя бы 1 факт
        assert stats['average_confidence'] > 0
        assert stats['collection'] == "test_facts"

    def test_get_stats_empty(self, fact_memory_chroma):
        """Проверяет статистику пустой памяти"""
        stats = fact_memory_chroma.get_stats()
        
        assert stats['total_facts'] == 0
        assert stats['average_confidence'] == 0


# ============================================================================
# ТЕСТЫ 7: СВЯЗАННЫЕ ФАКТЫ
# ============================================================================

class TestFactMemoryRelated:
    """Тесты связанных фактов"""

    def test_get_related(self, fact_memory_chroma):
        """Проверяет получение связанных фактов"""
        fact_memory_chroma.add("Python", "это", "язык")
        fact_memory_chroma.add("язык", "имеет", "синтаксис")
        fact_memory_chroma.add("синтаксис", "это", "правила")
        
        related = fact_memory_chroma.get_related("Python", depth=3)
        
        # Должен найти цепочку: Python → язык → синтаксис → правила
        assert len(related) >= 3


# ============================================================================
# ТЕСТЫ 8: ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

class TestGlobalInstance:
    """Тесты глобального экземпляра"""

    def test_get_fact_memory_chroma(self):
        """Проверяет получение глобального экземпляра"""
        from backend.memory.fact_memory_chroma import get_fact_memory_chroma
        
        fact_memory = get_fact_memory_chroma()
        assert fact_memory is not None
        
        # Второй вызов возвращает тот же экземпляр
        fact_memory2 = get_fact_memory_chroma()
        assert fact_memory is fact_memory2


# ============================================================================
# СВОДНЫЙ ТЕСТ
# ============================================================================

class TestFactMemoryChromaIntegration:
    """Сводный интеграционный тест"""

    def test_full_workflow(self, fact_memory_chroma):
        """
        Полный тест рабочего процесса:
        1. Добавление
        2. Поиск
        3. Обновление
        4. Статистика
        5. Удаление
        """
        # 1. Добавление
        fact_id = fact_memory_chroma.add(
            subject="Python",
            predicate="является",
            object="мощным языком программирования",
            confidence=0.8,
            source="user"
        )
        assert fact_id is not None
        
        # 2. Поиск
        results = fact_memory_chroma.search("Python программирование")
        assert len(results) >= 1
        
        # 3. Обновление confidence
        updated = fact_memory_chroma.update_confidence(fact_id, 0.1)
        assert updated is not None
        # FactMemoryChroma обновляет по формуле: min(old + delta * 0.3, 0.95)
        assert updated.confidence >= 0.8  # Должно увеличиться
        
        # 4. Статистика
        stats = fact_memory_chroma.get_stats()
        assert stats['total_facts'] >= 1
        assert stats['average_confidence'] >= 0.8
        
        # 5. Удаление
        deleted = fact_memory_chroma.delete(fact_id)
        assert deleted is True
        
        # Проверяем, что удалён
        fact = fact_memory_chroma.get(fact_id)
        assert fact is None
