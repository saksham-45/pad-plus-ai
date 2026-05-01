"""
🧠 Truth Tests — Проверка поведения системы

Проверяет:
- Правильные когнитивные решения
- Failure injection
- Replay consistency
- Chaos test
- Cognitive drift
"""

import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.xray.cognitive_state import CognitiveState
from core.xray.trace_context import TraceContextManager, Trace
from core.xray.validator import TraceValidator, get_trace_validator


# === TRUTH TEST CASES ===

TRUTH_TEST_CASES = [
    {
        "name": "simple_math",
        "input": "2+2",
        "expected": {
            "strategy": "simple",
            "max_spans": 4,
            "should_retrieve": False,
            "high_confidence": True
        }
    },
    {
        "name": "complex_explanation",
        "input": "Explain quantum entanglement in detail",
        "expected": {
            "strategy": "deep",
            "min_spans": 5,
            "should_retrieve": True,
            "high_confidence": False
        }
    },
    {
        "name": "factual_query",
        "input": "What is the capital of France?",
        "expected": {
            "strategy": "simple",
            "should_retrieve": True,
            "high_confidence": True
        }
    },
    {
        "name": "creative_task",
        "input": "Write a poem about AI",
        "expected": {
            "strategy": "creative",
            "should_retrieve": False,
            "high_confidence": False
        }
    }
]


class TestTruthScenarios:
    """Truth tests для проверки поведения системы"""

    def test_simple_query_strategy(self):
        """Простой запрос → простая стратегия"""
        state = CognitiveState()
        
        # Симуляция простого запроса
        state.set_strategy("simple", "Simple factual query")
        state.update_metrics(confidence=0.9, complexity=0.2)
        state.set_source_weight("facts", 0.8, 0.9)  # Добавляем источник
        
        assert state.strategy == "simple"
        assert state.metrics.confidence > 0.8
        assert not state.should_verify()

    def test_complex_query_strategy(self):
        """Сложный запрос → глубокая стратегия"""
        state = CognitiveState()
        
        # Симуляция сложного запроса
        state.set_strategy("deep", "Complex analytical query")
        state.update_metrics(confidence=0.6, complexity=0.8, uncertainty=0.4)
        
        assert state.strategy == "deep"
        assert state.metrics.complexity > 0.5
        assert state.should_verify()  # Нужна верификация

    def test_creative_query_strategy(self):
        """Творческий запрос → креативная стратегия"""
        state = CognitiveState()
        
        state.set_strategy("creative", "Creative writing task")
        state.update_metrics(confidence=0.5, complexity=0.6)
        
        assert state.strategy == "creative"
        assert not state.should_simplify()


class TestFailureInjection:
    """Тесты с намеренным внедрением ошибок"""

    def test_missing_retrieval_detection(self):
        """Обнаружение отсутствия retrieval стадии"""
        validator = get_trace_validator()
        
        # Создаём трассировку без retrieval
        trace_data = {
            "trace_id": "test-123",
            "spans": {
                "span-1": {"name": "intent", "status": "ok"},
                "span-2": {"name": "generate", "status": "ok"},  # Пропуск retrieve
                "span-3": {"name": "emit", "status": "ok"}
            }
        }
        
        errors = validator.validate(trace_data)
        
        # Должна быть ошибка missing_required_stage
        assert any(e.code == "missing_required_stage" for e in errors)

    def test_high_confidence_contradiction(self):
        """Обнаружение противоречивого состояния"""
        validator = get_trace_validator()
        
        # Создаём противоречивое состояние
        cognitive_state = {
            "metrics": {
                "confidence": 0.95,
                "uncertainty": 0.9  # Высокая неопределённость при высокой уверенности
            }
        }
        
        errors = validator.validate({}, cognitive_state)
        
        assert any(e.code == "contradictory_state" for e in errors)

    def test_no_sources_used(self):
        """Обнаружение отсутствия источников"""
        validator = get_trace_validator()
        
        cognitive_state = {
            "metrics": {"confidence": 0.8},
            "source_weights": {}  # Нет источников
        }
        
        errors = validator.validate({}, cognitive_state)
        
        assert any(e.code == "no_sources_used" for e in errors)

    def test_high_confidence_without_reason(self):
        """Высокая уверенность без записанных решений"""
        validator = get_trace_validator()
        
        cognitive_state = {
            "metrics": {"confidence": 0.9},
            "decision_path": [],  # Нет решений
            "source_weights": {}
        }
        
        errors = validator.validate({}, cognitive_state)
        
        assert any(e.code == "high_confidence_without_reason" for e in errors)


