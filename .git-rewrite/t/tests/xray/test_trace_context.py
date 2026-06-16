"""
🔬 Unit-тесты для Trace Context

Тестирует:
- SpanContext создание
- Trace дерево
- TraceContextManager
"""

import pytest
import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.xray.trace_context import (
    SpanContext,
    Trace,
    SpanStatus,
    TraceContextManager,
    get_trace_context_manager
)


class TestSpanContext:
    """Тесты для SpanContext"""

    def test_span_creation(self):
        """Создание спана с базовыми параметрами"""
        span = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            name="test_stage",
            kind="internal",
            start_time=1234567890.0
        )

        assert span.trace_id == "trace-123"
        assert span.span_id == "span-456"
        assert span.parent_span_id is None
        assert span.name == "test_stage"
        assert span.kind == "internal"
        assert span.status == SpanStatus.UNSET

    def test_span_duration(self):
        """Расчёт длительности спана"""
        span = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            name="test",
            kind="internal",
            start_time=100.0,
            end_time=150.0
        )

        assert span.duration_ms == 50000.0  # 50 секунд в мс

    def test_span_end(self):
        """Завершение спана"""
        span = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            name="test",
            kind="internal",
            start_time=100.0
        )

        assert span.end_time is None
        assert span.status == SpanStatus.UNSET

        span.end()

        assert span.end_time is not None
        assert span.status == SpanStatus.OK

    def test_span_set_status(self):
        """Установка статуса спана"""
        span = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            name="test",
            kind="internal",
            start_time=100.0
        )

        span.set_status(SpanStatus.ERROR, "Test error")

        assert span.status == SpanStatus.ERROR
        assert span.attributes["status_description"] == "Test error"

    def test_span_add_event(self):
        """Добавление события в спан"""
        span = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            name="test",
            kind="internal",
            start_time=100.0
        )

        span.add_event("memory_query", {"query": "test"})

        assert len(span.events) == 1
        assert span.events[0]["name"] == "memory_query"
        assert span.events[0]["attributes"]["query"] == "test"

    def test_span_set_attribute(self):
        """Установка атрибута"""
        span = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            name="test",
            kind="internal",
            start_time=100.0
        )

        span.set_attribute("passed", True)
        span.set_attribute("confidence", 0.95)

        assert span.attributes["passed"] is True
        assert span.attributes["confidence"] == 0.95

    def test_span_to_dict(self):
        """Сериализация в dict"""
        span = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id=None,
            name="test",
            kind="internal",
            start_time=100.0,
            end_time=150.0
        )

        # Без вызова end() статус остаётся UNSET
        data = span.to_dict()
        assert data["trace_id"] == "trace-123"
        assert data["span_id"] == "span-456"
        assert data["duration_ms"] == 50000.0
        assert data["status"] == "unset"

        # После вызова end() статус становится OK
        span.end()
        data_after_end = span.to_dict()
        assert data_after_end["status"] == "ok"


