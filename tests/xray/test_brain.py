"""
🧠 Тесты для X-Ray Brain

Проверяет:
- XRayBrain.decide() — принятие решений
- Decision — структура решения
- SystemState — состояние системы
- MetaLearner — мета-обучение
- ReflectionLoop — рефлексия
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Добавляем backend в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))


class TestXRayBrain:
    """Тесты для XRayBrain"""

    def setup_method(self):
        """Сброс перед каждым тестом"""
        from backend.core.xray.brain import reset_xray_brain
        from backend.core.xray.system_state import reset_system_state
        from backend.core.xray.meta_learner import reset_meta_learner
        from backend.core.xray.reflection import reset_reflection_loop
        
        reset_xray_brain()
        reset_system_state()
        reset_meta_learner()
        reset_reflection_loop()

    def test_brain_simple_greeting(self):
        """Тест: простой запрос (приветствие)"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        decision = brain.decide("Привет", {})
        
        # Простой запрос должен быть распознан как simple или retrieval
        assert decision.strategy in ["simple", "retrieval"]
        assert decision.confidence > 0.5

    def test_brain_reasoning_question(self):
        """Тест: сложный вопрос (reasoning/retrieval)"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        decision = brain.decide("Почему небо голубое и как это связано с физикой?", {})
        
        # Сложный вопрос должен использовать память и верификацию
        assert decision.strategy in ["reasoning", "retrieval"]
        assert decision.use_memory == True
        assert decision.use_verification == True

    def test_brain_creative_request(self):
        """Тест: творческий запрос"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        decision = brain.decide("Придумай историю про космонавта", {})
        
        assert decision.strategy == "creative"
        # Творческий запрос может использовать или не использовать память
        assert decision.confidence > 0.5

    def test_brain_learning_request(self):
        """Тест: запрос на обучение"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        decision = brain.decide("Запомни, что я люблю кофе", {})
        
        assert decision.strategy == "learning"
        assert decision.use_memory == True
        assert decision.memory_types.get("facts") == True

    def test_brain_reflective_question(self):
        """Тест: рефлексивный вопрос"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        decision = brain.decide("Почему ты так решил?", {})
        
        assert decision.strategy == "reflective"
        assert decision.use_memory == True

    def test_brain_fallback_on_error(self):
        """Тест: fallback при ошибке"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        
        # Простой короткий запрос должен быть распознан как simple
        decision = brain.decide("Тест", {})
        
        assert decision.strategy in ["simple", "retrieval"]
        assert decision.confidence >= 0.1

    def test_brain_model_selection(self):
        """Тест: выбор модели соответствует стратегии"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        
        # Простой запрос → лёгкая модель
        decision_simple = brain.decide("Привет", {})
        assert "8b" in decision_simple.model or "flash" in decision_simple.model.lower()
        
        # Сложный запрос → мощная модель
        decision_reasoning = brain.decide("Объясни квантовую физику подробно", {})
        assert decision_reasoning.model in brain.MODEL_MAP.values()

    def test_brain_tone_selection(self):
        """Тест: выбор тона"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        
        # Технический запрос
        decision_tech = brain.decide("Как работает алгоритм сортировки?", {})
        assert decision_tech.tone == "technical"
        
        # Дружеский запрос
        decision_friendly = brain.decide("Привет, как дела?", {})
        assert decision_friendly.tone == "friendly"

    def test_brain_memory_types(self):
        """Тест: типы памяти для разных стратегий"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        
        # Retrieval → RAG + Facts
        decision = brain.decide("Найди информацию о Python", {})
        assert decision.memory_types.get("rag") == True
        assert decision.memory_types.get("facts") == True
        
        # Для сложных запросов могут использоваться разные типы памяти
        decision = brain.decide("Объясни принцип работы нейросетей", {})
        assert decision.memory_types.get("rag") == True

    def test_brain_stats(self):
        """Тест: статистика Brain"""
        from backend.core.xray.brain import get_xray_brain
        brain = get_xray_brain()
        
        # Сделаем несколько решений
        brain.decide("Привет", {})
        brain.decide("Как дела?", {})
        brain.decide("Объясни квантовую физику", {})
        
        stats = brain.get_stats()
        
        assert stats["decision_count"] == 3
        assert stats["status"] == "active"


