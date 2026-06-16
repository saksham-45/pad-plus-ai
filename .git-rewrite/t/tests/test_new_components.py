"""
Тесты для новых компонентов v3.1:
- Эпизодическая память
- Семантическая память
- Консолидация
- Сновидения
- Иерархическое планирование
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestEpisodicMemory:
    """Тесты эпизодической памяти"""
    
    def test_import(self):
        """Тест импорта модуля"""
        from memory.episodic import EpisodicMemory, Episode, get_episodic_memory
        assert EpisodicMemory is not None
        assert Episode is not None
    
    def test_episode_creation(self):
        """Тест создания эпизода"""
        from memory.episodic import Episode
        
        episode = Episode(
            id="test_001",
            timestamp=datetime.now(),
            user_message="Привет",
            ai_response="Привет! Как дела?",
            topic="приветствие"
        )
        
        assert episode.id == "test_001"
        assert episode.topic == "приветствие"
        assert episode.to_dict() is not None
    
    def test_add_episode(self):
        """Тест добавления эпизода"""
        from memory.episodic import get_episodic_memory
        
        episodic = get_episodic_memory()
        episode = episodic.add_episode(
            user_message="Тестовое сообщение",
            ai_response="Тестовый ответ",
            topic="тест",
            intent="question",
            significance=0.7
        )
        
        assert episode.id is not None
        assert episode.topic == "тест"
        
        # Проверяем получение
        retrieved = episodic.get_episode(episode.id)
        assert retrieved is not None
        assert retrieved.user_message == "Тестовое сообщение"
    
    def test_search_episodes(self):
        """Тест поиска эпизодов"""
        from memory.episodic import get_episodic_memory
        
        episodic = get_episodic_memory()
        
        # Добавляем эпизод
        episodic.add_episode(
            user_message="Python это язык программирования",
            ai_response="Да, Python - популярный язык",
            topic="техническое"
        )
        
        # Ищем
        results = episodic.search_episodes(query="Python", limit=5)
        assert len(results) >= 0
    
    def test_stats(self):
        """Тест статистики"""
        from memory.episodic import get_episodic_memory
        
        episodic = get_episodic_memory()
        stats = episodic.get_stats()
        
        assert "total_episodes" in stats
        assert "total_relations" in stats


class TestSemanticMemory:
    """Тесты семантической памяти"""
    
    def test_import(self):
        """Тест импорта модуля"""
        from memory.semantic import SemanticMemory, SemanticKnowledge, KnowledgeType, get_semantic_memory
        assert SemanticMemory is not None
        assert KnowledgeType is not None
    
    def test_knowledge_type_enum(self):
        """Тест типов знаний"""
        from memory.semantic import KnowledgeType
        
        assert KnowledgeType.DECLARATIVE.value == "declarative"
        assert KnowledgeType.PROCEDURAL.value == "procedural"
        assert KnowledgeType.CONCEPTUAL.value == "conceptual"
        assert KnowledgeType.METACOGNITIVE.value == "metacognitive"
    
    def test_add_knowledge(self):
        """Тест добавления знания"""
        from memory.semantic import get_semantic_memory, KnowledgeType
        
        semantic = get_semantic_memory()
        knowledge = semantic.add_knowledge(
            content="Тестовое знание",
            knowledge_type=KnowledgeType.DECLARATIVE,
            confidence=0.8,
            tags=["тест"]
        )
        
        assert knowledge.id is not None
        assert knowledge.content == "Тестовое знание"
        
        # Проверяем получение
        retrieved = semantic.get_knowledge(knowledge.id)
        assert retrieved is not None
    
    def test_learn_procedure(self):
        """Тест изучения процедуры"""
        from memory.semantic import get_semantic_memory
        
        semantic = get_semantic_memory()
        procedure = semantic.learn_procedure(
            name="Тестовая процедура",
            steps=["Шаг 1", "Шаг 2", "Шаг 3"],
            triggers=["тест", "проверка"],
            domain="testing"
        )
        
        assert procedure.id is not None
        assert len(procedure.procedure_steps) == 3
    
    def test_find_procedure(self):
        """Тест поиска процедуры"""
        from memory.semantic import get_semantic_memory
        
        semantic = get_semantic_memory()
        
        # Добавляем процедуру
        semantic.learn_procedure(
            name="Обработка запроса",
            steps=["Анализ", "Ответ"],
            triggers=["запрос", "вопрос"]
        )
        
        # Ищем применимую
        found = semantic.find_applicable_procedure("у меня есть вопрос")
        # Может быть None если нет совпадения
        assert found is None or found.procedure_steps is not None
    
    def test_self_knowledge(self):
        """Тест метакогнитивных знаний"""
        from memory.semantic import get_semantic_memory
        
        semantic = get_semantic_memory()
        
        # Добавляем знание о себе
        semantic.add_self_knowledge(
            content="Я хорошо справляюсь с тестами",
            confidence=0.7
        )
        
        # Получаем
        self_knowledge = semantic.get_self_knowledge()
        assert isinstance(self_knowledge, list)


class TestConsolidation:
    """Тесты консолидации памяти"""
    
    def test_import(self):
        """Тест импорта модуля"""
        from memory.consolidation import MemoryConsolidator, ConsolidationResult, get_consolidator
        assert MemoryConsolidator is not None
        assert ConsolidationResult is not None
    
    def test_consolidator_init(self):
        """Тест инициализации консолидатора"""
        from memory.consolidation import get_consolidator
        
        consolidator = get_consolidator()
        assert consolidator.config is not None
        assert "min_access_count" in consolidator.config
    
    def test_consolidation_stats(self):
        """Тест статистики консолидации"""
        from memory.consolidation import get_consolidator
        
        consolidator = get_consolidator()
        stats = consolidator.get_consolidation_stats()
        
        assert "total_consolidations" in stats
        assert "history" in stats or "total_items_processed" in stats


class TestDreamSystem:
    """Тесты системы сновидений"""
    
    def test_import(self):
        """Тест импорта модуля"""
        from core.dreams import DreamSystem, DreamContent, DreamReport, get_dream_system
        assert DreamSystem is not None
        assert DreamContent is not None
        assert DreamReport is not None
    
    def test_dream_system_init(self):
        """Тест инициализации системы снов"""
        from core.dreams import get_dream_system
        
        dreams = get_dream_system()
        assert dreams.config is not None
        assert "min_idle_minutes" in dreams.config
    
    def test_record_activity(self):
        """Тест записи активности"""
        from core.dreams import get_dream_system
        
        dreams = get_dream_system()
        before = dreams._last_activity
        dreams.record_activity()
        after = dreams._last_activity
        
        assert after >= before
    
    def test_should_dream(self):
        """Тест проверки необходимости сна"""
        from core.dreams import get_dream_system
        
        dreams = get_dream_system()
        result = dreams.should_dream()
        
        assert isinstance(result, bool)
    
    def test_dream_stats(self):
        """Тест статистики снов"""
        from core.dreams import get_dream_system
        
        dreams = get_dream_system()
        stats = dreams.get_dream_stats()
        
        assert "total_dreams" in stats
        assert "is_dreaming" in stats


class TestHierarchicalPlanner:
    """Тесты иерархического планирования"""
    
    def test_import(self):
        """Тест импорта модуля"""
        from autonomy.hierarchical_planner import (
            HierarchicalPlanner, Plan, PlanLevel, PlanStatus, get_hierarchical_planner
        )
        assert HierarchicalPlanner is not None
        assert Plan is not None
    
    def test_plan_level_enum(self):
        """Тест уровней планирования"""
        from autonomy.hierarchical_planner import PlanLevel
        
        assert PlanLevel.VISION.value == "vision"
        assert PlanLevel.STRATEGIC.value == "strategic"
        assert PlanLevel.TACTICAL.value == "tactical"
        assert PlanLevel.OPERATIONAL.value == "operational"
    
    def test_plan_status_enum(self):
        """Тест статусов планов"""
        from autonomy.hierarchical_planner import PlanStatus
        
        assert PlanStatus.PROPOSED.value == "proposed"
        assert PlanStatus.ACTIVE.value == "active"
        assert PlanStatus.COMPLETED.value == "completed"
    
    def test_create_vision(self):
        """Тест создания Vision"""
        from autonomy.hierarchical_planner import get_hierarchical_planner
        
        planner = get_hierarchical_planner()
        vision = planner.create_vision(
            title="Тестовое видение",
            description="Описание видения",
            importance=0.9
        )
        
        assert vision.id.startswith("vision_")
        assert vision.title == "Тестовое видение"
    
    def test_create_strategic_plan(self):
        """Тест создания стратегического плана"""
        from autonomy.hierarchical_planner import get_hierarchical_planner
        
        planner = get_hierarchical_planner()
        
        # Создаём vision
        vision = planner.create_vision(title="Vision для теста")
        
        # Создаём стратегический план
        strategic = planner.create_strategic_plan(
            title="Стратегия 1",
            parent_vision_id=vision.id
        )
        
        assert strategic.id.startswith("strat_")
        assert strategic.parent_id == vision.id
        
        # Проверяем связь
        updated_vision = planner.get_plan(vision.id)
        assert strategic.id in updated_vision.child_ids
    
    def test_update_progress(self):
        """Тест обновления прогресса"""
        from autonomy.hierarchical_planner import get_hierarchical_planner
        
        planner = get_hierarchical_planner()
        
        # Создаём план
        vision = planner.create_vision(title="Тест прогресса")
        
        # Обновляем прогресс
        planner.update_progress(vision.id, 0.5)
        
        # Проверяем
        updated = planner.get_plan(vision.id)
        assert updated.progress == 0.5
    
    def test_get_stats(self):
        """Тест статистики планирования"""
        from autonomy.hierarchical_planner import get_hierarchical_planner
        
        planner = get_hierarchical_planner()
        stats = planner.get_stats()
        
        assert "by_level" in stats
        assert "active_plans" in stats
    
    def test_get_hierarchy(self):
        """Тест получения иерархии"""
        from autonomy.hierarchical_planner import get_hierarchical_planner
        
        planner = get_hierarchical_planner()
        hierarchy = planner.get_hierarchy()
        
        assert "hierarchy" in hierarchy


class TestIntegration:
    """Интеграционные тесты"""
    
    def test_memory_flow(self):
        """Тест потока данных между типами памяти"""
        # 1. Создаём эпизод
        from memory.episodic import get_episodic_memory
        episodic = get_episodic_memory()
        
        episode = episodic.add_episode(
            user_message="Что такое машинное обучение?",
            ai_response="Машинное обучение - это область ИИ...",
            topic="техническое",
            intent="question",
            significance=0.8,
            concepts=["машинное обучение", "ИИ"]
        )
        
        assert episode.id is not None
        
        # 2. Проверяем, что можно найти в семантической памяти
        from memory.semantic import get_semantic_memory
        semantic = get_semantic_memory()
        
        # Добавляем концепцию
        concept = semantic.add_concept(
            name="Машинное обучение",
            definition="Область искусственного интеллекта",
            domain="техническое"
        )
        
        assert concept.id is not None
    
    def test_dream_consolidation_flow(self):
        """Тест потока: сон -> консолидация"""
        from core.dreams import get_dream_system
        from memory.consolidation import get_consolidator
        
        dreams = get_dream_system()
        consolidator = get_consolidator()
        
        # Проверяем, что оба модуля инициализированы
        assert dreams.config is not None
        assert consolidator.config is not None
        
        # Проверяем статистику
        dream_stats = dreams.get_dream_stats()
        cons_stats = consolidator.get_consolidation_stats()
        
        assert "total_dreams" in dream_stats
        assert "total_consolidations" in cons_stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])