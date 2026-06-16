"""
🔬 Unit-тесты для Cognitive State

Тестирует:
- CognitiveMetrics
- DecisionNode
- SourceWeight
- CognitiveState
- CognitiveStateManager
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.xray.cognitive_state import (
    CognitiveMetrics,
    DecisionNode,
    SourceWeight,
    CognitiveState,
    CognitiveStateManager,
    get_cognitive_state_manager
)


class TestCognitiveMetrics:
    """Тесты для CognitiveMetrics"""

    def test_default_values(self):
        """Значения по умолчанию"""
        metrics = CognitiveMetrics()

        assert metrics.uncertainty == 0.0
        assert metrics.cognitive_load == 0.0
        assert metrics.confidence == 1.0
        assert metrics.complexity == 0.0
        assert not metrics.verification_needed
        assert not metrics.fallback_triggered

    def test_to_dict(self):
        """Сериализация в dict"""
        metrics = CognitiveMetrics(
            uncertainty=0.3,
            cognitive_load=0.5,
            confidence=0.8,
            complexity=0.6,
            verification_needed=True,
            fallback_triggered=False
        )

        data = metrics.to_dict()

        assert data["uncertainty"] == 0.3
        assert data["cognitive_load"] == 0.5
        assert data["confidence"] == 0.8
        assert data["complexity"] == 0.6
        assert data["verification_needed"] is True
        assert data["fallback_triggered"] is False


class TestDecisionNode:
    """Тесты для DecisionNode"""

    def test_decision_creation(self):
        """Создание узла решения"""
        node = DecisionNode(
            name="strategy_selection",
            decision_type="strategy",
            options=["simple", "deep", "creative"],
            selected="deep",
            confidence=0.9,
            reasoning="Complex query"
        )

        assert node.name == "strategy_selection"
        assert node.decision_type == "strategy"
        assert len(node.options) == 3
        assert node.selected == "deep"
        assert node.confidence == 0.9
        assert node.reasoning == "Complex query"

    def test_decision_to_dict(self):
        """Сериализация решения"""
        node = DecisionNode(
            name="model_selection",
            decision_type="model",
            options=["gpt-4", "claude"],
            selected="gpt-4",
            confidence=0.95,
            reasoning="Best for reasoning",
            metadata={"tier": "premium"}
        )

        data = node.to_dict()

        assert data["name"] == "model_selection"
        assert data["selected"] == "gpt-4"
        assert data["metadata"]["tier"] == "premium"


class TestSourceWeight:
    """Тесты для SourceWeight"""

    def test_source_weight_creation(self):
        """Создание веса источника"""
        sw = SourceWeight(
            source="rag",
            weight=0.45,
            confidence=0.8,
            contribution=0.4
        )

        assert sw.source == "rag"
        assert sw.weight == 0.45
        assert sw.confidence == 0.8
        assert sw.contribution == 0.4

    def test_source_weight_to_dict(self):
        """Сериализация"""
        sw = SourceWeight(
            source="facts",
            weight=0.25,
            confidence=0.7,
            contribution=0.2
        )

        data = sw.to_dict()

        assert data["source"] == "facts"
        assert data["weight"] == 0.25
        assert data["confidence"] == 0.7
        assert data["contribution"] == 0.2


class TestCognitiveState:
    """Тесты для CognitiveState"""

    def test_state_creation(self):
        """Создание когнитивного состояния"""
        state = CognitiveState()

        assert state.trace_id is None
        assert state.user_message == ""
        assert state.strategy == "simple"
        assert state.current_stage == "idle"
        assert len(state.decision_path) == 0
        assert len(state.source_weights) == 0

    def test_record_decision(self):
        """Запись решения"""
        state = CognitiveState()

        node = state.record_decision(
            name="intent_classification",
            decision_type="classification",
            options=["question", "command", "chat"],
            selected="question",
            confidence=0.92,
            reasoning="Contains question mark"
        )

        assert len(state.decision_path) == 1
        assert node.selected == "question"
        assert node.confidence == 0.92

    def test_update_metrics(self):
        """Обновление метрик"""
        state = CognitiveState()

        state.update_metrics(
            uncertainty=0.3,
            cognitive_load=0.5,
            confidence=0.8,
            complexity=0.6
        )

        assert state.metrics.uncertainty == 0.3
        assert state.metrics.cognitive_load == 0.5
        assert state.metrics.confidence == 0.8
        assert state.metrics.complexity == 0.6

    def test_update_metrics_clamping(self):
        """Ограничение метрик диапазоном [0, 1]"""
        state = CognitiveState()

        state.update_metrics(
            uncertainty=1.5,  # > 1
            cognitive_load=-0.3,  # < 0
            confidence=2.0  # > 1
        )

        assert state.metrics.uncertainty == 1.0
        assert state.metrics.cognitive_load == 0.0
        assert state.metrics.confidence == 1.0

    def test_set_source_weight(self):
        """Установка веса источника"""
        state = CognitiveState()

        state.set_source_weight("rag", 0.45, 0.8)
        state.set_source_weight("facts", 0.25, 0.7)

        assert len(state.source_weights) == 2
        assert state.source_weights["rag"].weight == 0.45
        assert state.source_weights["facts"].confidence == 0.7

    def test_calculate_final_confidence(self):
        """Расчёт итоговой уверенности"""
        state = CognitiveState()

        state.set_source_weight("rag", 0.45, 0.8, 0.4)
        state.set_source_weight("facts", 0.25, 0.7, 0.2)
        state.set_source_weight("llm", 0.30, 0.6, 0.3)

        # weighted_sum = 0.45*0.8*0.4 + 0.25*0.7*0.2 + 0.30*0.6*0.3
        #              = 0.144 + 0.035 + 0.054 = 0.233
        # total_weight = 0.45*0.4 + 0.25*0.2 + 0.30*0.3
        #              = 0.18 + 0.05 + 0.09 = 0.32
        # final = 0.233 / 0.32 = 0.728...
        final = state.calculate_final_confidence()

        assert 0.72 < final < 0.74

    def test_calculate_final_confidence_no_sources(self):
        """Без источников — возвращает confidence из metrics"""
        state = CognitiveState()
        state.metrics.confidence = 0.85

        final = state.calculate_final_confidence()

        assert final == 0.85

    def test_get_cognitive_load_score(self):
        """Расчёт когнитивной нагрузки"""
        state = CognitiveState()

        state.update_metrics(complexity=0.8, uncertainty=0.6)
        state.stages_completed = ["safety", "intent", "retrieve"]  # 3 stages

        # load = 0.8 * 0.6 * (1 + 3*0.1) = 0.48 * 1.3 = 0.624
        load = state.get_cognitive_load_score()

        assert 0.62 < load < 0.63

    def test_get_cognitive_load_score_cap(self):
        """Ограничение нагрузки максимум 1.0"""
        state = CognitiveState()

        state.update_metrics(complexity=1.0, uncertainty=1.0)
        state.stages_completed = ["safety", "intent", "retrieve", 
                                   "generate", "verify", "remember", 
                                   "emit", "complete"]  # 8 stages

        # load = 1.0 * 1.0 * (1 + 8*0.1) = 1.8 → cap at 1.0
        load = state.get_cognitive_load_score()

        assert load == 1.0

    def test_should_verify(self):
        """Проверка необходимости верификации"""
        state = CognitiveState()

        # По умолчанию нужно (нет источников)
        assert state.should_verify()

        # Добавляем источник
        state.set_source_weight("rag", 0.5, 0.8)

        # Теперь не нужно (есть источники, нормальная уверенность)
        assert not state.should_verify()

        # Высокая неопределённость
        state.update_metrics(uncertainty=0.6)
        assert state.should_verify()

        # Сброс
        state.update_metrics(uncertainty=0.3, confidence=0.8)
        assert not state.should_verify()

        # Низкая уверенность
        state.update_metrics(confidence=0.3)
        assert state.should_verify()

    def test_should_simplify(self):
        """Проверка необходимости упрощения"""
        state = CognitiveState()

        # По умолчанию не нужно
        assert not state.should_simplify()

        # Высокая нагрузка
        state.update_metrics(complexity=0.9, uncertainty=0.9)
        state.stages_completed = list(range(10))  # много стадий

        assert state.should_simplify()

    def test_set_strategy(self):
        """Установка стратегии"""
        state = CognitiveState()

        state.set_strategy("deep", "Complex query requires analysis")

        assert state.strategy == "deep"
        assert state.strategy_reason == "Complex query requires analysis"

    def test_complete_stage(self):
        """Завершение стадии"""
        state = CognitiveState()

        state.complete_stage("safety")
        state.complete_stage("intent")
        state.complete_stage("retrieve")

        assert state.current_stage == "retrieve"
        assert len(state.stages_completed) == 3
        assert "safety" in state.stages_completed
        assert "retrieve" in state.stages_completed

    def test_to_dict(self):
        """Сериализация состояния"""
        state = CognitiveState()
        state.trace_id = "trace-123"
        state.user_message = "Test query"
        state.set_strategy("deep", "Test reason")
        state.complete_stage("safety")
        state.update_metrics(confidence=0.8)

        data = state.to_dict()

        assert data["trace_id"] == "trace-123"
        assert data["user_message"] == "Test query"
        assert data["strategy"] == "deep"
        assert data["current_stage"] == "safety"
        assert len(data["stages_completed"]) == 1


class TestCognitiveStateManager:
    """Тесты для CognitiveStateManager"""

    def test_create_state(self):
        """Создание состояния"""
        csm = CognitiveStateManager()

        state = csm.create_state("trace-123", "Test message")

        assert state is not None
        assert state.trace_id == "trace-123"
        assert state.user_message == "Test message"
        assert csm.get_active_count() == 1

    def test_get_state(self):
        """Получение состояния"""
        csm = CognitiveStateManager()

        state = csm.create_state("trace-123", "Test")

        found = csm.get_state("trace-123")

        assert found == state

    def test_get_state_not_found(self):
        """Состояние не найдено"""
        csm = CognitiveStateManager()

        found = csm.get_state("non-existent")

        assert found is None

    def test_complete_state(self):
        """Завершение состояния"""
        csm = CognitiveStateManager()

        state = csm.create_state("trace-123", "Test")
        csm.complete_state("trace-123")

        assert csm.get_active_count() == 0
        # Состояние сохранено в историю
        assert len(csm._state_history) == 1

    def test_stats(self):
        """Статистика менеджера"""
        csm = CognitiveStateManager()

        # Создаём и завершаем несколько состояний
        for i in range(5):
            state = csm.create_state(f"trace-{i}", f"Test {i}")
            state.update_metrics(confidence=0.5 + i * 0.1)
            csm.complete_state(f"trace-{i}")

        stats = csm.get_stats()

        assert stats["total_processed"] == 5
        assert "avg_confidence" in stats
        assert "avg_cognitive_load" in stats
        assert "strategy_distribution" in stats

    def test_global_instance(self):
        """Глобальный экземпляр"""
        import core.xray.cognitive_state as cs
        cs._cognitive_state_manager = None

        instance1 = get_cognitive_state_manager()
        instance2 = get_cognitive_state_manager()

        assert instance1 is instance2

        cs._cognitive_state_manager = None