class TestReplayConsistency:
    """Тесты консистентности replay"""

    def test_trace_structure_preserved(self):
        """Структура трассировки сохраняется"""
        ctx = TraceContextManager()
        
        # Создаём трассировку
        trace = ctx.start_trace("Test message")
        span1 = ctx.start_span("intent")
        span2 = ctx.start_span("retrieve")
        span3 = ctx.start_span("generate")
        
        # Сохраняем структуру
        original_spans = list(trace.spans.keys())
        
        # Завершаем
        ctx.end_span(span3)
        ctx.end_span(span2)
        ctx.end_span(span1)
        ctx.end_trace(trace.trace_id)
        
        # Проверяем что структура сохранена
        assert len(trace.spans) == 4  # root + 3 child spans
        assert trace.completed is True

    def test_span_hierarchy_preserved(self):
        """Иерархия спанов сохраняется"""
        ctx = TraceContextManager()
        trace = ctx.start_trace("Test")
        
        parent = ctx.start_span("parent")
        child = ctx.start_span("child")
        
        # Проверяем иерархию
        assert child.parent_span_id == parent.span_id
        assert parent.parent_span_id is not None  # root
        
        ctx.end_trace(trace.trace_id)

    def test_critical_path_calculation(self):
        """Критический путь вычисляется корректно"""
        trace = Trace(
            trace_id="test-123",
            root_span_id="root",
            start_time=100.0,
            user_message="Test"
        )
        
        # Добавляем спаны с разной длительностью
        from core.xray.trace_context import SpanContext
        
        root = SpanContext(
            trace_id="test-123",
            span_id="root",
            parent_span_id=None,
            name="root",
            kind="internal",
            start_time=100.0,
            end_time=200.0
        )
        
        long_child = SpanContext(
            trace_id="test-123",
            span_id="long",
            parent_span_id="root",
            name="long",
            kind="internal",
            start_time=110.0,
            end_time=180.0  # 70ms
        )
        
        short_child = SpanContext(
            trace_id="test-123",
            span_id="short",
            parent_span_id="root",
            name="short",
            kind="internal",
            start_time=110.0,
            end_time=130.0  # 20ms
        )
        
        trace.add_span(root)
        trace.add_span(long_child)
        trace.add_span(short_child)
        
        critical_path = trace.get_critical_path()
        
        # Критический путь должен включать long_child
        assert long_child in critical_path
        assert short_child not in critical_path


class TestChaosScenarios:
    """Хаос-тесты — проверка устойчивости"""

    def test_random_inputs(self):
        """Система обрабатывает случайные входы"""
        inputs = [
            "2+2",
            "Explain AI",
            "",  # Пустой ввод
            "???",  # Неясный ввод
            "A" * 1000,  # Очень длинный ввод
            "Очень сложный философский вопрос о существовании",
            None,  # None (будет обработан как строка)
        ]
        
        validator = get_trace_validator()
        
        for inp in inputs:
            # Создаём минимальную трассировку
            trace_data = {
                "trace_id": f"test-{hash(inp)}",
                "spans": {
                    "span-1": {"name": "intent", "status": "ok"},
                    "span-2": {"name": "generate", "status": "ok"},
                    "span-3": {"name": "emit", "status": "ok"}
                }
            }
            
            # Создаём состояние
            state = CognitiveState()
            state.update_metrics(
                confidence=random.uniform(0.3, 0.9),
                complexity=random.uniform(0.1, 0.9)
            )
            
            # Валидируем
            errors = validator.validate(trace_data, state.to_dict())
            
            # Не должно быть критичных ошибок
            assert not any(e.severity.value == "critical" for e in errors)

    def test_rapid_sequential_requests(self):
        """Быстрые последовательные запросы"""
        ctx = TraceContextManager()
        
        for i in range(10):
            trace = ctx.start_trace(f"Request {i}")
            span = ctx.start_span("test")
            ctx.end_span(span)
            ctx.end_trace(trace.trace_id)
        
        # Все трассировки должны быть завершены
        assert ctx.get_stats()["active_traces"] == 0

    def test_nested_spans_stress(self):
        """Много вложенных спанов"""
        ctx = TraceContextManager()
        trace = ctx.start_trace("Deep nesting test")
        
        # Создаём 10 вложенных спанов
        spans = []
        for i in range(10):
            span = ctx.start_span(f"level_{i}")
            spans.append(span)
        
        # Завершаем в обратном порядке
        for span in reversed(spans):
            ctx.end_span(span)
        
        ctx.end_trace(trace.trace_id)
        
        # Проверяем что всё завершено
        assert trace.completed is True
        assert len(ctx._current_span_stack) == 0


class TestCognitiveDrift:
    """Тесты на стабильность когнитивного состояния"""

    def test_strategy_stability(self):
        """Стратегия стабильна при одинаковых входах"""
        strategies = []
        
        for _ in range(5):
            state = CognitiveState()
            state.set_strategy("deep", "Complex query")
            strategies.append(state.strategy)
        
        # Все стратегии должны быть одинаковы
        assert len(set(strategies)) == 1

    def test_metrics_consistency(self):
        """Метрики остаются в допустимых пределах"""
        for _ in range(10):
            state = CognitiveState()
            state.update_metrics(
                uncertainty=random.uniform(0, 1),
                cognitive_load=random.uniform(0, 1),
                confidence=random.uniform(0, 1),
                complexity=random.uniform(0, 1)
            )
            
            # Все метрики должны быть в [0, 1]
            assert 0 <= state.metrics.uncertainty <= 1
            assert 0 <= state.metrics.cognitive_load <= 1
            assert 0 <= state.metrics.confidence <= 1
            assert 0 <= state.metrics.complexity <= 1

    def test_should_verify_consistency(self):
        """should_verify() возвращает консистентные результаты"""
        state = CognitiveState()
        
        # Без источников всегда нужно проверять
        assert state.should_verify()
        
        # С источниками — зависит от уверенности
        state.set_source_weight("rag", 0.5, 0.8)
        state.update_metrics(confidence=0.9, uncertainty=0.2)
        assert not state.should_verify()
        
        state.update_metrics(confidence=0.3, uncertainty=0.7)
        assert state.should_verify()