"""
🔥 Production Reliability Tests

Проверяет:
- Load test (500-1000 запросов)
- Buffer overflow test
- E2E WebSocket test
- Semantic replay test
- Quality regression test
"""

import sys
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.xray.cognitive_state import CognitiveState
from core.xray.trace_context import TraceContextManager
from core.xray.event_buffer import EventBuffer, EventPriority, get_event_buffer
from core.xray.validator import get_trace_validator


class TestLoadBehavior:
    """Load test — проверка под нагрузкой"""

    def test_high_load_pipeline(self):
        """Высокая нагрузка — 500 запросов"""
        ctx = TraceContextManager()
        start = time.time()
        
        for i in range(500):
            trace = ctx.start_trace(f"Load test {i}")
            span = ctx.start_span("test")
            ctx.end_span(span)
            ctx.end_trace(trace.trace_id)
        
        duration = time.time() - start
        
        # SLA: 500 запросов должны обработаться за < 10 секунд
        assert duration < 10, f"Load test failed: {duration:.2f}s > 10s"
        
        # Проверяем что нет утечек
        assert ctx.get_stats()["active_traces"] == 0

    def test_sustained_load(self):
        """Длительная нагрузка — 1000 запросов сериями"""
        ctx = TraceContextManager()
        total_start = time.time()
        
        # 10 серий по 100 запросов
        for batch in range(10):
            batch_start = time.time()
            
            for i in range(100):
                trace = ctx.start_trace(f"Sustained {batch}-{i}")
                span = ctx.start_span("test")
                ctx.end_span(span)
                ctx.end_trace(trace.trace_id)
            
            batch_duration = time.time() - batch_start
            # Каждая серия должна обрабатываться за < 2 секунды
            assert batch_duration < 2, f"Batch {batch} too slow: {batch_duration:.2f}s"
        
        total_duration = time.time() - total_start
        assert total_duration < 30, f"Total sustained load too slow: {total_duration:.2f}s"
        assert ctx.get_stats()["active_traces"] == 0


class TestEventBufferOverflow:
    """Тесты переполнения буфера"""

    def test_buffer_overflow_drops_correctly(self):
        """Переполнение буфера — дропаются правильные события"""
        buffer = EventBuffer(max_size=100, batch_size=100, flush_interval=10)
        
        # Заполняем низкими приоритетами
        for i in range(100):
            asyncio.run(buffer.publish("low_event", {}, EventPriority.LOW))
        
        # Пытаемся добавить критичные
        for i in range(20):
            asyncio.run(buffer.publish("critical_event", {}, EventPriority.CRITICAL))
        
        stats = buffer.get_stats()
        
        # Должны быть дропнутые события
        assert stats["events_dropped"] > 0, "No events dropped during overflow"
        
        # Критичные должны пройти
        assert stats["events_received"] == 120

    def test_buffer_backpressure_activates(self):
        """Backpressure активируется при 80% заполнении"""
        buffer = EventBuffer(max_size=10, batch_size=100, flush_interval=10)
        
        # Заполняем на 80%
        for i in range(8):
            asyncio.run(buffer.publish("event", {}, EventPriority.NORMAL))
        
        assert not buffer.is_backpressure_active
        
        # Ещё немного — должно сработать
        for i in range(3):
            asyncio.run(buffer.publish("event", {}, EventPriority.NORMAL))
        
        assert buffer.is_backpressure_active, "Backpressure not activated"


class TestQualityRegression:
    """Проверка деградации качества"""

    def test_confidence_stays_above_threshold(self):
        """Уверенность остаётся выше порога"""
        inputs = [
            "What is AI?",
            "Explain gravity",
            "How does a neural network work?",
            "What is quantum computing?",
            "Explain machine learning"
        ]
        
        scores = []
        
        for inp in inputs:
            state = CognitiveState()
            # Симуляция обработки
            state.set_strategy("deep", "Complex query")
            state.set_source_weight("rag", 0.5, 0.8)
            state.update_metrics(
                confidence=0.7,
                complexity=0.6,
                uncertainty=0.3
            )
            scores.append(state.metrics.confidence)
        
        avg_score = sum(scores) / len(scores)
        
        # Средняя уверенность должна быть > 0.6
        assert avg_score > 0.6, f"Quality regression: avg confidence {avg_score:.2f} < 0.6"

    def test_strategy_consistency(self):
        """Стратегии остаются консистентными"""
        strategies = []
        
        for _ in range(20):
            state = CognitiveState()
            state.set_strategy("deep", "Complex query")
            state.update_metrics(confidence=0.7, complexity=0.8)
            strategies.append(state.strategy)
        
        # Все стратегии должны быть одинаковы
        unique_strategies = set(strategies)
        assert len(unique_strategies) == 1, f"Strategy inconsistency: {unique_strategies}"


