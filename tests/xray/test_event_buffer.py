"""
📦 Unit-тесты для Event Buffer

Тестирует:
- Priority queue
- Backpressure
- Drop strategy
- Batching
"""

import sys
import asyncio
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.xray.event_buffer import (
    EventBuffer,
    EventPriority,
    PrioritizedEvent,
    get_event_buffer
)


class TestPrioritizedEvent:
    """Тесты для PrioritizedEvent"""

    def test_event_creation(self):
        """Создание события"""
        event = PrioritizedEvent(
            priority=EventPriority.NORMAL,
            timestamp=1234567890.0,
            event_type="trace_event",
            data={"stage": "safety"},
            channel="trace"
        )

        assert event.priority == EventPriority.NORMAL
        assert event.event_type == "trace_event"
        assert event.data["stage"] == "safety"
        assert event.channel == "trace"

    def test_event_ordering(self):
        """События сортируются по приоритету"""
        events = [
            PrioritizedEvent(EventPriority.LOW, 1, "low", {}),
            PrioritizedEvent(EventPriority.CRITICAL, 2, "critical", {}),
            PrioritizedEvent(EventPriority.HIGH, 3, "high", {}),
            PrioritizedEvent(EventPriority.NORMAL, 4, "normal", {}),
        ]

        sorted_events = sorted(events)

        assert sorted_events[0].priority == EventPriority.CRITICAL
        assert sorted_events[1].priority == EventPriority.HIGH
        assert sorted_events[2].priority == EventPriority.NORMAL
        assert sorted_events[3].priority == EventPriority.LOW

    def test_event_to_dict(self):
        """Сериализация в dict"""
        event = PrioritizedEvent(
            priority=EventPriority.HIGH,
            timestamp=1234567890.0,
            event_type="anomaly",
            data={"type": "slow_stage"},
            channel="anomaly"
        )

        data = event.to_dict()

        assert data["priority"] == EventPriority.HIGH
        assert data["event_type"] == "anomaly"
        assert data["data"]["type"] == "slow_stage"


class TestEventBuffer:
    """Тесты для EventBuffer"""

    @pytest.mark.asyncio
    async def test_buffer_creation(self):
        """Создание буфера"""
        buffer = EventBuffer(max_size=100, batch_size=5, flush_interval=0.1)

        assert buffer._max_size == 100
        assert buffer._batch_size == 5
        assert buffer._flush_interval == 0.1
        assert buffer.queue_size == 0
        assert not buffer.is_backpressure_active

    @pytest.mark.asyncio
    async def test_publish_event(self):
        """Публикация события"""
        buffer = EventBuffer(max_size=100)
        await buffer.start()

        result = await buffer.publish(
            event_type="trace_event",
            data={"stage": "safety"},
            priority=EventPriority.NORMAL
        )

        assert result is True
        assert buffer.queue_size == 1

        await buffer.stop()

    @pytest.mark.asyncio
    async def test_publish_with_priority(self):
        """Публикация с разными приоритетами"""
        buffer = EventBuffer(max_size=100)
        await buffer.start()

        await buffer.publish("event1", {}, EventPriority.LOW)
        await buffer.publish("event2", {}, EventPriority.CRITICAL)
        await buffer.publish("event3", {}, EventPriority.HIGH)

        assert buffer.queue_size == 3

        await buffer.stop()

    @pytest.mark.asyncio
    async def test_backpressure_activation(self):
        """Активация backpressure при заполнении"""
        buffer = EventBuffer(max_size=10, batch_size=100, flush_interval=10)
        await buffer.start()

        # Заполняем на 80%
        for i in range(8):
            await buffer.publish(f"event{i}", {}, EventPriority.NORMAL)

        assert not buffer.is_backpressure_active

        # Ещё немного — должно сработать backpressure
        for i in range(2):
            await buffer.publish(f"event{i+8}", {}, EventPriority.NORMAL)

        assert buffer.is_backpressure_active

        await buffer.stop()

    @pytest.mark.asyncio
    async def test_drop_low_priority_on_overflow(self):
        """Дроп низких приоритетов при переполнении"""
        buffer = EventBuffer(max_size=5, batch_size=100, flush_interval=10)
        await buffer.start()

        # Заполняем низкими приоритетами
        for i in range(5):
            await buffer.publish(f"low{i}", {}, EventPriority.LOW)

        assert buffer.queue_size == 5

        # Пытаемся добавить критичное — должно дропнуть низкие
        result = await buffer.publish("critical", {}, EventPriority.CRITICAL)

        assert result is True
        assert buffer._stats["events_dropped"] > 0

        await buffer.stop()

    @pytest.mark.asyncio
    async def test_critical_event_not_dropped(self):
        """Критичные события не дропаются"""
        buffer = EventBuffer(max_size=2, batch_size=100, flush_interval=10)
        await buffer.start()

        # Заполняем
        await buffer.publish("event1", {}, EventPriority.NORMAL)
        await buffer.publish("event2", {}, EventPriority.NORMAL)

        # Критичное должно пройти
        result = await buffer.publish("critical", {}, EventPriority.CRITICAL)

        assert result is True

        await buffer.stop()

    @pytest.mark.asyncio
    async def test_subscribe_and_receive(self):
        """Подписка и получение событий"""
        buffer = EventBuffer(max_size=100, batch_size=2, flush_interval=0.1)
        received_events = []

        async def handler(events):
            received_events.extend(events)

        buffer.subscribe(handler)
        await buffer.start()

        # Публикуем несколько событий
        await buffer.publish("event1", {"id": 1}, EventPriority.NORMAL)
        await buffer.publish("event2", {"id": 2}, EventPriority.NORMAL)

        # Ждём flush
        await asyncio.sleep(0.2)

        assert len(received_events) >= 2

        await buffer.stop()

    @pytest.mark.asyncio
    async def test_stats(self):
        """Статистика буфера"""
        buffer = EventBuffer(max_size=100)
        await buffer.start()

        for i in range(5):
            await buffer.publish(f"event{i}", {}, EventPriority.NORMAL)

        stats = buffer.get_stats()

        assert stats["events_received"] == 5
        assert stats["queue_size"] == 5
        assert stats["max_size"] == 100
        assert "utilization" in stats

        await buffer.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Отписка от событий"""
        buffer = EventBuffer(max_size=100, batch_size=100, flush_interval=10)
        received = []

        async def handler(events):
            received.extend(events)

        buffer.subscribe(handler)
        buffer.unsubscribe(handler)
        await buffer.start()

        await buffer.publish("event1", {}, EventPriority.NORMAL)

        # Принудительно не отправляем — подписчик отписан
        assert len(received) == 0

        await buffer.stop()

    @pytest.mark.asyncio
    async def test_global_instance(self):
        """Глобальный экземпляр"""
        import core.xray.event_buffer as eb
        eb._event_buffer = None

        instance1 = get_event_buffer()
        instance2 = get_event_buffer()

        assert instance1 is instance2

        eb._event_buffer = None