class TestTrace:
    """Тесты для Trace"""

    def test_trace_creation(self):
        """Создание трассировки"""
        trace = Trace(
            trace_id="trace-123",
            root_span_id="span-root",
            start_time=1234567890.0,
            user_message="Test message"
        )

        assert trace.trace_id == "trace-123"
        assert trace.root_span_id == "span-root"
        assert trace.user_message == "Test message"
        assert not trace.completed

    def test_trace_add_span(self):
        """Добавление спанов в трассировку"""
        trace = Trace(
            trace_id="trace-123",
            root_span_id="span-root",
            start_time=1234567890.0,
            user_message="Test"
        )

        root_span = SpanContext(
            trace_id="trace-123",
            span_id="span-root",
            parent_span_id=None,
            name="root",
            kind="internal",
            start_time=100.0
        )

        child_span = SpanContext(
            trace_id="trace-123",
            span_id="span-child",
            parent_span_id="span-root",
            name="child",
            kind="internal",
            start_time=110.0
        )

        trace.add_span(root_span)
        trace.add_span(child_span)

        assert len(trace.spans) == 2
        assert trace.get_span("span-root") == root_span
        assert trace.get_span("span-child") == child_span

    def test_trace_get_children(self):
        """Получение дочерних спанов"""
        trace = Trace(
            trace_id="trace-123",
            root_span_id="span-root",
            start_time=1234567890.0,
            user_message="Test"
        )

        root = SpanContext(
            trace_id="trace-123",
            span_id="span-root",
            parent_span_id=None,
            name="root",
            kind="internal",
            start_time=100.0
        )

        child1 = SpanContext(
            trace_id="trace-123",
            span_id="span-child1",
            parent_span_id="span-root",
            name="child1",
            kind="internal",
            start_time=110.0
        )

        child2 = SpanContext(
            trace_id="trace-123",
            span_id="span-child2",
            parent_span_id="span-root",
            name="child2",
            kind="internal",
            start_time=120.0
        )

        trace.add_span(root)
        trace.add_span(child1)
        trace.add_span(child2)

        children = trace.get_children("span-root")

        assert len(children) == 2
        assert child1 in children
        assert child2 in children

    def test_trace_get_span_tree(self):
        """Построение дерева спанов"""
        trace = Trace(
            trace_id="trace-123",
            root_span_id="span-root",
            start_time=1234567890.0,
            user_message="Test"
        )

        root = SpanContext(
            trace_id="trace-123",
            span_id="span-root",
            parent_span_id=None,
            name="root",
            kind="internal",
            start_time=100.0,
            end_time=200.0
        )

        child = SpanContext(
            trace_id="trace-123",
            span_id="span-child",
            parent_span_id="span-root",
            name="child",
            kind="internal",
            start_time=110.0,
            end_time=150.0
        )

        trace.add_span(root)
        trace.add_span(child)

        tree = trace.get_span_tree()

        assert tree["span_id"] == "span-root"
        assert len(tree["children"]) == 1
        assert tree["children"][0]["span_id"] == "span-child"

    def test_trace_total_duration(self):
        """Расчёт общей длительности"""
        trace = Trace(
            trace_id="trace-123",
            root_span_id="span-root",
            start_time=100.0,
            user_message="Test"
        )

        span1 = SpanContext(
            trace_id="trace-123",
            span_id="span-1",
            parent_span_id=None,
            name="span1",
            kind="internal",
            start_time=100.0,
            end_time=150.0
        )

        span2 = SpanContext(
            trace_id="trace-123",
            span_id="span-2",
            parent_span_id=None,
            name="span2",
            kind="internal",
            start_time=120.0,
            end_time=200.0
        )

        trace.add_span(span1)
        trace.add_span(span2)

        # Min start = 100, max end = 200
        assert trace.get_total_duration_ms() == 100000.0

    def test_trace_critical_path(self):
        """Нахождение критического пути"""
        trace = Trace(
            trace_id="trace-123",
            root_span_id="span-root",
            start_time=100.0,
            user_message="Test"
        )

        root = SpanContext(
            trace_id="trace-123",
            span_id="span-root",
            parent_span_id=None,
            name="root",
            kind="internal",
            start_time=100.0,
            end_time=300.0  # 200ms
        )

        # Длинный путь
        long_child = SpanContext(
            trace_id="trace-123",
            span_id="span-long",
            parent_span_id="span-root",
            name="long",
            kind="internal",
            start_time=110.0,
            end_time=250.0  # 140ms
        )

        # Короткий путь
        short_child = SpanContext(
            trace_id="trace-123",
            span_id="span-short",
            parent_span_id="span-root",
            name="short",
            kind="internal",
            start_time=110.0,
            end_time=130.0  # 20ms
        )

        trace.add_span(root)
        trace.add_span(long_child)
        trace.add_span(short_child)

        critical_path = trace.get_critical_path()

        # Критический путь должен включать root и long_child
        assert root in critical_path
        assert long_child in critical_path
        assert short_child not in critical_path

    def test_trace_to_dict(self):
        """Сериализация трассировки"""
        trace = Trace(
            trace_id="trace-123",
            root_span_id="span-root",
            start_time=1234567890.0,
            user_message="Test message"
        )

        trace.completed = True

        data = trace.to_dict()

        assert data["trace_id"] == "trace-123"
        assert data["user_message"] == "Test message"
        assert data["completed"] is True


class TestTraceContextManager:
    """Тесты для TraceContextManager"""

    def test_start_trace(self):
        """Начало трассировки"""
        ctx = TraceContextManager()

        trace = ctx.start_trace("Test message")

        assert trace is not None
        assert trace.user_message == "Test message"
        assert len(ctx._active_traces) == 1
        assert len(ctx._current_span_stack) == 1  # корневой спан

    def test_start_span(self):
        """Создание спана в трассировке"""
        ctx = TraceContextManager()
        trace = ctx.start_trace("Test")

        span = ctx.start_span("test_stage", attributes={"key": "value"})

        assert span is not None
        assert span.name == "test_stage"
        assert span.trace_id == trace.trace_id
        assert span.parent_span_id == trace.root_span_id
        assert span.attributes["key"] == "value"
        assert len(ctx._current_span_stack) == 2  # root + new span

    def test_end_span(self):
        """Завершение спана"""
        ctx = TraceContextManager()
        ctx.start_trace("Test")
        span = ctx.start_span("test_stage")

        assert span.end_time is None

        ctx.end_span(span)

        assert span.end_time is not None
        assert len(ctx._current_span_stack) == 1  # только root

    def test_end_trace(self):
        """Завершение трассировки"""
        ctx = TraceContextManager()
        trace = ctx.start_trace("Test")

        ctx.end_trace(trace.trace_id)

        assert trace.completed is True
        assert len(ctx._active_traces) == 0
        assert len(ctx._current_span_stack) == 0

    def test_get_current_trace(self):
        """Получение текущей трассировки"""
        ctx = TraceContextManager()

        assert ctx.get_current_trace() is None

        trace = ctx.start_trace("Test")

        assert ctx.get_current_trace() == trace

    def test_get_trace(self):
        """Получение трассировки по ID"""
        ctx = TraceContextManager()
        trace = ctx.start_trace("Test")

        found = ctx.get_trace(trace.trace_id)

        assert found == trace

    def test_nested_spans(self):
        """Вложенные спаны"""
        ctx = TraceContextManager()
        ctx.start_trace("Test")

        parent = ctx.start_span("parent")
        child = ctx.start_span("child")
        grandchild = ctx.start_span("grandchild")

        assert grandchild.parent_span_id == child.span_id
        assert child.parent_span_id == parent.span_id
        assert parent.parent_span_id is not None  # root

        # Завершаем в обратном порядке
        ctx.end_span(grandchild)
        ctx.end_span(child)
        ctx.end_span(parent)

        assert len(ctx._current_span_stack) == 1  # только root

    def test_global_instance(self):
        """Глобальный экземпляр"""
        # Сбрасываем глобальный
        import core.xray.trace_context as tc
        tc._trace_context_manager = None

        instance1 = get_trace_context_manager()
        instance2 = get_trace_context_manager()

        assert instance1 is instance2

        # Сброс
        tc._trace_context_manager = None