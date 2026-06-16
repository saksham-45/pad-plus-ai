"""
📦 Event Buffer — Буфер событий с backpressure

Реализует:
- Priority queue для событий
- Backpressure при перегрузке
- Batching для эффективной отправки
- Drop strategy для низких приоритетов
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import IntEnum
import logging
from collections import defaultdict

logger = logging.getLogger("padplus.xray")


class EventPriority(IntEnum):
    """Приоритет события (меньше = важнее)"""
    CRITICAL = 0    # Ошибки, критичные события
    HIGH = 1        # Важные обновления состояния
    NORMAL = 2      # Обычные события
    LOW = 3         # Детали, отладка


@dataclass(order=True)
class PrioritizedEvent:
    """Событие с приоритетом для очереди"""
    priority: int
    timestamp: float = field(compare=False)
    event_type: str = field(compare=False)
    data: Dict[str, Any] = field(compare=False)
    channel: str = field(compare=False, default="all")
    
    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "data": self.data,
            "channel": self.channel
        }


class EventBuffer:
    """
    📦 Буфер событий с backpressure
    
    Особенности:
    - Priority queue (критичные события не теряются)
    - Backpressure при заполнении
    - Batching для эффективной отправки
    - Drop low-priority events при перегрузке
    """
    
    def __init__(
        self, 
        max_size: int = 1000,
        batch_size: int = 10,
        flush_interval: float = 0.5
    ):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self._max_size = max_size
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        
        # Статистика
        self._stats = {
            "events_received": 0,
            "events_sent": 0,
            "events_dropped": 0,
            "batches_sent": 0,
            "backpressure_activations": 0,
            "drops_by_priority": defaultdict(int)
        }
        
        # Подписчики
        self._subscribers: List[Callable] = []
        
        # Флаг backpressure
        self._backpressure_active = False
        
        # Задача flush
        self._flush_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Запускает фоновый flush"""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info("📦 EventBuffer started")
    
    async def stop(self):
        """Останавливает буфер"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        
        # Отправляем оставшиеся события
        await self._flush()
        
        logger.info("📦 EventBuffer stopped")
    
    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        channel: str = "all"
    ) -> bool:
        """
        Публикует событие в буфер
        
        Returns:
            True если событие добавлено, False если отброшено
        """
        event = PrioritizedEvent(
            priority=priority,
            timestamp=time.time(),
            event_type=event_type,
            data=data,
            channel=channel
        )
        
        self._stats["events_received"] += 1
        
        try:
            # Пробуем добавить без блокировки
            self._queue.put_nowait(event)
            
            # Проверяем backpressure
            queue_size = self._queue.qsize()
            if queue_size > self._max_size * 0.8:
                if not self._backpressure_active:
                    self._backpressure_active = True
                    self._stats["backpressure_activations"] += 1
                    logger.warning(f"📦 Backpressure activated: {queue_size}/{self._max_size}")
            
            return True
            
        except asyncio.QueueFull:
            # Очередь полна — пытаемся дропнуть низкие приоритеты
            return await self._handle_overflow(event)
    
    async def _handle_overflow(self, event: PrioritizedEvent) -> bool:
        """Обрабатывает переполнение очереди"""
        # Если событие критичное — дропаем низкие приоритеты
        if event.priority <= EventPriority.HIGH:
            dropped = await self._drop_low_priority_events()
            if dropped:
                logger.info(f"📦 Dropped {dropped} low-priority events")
                
                # Пробуем снова добавить
                try:
                    self._queue.put_nowait(event)
                    return True
                except asyncio.QueueFull:
                    pass
        
        # Всё ещё полно — дропаем текущее если низкий приоритет
        if event.priority >= EventPriority.LOW:
            self._stats["events_dropped"] += 1
            self._stats["drops_by_priority"][event.priority] += 1
            logger.debug(f"📦 Dropped low-priority event: {event.event_type}")
            return False
        
        # Критичное событие не может быть добавлено — это плохо
        logger.error(f"📦 CRITICAL: Queue full, cannot add critical event: {event.event_type}")
        return False
    
    async def _drop_low_priority_events(self, keep_count: int = None) -> int:
        """Дропает события с низким приоритетом
        
        Args:
            keep_count: Сколько событий оставить (None = автоматическки)
        """
        dropped = 0
        temp_events = []
        
        # Вытаскиваем все события
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                temp_events.append(event)
            except asyncio.QueueEmpty:
                break
        
        if not temp_events:
            return 0
        
        # Сортируем по приоритету (важные первые)
        temp_events.sort(key=lambda e: e.priority)
        
        # Определяем сколько оставить
        if keep_count is None:
            # Дропаем до 1/3, но не больше 10
            to_drop = min(len(temp_events) // 3, 10)
            # Гарантируем что дропнем хотя бы 1 если очередь полна
            to_drop = max(to_drop, 1)
        else:
            to_drop = len(temp_events) - keep_count
        
        kept_events = temp_events[:len(temp_events) - to_drop]
        dropped_events = temp_events[len(temp_events) - to_drop:]
        
        # Возвращаем сохранённые
        for event in kept_events:
            try:
                self._queue.put_nowait(event)
            except asyncio.QueueFull:
                break
        
        # Статистика
        for event in dropped_events:
            self._stats["events_dropped"] += 1
            self._stats["drops_by_priority"][event.priority] += 1
            dropped += 1
        
        return dropped
    
    async def _flush_loop(self):
        """Фоновый цикл отправки пакетов"""
        batch = []
        last_flush = time.time()
        
        while True:
            try:
                # Ждём событие или таймаут
                try:
                    event = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=self._flush_interval
                    )
                    batch.append(event)
                except asyncio.TimeoutError:
                    pass
                
                current_time = time.time()
                
                # Отправляем если:
                # 1. Набрано достаточно событий
                # 2. Прошло достаточно времени
                should_flush = (
                    len(batch) >= self._batch_size or
                    (batch and current_time - last_flush >= self._flush_interval)
                )
                
                if should_flush and batch:
                    await self._send_batch(batch)
                    batch = []
                    last_flush = current_time
                
                # Сбрасываем backpressure если очередь пуста
                if self._queue.empty() and self._backpressure_active:
                    self._backpressure_active = False
                    logger.info("📦 Backpressure deactivated")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"📦 Flush loop error: {e}")
                await asyncio.sleep(1)
    
    async def _send_batch(self, batch: List[PrioritizedEvent]):
        """Отправляет пакет событий подписчикам"""
        if not batch or not self._subscribers:
            return
        
        events_data = [e.to_dict() for e in batch]
        
        for subscriber in self._subscribers:
            try:
                await subscriber(events_data)
            except Exception as e:
                logger.error(f"📦 Subscriber error: {e}")
        
        self._stats["events_sent"] += len(batch)
        self._stats["batches_sent"] += 1
    
    async def _flush(self):
        """Принудительный flush всех событий"""
        batch = []
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                batch.append(event)
            except asyncio.QueueEmpty:
                break
        
        if batch:
            await self._send_batch(batch)
    
    def subscribe(self, callback: Callable):
        """
        Подписывает обработчик на события
        
        Callback должен быть async и принимать List[Dict]
        """
        self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Отписывает обработчик"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    @property
    def queue_size(self) -> int:
        """Текущий размер очереди"""
        return self._queue.qsize()
    
    @property
    def is_backpressure_active(self) -> bool:
        """Активен ли backpressure"""
        return self._backpressure_active
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика буфера"""
        queue_size = self._queue.qsize()
        utilization = queue_size / self._max_size if self._max_size > 0 else 0
        
        return {
            **self._stats,
            "queue_size": queue_size,
            "max_size": self._max_size,
            "utilization": round(utilization, 3),
            "backpressure_active": self._backpressure_active,
            "drops_by_priority": dict(self._stats["drops_by_priority"])
        }


# Глобальный экземпляр
_event_buffer: Optional[EventBuffer] = None


def get_event_buffer() -> EventBuffer:
    """Возвращает глобальный буфер событий"""
    global _event_buffer
    if _event_buffer is None:
        _event_buffer = EventBuffer()
    return _event_buffer