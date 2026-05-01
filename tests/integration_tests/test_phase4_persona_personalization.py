"""
Тесты Фазы 4: Персонализация Persona

Проверяют:
1. UserPersona модель работает
2. UserPersonaManager управляет персонажами
3. Pipeline использует UserPersona
4. Эволюция личности работает
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


# ============================================================================
# ТЕСТЫ 1: USERPERSONA МОДЕЛЬ
# ============================================================================

class TestUserPersonaModel:
    """Тесты модели UserPersona"""

    def test_user_persona_creation(self):
        """Проверяет создание UserPersona"""
        from backend.memory.user_persona import UserPersona
        
        persona = UserPersona(user_id="user-123")
        
        assert persona.user_id == "user-123"
        assert persona.total_interactions == 0
        assert persona.style_preferences["verbosity"] == 0.5

    def test_user_persona_to_dict(self):
        """Проверяет сериализацию в словарь"""
        from backend.memory.user_persona import UserPersona
        
        persona = UserPersona(user_id="user-123")
        data = persona.to_dict()
        
        assert data["user_id"] == "user-123"
        assert "style_preferences" in data
        assert "interests" in data

    def test_user_persona_from_dict(self):
        """Проверяет десериализацию из словаря"""
        from backend.memory.user_persona import UserPersona
        
        data = {
            "user_id": "user-456",
            "style_preferences": {"verbosity": 0.8},
            "interests": ["programming", "AI"],
            "total_interactions": 10
        }
        
        persona = UserPersona.from_dict(data)
        
        assert persona.user_id == "user-456"
        assert persona.style_preferences["verbosity"] == 0.8
        assert "programming" in persona.interests
        assert persona.total_interactions == 10

    def test_user_persona_get_context(self):
        """Проверяет формирование контекста"""
        from backend.memory.user_persona import UserPersona
        
        persona = UserPersona(user_id="user-123")
        persona.style_preferences["verbosity"] = 0.9
        persona.interests = ["Python", "Machine Learning"]
        
        context = persona.get_context_for_prompt()
        
        assert context is not None
        assert "подробные" in context or "Python" in context

    def test_user_persona_record_interaction(self):
        """Проверяет запись взаимодействия"""
        from backend.memory.user_persona import UserPersona
        
        persona = UserPersona(user_id="user-123")
        
        persona.record_interaction(
            topic="programming",
            provider="google",
            model="gemini-2.0-flash"
        )
        
        assert persona.total_interactions == 1
        assert "programming" in persona.frequent_topics
        assert "google" in persona.preferred_providers

    def test_user_persona_adjust_style(self):
        """Проверяет корректировку стиля"""
        from backend.memory.user_persona import UserPersona
        
        persona = UserPersona(user_id="user-123")
        old_value = persona.style_preferences["verbosity"]
        
        persona.adjust_style("verbosity", 0.05, "тест")
        
        new_value = persona.style_preferences["verbosity"]
        assert new_value == old_value + 0.05
        
        # Проверяем историю эволюции
        assert len(persona.evolution_history) == 1
        assert persona.evolution_history[0]["trait"] == "verbosity"


# ============================================================================
# ТЕСТЫ 2: USERPERSONA MANAGER
# ============================================================================

class TestUserPersonaManager:
    """Тесты менеджера персонажей"""

    def test_manager_creation(self):
        """Проверяет создание менеджера"""
        from backend.memory.user_persona import UserPersonaManager
        from pathlib import Path
        
        with patch.object(Path, 'exists', return_value=False):
            manager = UserPersonaManager()
            
            assert manager is not None
            assert len(manager._personas) == 0

    def test_manager_get_persona(self):
        """Проверяет получение персоны"""
        from backend.memory.user_persona import UserPersonaManager
        from pathlib import Path
        
        with patch.object(Path, 'exists', return_value=False):
            manager = UserPersonaManager()
            
            # Получаем персону для нового пользователя
            persona1 = manager.get_persona("user-new")
            
            assert persona1 is not None
            assert persona1.user_id == "user-new"
            
            # Получаем ту же персону снова
            persona2 = manager.get_persona("user-new")
            
            assert persona1 is persona2  # Один объект

    def test_manager_save_persona(self):
        """Проверяет сохранение персоны"""
        from backend.memory.user_persona import UserPersonaManager, UserPersona
        from pathlib import Path
        
        with patch.object(Path, 'exists', return_value=False):
            manager = UserPersonaManager()
            
            persona = UserPersona(user_id="user-save-test")
            persona.total_interactions = 5
            
            manager.save_persona(persona)
            
            assert "user-save-test" in manager._personas
            assert manager._personas["user-save-test"].total_interactions == 5

    def test_manager_get_stats(self):
        """Проверяет статистику менеджера"""
        from backend.memory.user_persona import UserPersonaManager
        from pathlib import Path
        
        with patch.object(Path, 'exists', return_value=False):
            manager = UserPersonaManager()
            
            # Добавляем пользователей
            manager.get_persona("user-1")
            manager.get_persona("user-2")
            
            stats = manager.get_stats()
            
            assert stats["total_users"] == 2


# ============================================================================
# ТЕСТЫ 3: PIPELINE INTEGRATION
# ============================================================================

class TestPipelineIntegration:
    """Тесты интеграции Pipeline с UserPersona"""

    def test_pipeline_source_has_user_persona(self):
        """
        Проверяет, что в коде Pipeline есть использование UserPersona
        """
        from backend.core.pipeline import PipelineExecutor
        import inspect
        
        source = inspect.getsource(PipelineExecutor.execute)
        
        # Проверяем, что есть использование UserPersona
        assert 'user_persona' in source or 'UserPersona' in source
        assert 'get_user_persona_manager' in source

    def test_pipeline_persona_context_with_user_id(self):
        """
        Проверяет, что Pipeline использует user_id для персонализации
        """
        from backend.core.pipeline import PipelineExecutor
        import inspect
        
        source = inspect.getsource(PipelineExecutor.execute)
        
        # Ищем блок PERSONA CONTEXT
        assert '# === 6. PERSONA CONTEXT ===' in source
        
        # Проверяем, что есть проверка user_id
        assert 'user_id' in source
        assert 'get_persona' in source


# ============================================================================
# ТЕСТЫ 4: PERSONA EVOLUTION
# ============================================================================

class TestPersonaEvolution:
    """Тесты эволюции личности"""

    def test_evolution_records_changes(self):
        """Проверяет, что эволюция записывает изменения"""
        from backend.memory.user_persona import UserPersona
        
        persona = UserPersona(user_id="user-evolve")
        
        # Корректируем стиль
        persona.adjust_style("verbosity", 0.05, "положительная обратная связь")
        
        # Проверяем историю
        assert len(persona.evolution_history) >= 1
        
        change = persona.evolution_history[-1]
        assert change["trait"] == "verbosity"
        assert "reason" in change

    def test_evolution_limits_changes(self):
        """Проверяет, что изменения ограничены"""
        from backend.memory.user_persona import UserPersona
        
        persona = UserPersona(user_id="user-limit")
        persona.style_preferences["verbosity"] = 0.95
        
        # Пытаемся увеличить ещё больше
        persona.adjust_style("verbosity", 0.1, "тест")
        
        # Значение должно быть ограничено 1.0
        assert persona.style_preferences["verbosity"] <= 1.0


# ============================================================================
# СВОДНЫЙ ТЕСТ ФАЗЫ 4
# ============================================================================

class TestPhase4Integration:
    """Сводный тест Фазы 4"""

    def test_full_phase4_integration(self):
        """
        Полный тест Фазы 4: Persona персонализация
        """
        # 1. UserPersona модель работает
        from backend.memory.user_persona import UserPersona
        
        persona = UserPersona(user_id="test-user")
        assert persona.user_id == "test-user"
        
        # 2. Сериализация работает
        data = persona.to_dict()
        assert "user_id" in data
        
        persona2 = UserPersona.from_dict(data)
        assert persona2.user_id == "test-user"
        
        # 3. Менеджер работает
        from backend.memory.user_persona import UserPersonaManager
        from pathlib import Path
        import inspect
        
        with patch.object(Path, 'exists', return_value=False):
            manager = UserPersonaManager()
            
            persona3 = manager.get_persona("manager-test")
            assert persona3 is not None
        
        # 4. Pipeline использует UserPersona
        from backend.core.pipeline import PipelineExecutor
        
        source = inspect.getsource(PipelineExecutor.execute)
        assert 'get_user_persona_manager' in source
        
        # 5. Эволюция работает
        persona.adjust_style("verbosity", 0.01, "тест")
        assert len(persona.evolution_history) >= 1
        
        # Все компоненты Фазы 4 работают!
        assert True