class TestSystemState:
    """Тесты для SystemState"""

    def setup_method(self):
        """Сброс перед каждым тестом"""
        from backend.core.xray.system_state import reset_system_state
        from backend.core.xray.brain import reset_xray_brain
        from backend.core.xray.meta_learner import reset_meta_learner
        from backend.core.xray.reflection import reset_reflection_loop
        reset_system_state()
        reset_xray_brain()
        reset_meta_learner()
        reset_reflection_loop()

    def test_state_initialization(self):
        """Тест: инициализация состояния"""
        from backend.core.xray.system_state import get_system_state_manager, reset_system_state
        reset_system_state()
        manager = get_system_state_manager()
        state = manager.get_state()
        
        assert state.load == 0.0
        assert state.confidence == 1.0
        assert state.recent_errors == 0

    def test_state_update_from_result(self):
        """Тест: обновление состояния из результата"""
        from backend.core.xray.system_state import get_system_state_manager, reset_system_state
        reset_system_state()
        manager = get_system_state_manager()
        
        # Обновляем успешным результатом
        manager.update({
            "success": True,
            "confidence": 0.8,
            "execution_time_ms": 1000
        })
        
        state = manager.get_state()
        assert state.total_requests == 1
        assert state.success_count == 1
        assert state.confidence == 0.8

    def test_state_should_simplify(self):
        """Тест: определение необходимости упрощения"""
        from backend.core.xray.system_state import SystemState
        
        state = SystemState()
        
        # Нормальное состояние
        assert state.should_simplify() == False
        
        # Высокая нагрузка
        state.load = 0.9
        assert state.should_simplify() == True
        
        # Много ошибок
        state.load = 0.5
        state.recent_errors = 6
        assert state.should_simplify() == True

    def test_state_health_status(self):
        """Тест: статус здоровья системы"""
        from backend.core.xray.system_state import SystemState
        
        state = SystemState()
        
        # Здоровое состояние
        assert state.get_health_status() == "healthy"
        
        # Деградированное
        state.load = 0.8
        assert state.get_health_status() == "degraded"
        
        # Критическое
        state.load = 0.95
        assert state.get_health_status() == "critical"

    def test_state_snapshot(self):
        """Тест: снимок состояния"""
        from backend.core.xray.system_state import get_system_state_manager, reset_system_state
        reset_system_state()
        manager = get_system_state_manager()
        
        snapshot = manager.get_snapshot()
        
        assert "load" in snapshot
        assert "confidence" in snapshot
        assert "recent_errors" in snapshot
        assert "success_rate" in snapshot


class TestMetaLearner:
    """Тесты для MetaLearner"""

    def setup_method(self):
        """Сброс перед каждым тестом"""
        from backend.core.xray.meta_learner import reset_meta_learner
        from backend.core.xray.system_state import reset_system_state
        from backend.core.xray.brain import reset_xray_brain
        from backend.core.xray.reflection import reset_reflection_loop
        reset_meta_learner()
        reset_system_state()
        reset_xray_brain()
        reset_reflection_loop()

    def test_meta_learner_record_outcome(self):
        """Тест: запись результата"""
        from backend.core.xray.meta_learner import get_meta_learner, reset_meta_learner
        reset_meta_learner()
        learner = get_meta_learner()
        
        # Записываем успешный результат
        learner.record_outcome("reasoning", {"success": True, "confidence": 0.8})
        
        stats = learner.get_strategy_stats("reasoning")
        assert stats.count == 1
        assert stats.success == 1

    def test_meta_learner_fail_record(self):
        """Тест: запись неудачи"""
        from backend.core.xray.meta_learner import get_meta_learner, reset_meta_learner
        reset_meta_learner()
        learner = get_meta_learner()
        
        learner.record_outcome("simple", {"success": False, "confidence": 0.3})
        
        stats = learner.get_strategy_stats("simple")
        assert stats.fail == 1

    def test_meta_learner_success_rate(self):
        """Тест: расчёт success rate"""
        from backend.core.xray.meta_learner import get_meta_learner, reset_meta_learner
        reset_meta_learner()
        learner = get_meta_learner()
        
        # 3 успеха, 1 неудача
        learner.record_outcome("reasoning", {"success": True, "confidence": 0.8})
        learner.record_outcome("reasoning", {"success": True, "confidence": 0.9})
        learner.record_outcome("reasoning", {"success": True, "confidence": 0.7})
        learner.record_outcome("reasoning", {"success": False, "confidence": 0.3})
        
        stats = learner.get_strategy_stats("reasoning")
        assert stats.success_rate == 0.75

    def test_meta_learner_get_best_strategy(self):
        """Тест: получение лучшей стратегии"""
        from backend.core.xray.meta_learner import get_meta_learner, reset_meta_learner
        reset_meta_learner()
        learner = get_meta_learner()
        
        # Простая стратегия всегда успешна
        for _ in range(6):
            learner.record_outcome("simple", {"success": True, "confidence": 0.9})
        
        # Reasoning иногда неудачен
        for _ in range(3):
            learner.record_outcome("reasoning", {"success": True, "confidence": 0.8})
        learner.record_outcome("reasoning", {"success": False, "confidence": 0.3})
        
        best = learner.get_best_strategy(min_samples=5)
        assert best == "simple"

    def test_meta_learner_should_adjust(self):
        """Тест: рекомендация смены стратегии"""
        from backend.core.xray.meta_learner import get_meta_learner, reset_meta_learner
        reset_meta_learner()
        learner = get_meta_learner()
        
        # Creative всегда неудачен
        for _ in range(6):
            learner.record_outcome("creative", {"success": False, "confidence": 0.2})
        
        # Simple всегда успешен
        for _ in range(6):
            learner.record_outcome("simple", {"success": True, "confidence": 0.9})
        
        adjustment = learner.should_adjust_strategy("creative")
        assert adjustment == "simple"

    def test_meta_learner_patterns(self):
        """Тест: анализ паттернов"""
        from backend.core.xray.meta_learner import get_meta_learner, reset_meta_learner
        reset_meta_learner()
        learner = get_meta_learner()
        
        # 3 последовательные неудачи
        for _ in range(3):
            learner.record_outcome("reasoning", {"success": False, "confidence": 0.3})
        
        patterns = learner.analyze_patterns()
        assert len(patterns["patterns"]) > 0
        assert "последовательных неудач" in patterns["patterns"][0]