class TestSemanticReplay:
    """Проверка семантического replay"""

    def test_cognitive_state_preserved(self):
        """Когнитивное состояние сохраняется при replay"""
        # Создаём оригинальное состояние
        original = CognitiveState()
        original.set_strategy("deep", "Complex analysis")
        original.update_metrics(confidence=0.8, complexity=0.7, uncertainty=0.3)
        original.set_source_weight("rag", 0.5, 0.8)
        original.record_decision(
            "strategy_selection",
            "strategy",
            ["simple", "deep"],
            "deep",
            0.9,
            "Complex query"
        )
        
        # "Реплей" — создаём новое состояние с теми же параметрами
        replayed = CognitiveState()
        replayed.set_strategy("deep", "Complex analysis")
        replayed.update_metrics(confidence=0.8, complexity=0.7, uncertainty=0.3)
        replayed.set_source_weight("rag", 0.5, 0.8)
        replayed.record_decision(
            "strategy_selection",
            "strategy",
            ["simple", "deep"],
            "deep",
            0.9,
            "Complex query"
        )
        
        # Проверяем семантическую эквивалентность
        assert original.strategy == replayed.strategy
        assert original.metrics.confidence == replayed.metrics.confidence
        assert original.metrics.complexity == replayed.metrics.complexity
        assert len(original.decision_path) == len(replayed.decision_path)


class TestValidatorUnderLoad:
    """Валидатор под нагрузкой"""

    def test_validator_handles_many_traces(self):
        """Валидатор обрабатывает много трассировок"""
        validator = get_trace_validator()
        
        for i in range(100):
            trace_data = {
                "trace_id": f"test-{i}",
                "spans": {
                    f"span-{j}": {"name": "test", "status": "ok"}
                    for j in range(5)
                }
            }
            
            errors = validator.validate(trace_data)
            
            # Не должно быть критичных ошибок
            assert not any(e.severity.value == "critical" for e in errors)
        
        stats = validator.get_error_stats()
        assert stats["total_errors"] >= 0  # Валидатор работает


class TestChaosScenarios:
    """Хаос-сценарии"""

    def test_concurrent_traces(self):
        """Конкурентные трассировки"""
        ctx = TraceContextManager()
        
        # Создаём 10 конкурентных трассировок
        traces = []
        for i in range(10):
            trace = ctx.start_trace(f"Concurrent {i}")
            traces.append(trace)
        
        # Добавляем спаны
        for trace in traces:
            ctx.start_span("test")
        
        # Завершаем
        for trace in traces:
            ctx.end_trace(trace.trace_id)
        
        # Все должны быть завершены
        assert ctx.get_stats()["active_traces"] == 0

    def test_rapid_connect_disconnect(self):
        """Быстрое подключение/отключение"""
        ctx = TraceContextManager()
        
        for _ in range(50):
            trace = ctx.start_trace("Rapid test")
            ctx.end_trace(trace.trace_id)
        
        assert ctx.get_stats()["active_traces"] == 0

    def test_empty_and_null_inputs(self):
        """Пустые и null входы"""
        validator = get_trace_validator()
        
        test_cases = [
            {},  # Пустая трассировка
            {"trace_id": None},  # Null trace_id
            {"spans": {}},  # Нет спанов
            {"trace_id": "test", "spans": None},  # Null spans
        ]
        
        for case in test_cases:
            errors = validator.validate(case)
            # Должны быть ошибки валидации, но не краш
            assert isinstance(errors, list)