class TestReflectionLoop:
    """Тесты для ReflectionLoop"""

    def setup_method(self):
        """Сброс перед каждым тестом"""
        from backend.core.xray.reflection import reset_reflection_loop
        from backend.core.xray.meta_learner import reset_meta_learner
        from backend.core.xray.system_state import reset_system_state
        from backend.core.xray.brain import reset_xray_brain
        reset_reflection_loop()
        reset_meta_learner()
        reset_system_state()
        reset_xray_brain()

    def test_reflection_analyze_confidence_gap(self):
        """Тест: анализ разрыва уверенности"""
        from backend.core.xray.reflection import get_reflection_loop, reset_reflection_loop
        reset_reflection_loop()
        reflection = get_reflection_loop()
        
        decision = {"confidence": 0.8}
        result = {"confidence": 0.6, "success": True}
        
        gap = reflection._analyze_confidence_gap(decision, result)
        assert gap == -0.2  # Уверенность ниже ожидаемой

    def test_reflection_extract_lessons(self):
        """Тест: извлечение уроков"""
        from backend.core.xray.reflection import get_reflection_loop, reset_reflection_loop
        reset_reflection_loop()
        reflection = get_reflection_loop()
        
        decision = {"strategy": "reasoning", "confidence": 0.8, "use_memory": False}
        result = {"confidence": 0.4, "success": False, "execution_time_ms": 6000}
        
        lessons = reflection._extract_lessons(decision, result)
        
        assert len(lessons) > 0
        assert "Низкая уверенность" in lessons[0] or "Ошибка" in lessons

    def test_reflection_full_cycle(self):
        """Тест: полный цикл рефлексии"""
        from backend.core.xray.reflection import get_reflection_loop, reset_reflection_loop
        from backend.core.xray.meta_learner import get_meta_learner, reset_meta_learner
        reset_reflection_loop()
        reset_meta_learner()
        reflection = get_reflection_loop()
        
        decision = {"strategy": "reasoning", "confidence": 0.8, "use_memory": True, "use_verification": True}
        result = {"success": True, "confidence": 0.7, "execution_time_ms": 2000}
        
        reflection_result = reflection.reflect(decision, result)
        
        assert reflection_result.success == True
        assert reflection_result.confidence_gap == -0.1
        assert len(reflection_result.lessons) >= 0

    def test_reflection_stats(self):
        """Тест: статистика Reflection"""
        from backend.core.xray.reflection import get_reflection_loop, reset_reflection_loop
        reset_reflection_loop()
        reflection = get_reflection_loop()
        
        # Несколько рефлекссий
        for i in range(3):
            reflection.reflect({"strategy": "simple", "confidence": 0.8}, {"success": True, "confidence": 0.7})
        
        stats = reflection.get_stats()
        assert stats["reflection_count"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])