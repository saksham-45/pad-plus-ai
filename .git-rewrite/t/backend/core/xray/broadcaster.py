"""
📡 XRayBroadcaster — Real-time трансляция X-Ray событий

Отправляет события трассировки и мысли через WebSocket
в реальном времени.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger("padplus.xray")


@dataclass
class BroadcastMessage:
    """Сообщение для трансляции"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }, ensure_ascii=False)


class XRayBroadcaster:
    """
    📡 Вещатель X-Ray событий
    
    Управляет WebSocket подключениями и транслирует
    события трассировки в реальном времени.
    """
    
    def __init__(self):
        self._connections: Dict[str, Any] = {}  # client_id -> websocket
        self._subscriptions: Dict[str, Set[str]] = {}  # client_id -> subscribed channels
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._broadcast_task: Optional[asyncio.Task] = None
        self._state_publisher_task: Optional[asyncio.Task] = None
        self._stats = {
            "total_messages_sent": 0,
            "total_connections": 0,
            "active_connections": 0,
            "errors": 0
        }
        
        # Каналы для подписки
        self._available_channels = {
            "trace",        # События трассировки
            "thought",      # Поток мыслей
            "pipeline",     # Статус пайплайна
            "emotion",      # Эмоции
            "decision",     # Принятие решений
            "all"           # Все события
        }
        
        logger.info("✅ XRayBroadcaster инициализирован")
    
    async def start(self):
        """Запускает фоновый вещатель"""
        if self._broadcast_task is None:
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())
            self._state_publisher_task = asyncio.create_task(self._state_publisher_loop())
            logger.info("📡 XRayBroadcaster запущен")
    
    async def stop(self):
        """Останавливает вещатель"""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            self._broadcast_task = None
        
        if self._state_publisher_task:
            self._state_publisher_task.cancel()
            try:
                await self._state_publisher_task
            except asyncio.CancelledError:
                pass
            self._state_publisher_task = None
            
        logger.info("📡 XRayBroadcaster остановлен")
    
    async def _broadcast_loop(self):
        """Фоновый цикл отправки сообщений"""
        while True:
            try:
                # Получаем сообщение из очереди
                message = await self._message_queue.get()
                
                # Отправляем подписчикам
                await self._distribute_message(message)
                
                self._message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"📡 Ошибка в broadcast loop: {e}")
                self._stats["errors"] += 1

    async def _state_publisher_loop(self):
        """Фоновый цикл публикации актуального состояния системы"""
        while True:
            try:
                await asyncio.sleep(2)
                
                if not self._connections:
                    continue
                
                # Отправляем актуальное состояние системы
                try:
                    from backend.core.xray.cognitive_state import get_cognitive_state
                    cognitive_state = get_cognitive_state()
                    await self.send_emotion_update(cognitive_state.get_pad_state())
                except Exception as e:
                    logger.debug(f"📡 Не удалось отправить состояние PAD: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"📡 Ошибка в state publisher loop: {e}")
                await asyncio.sleep(5)
    
    async def _distribute_message(self, message: BroadcastMessage):
        """Распределяет сообщение подписчикам"""
        if not self._connections:
            return
        
        tasks = []
        for client_id, ws in list(self._connections.items()):
            # Проверяем подписку
            subscribed = self._subscriptions.get(client_id, set())
            
            # Отправляем если подписан на канал или "all"
            channel = message.data.get("channel")
            if "all" in subscribed or channel in subscribed:
                tasks.append(self._send_to_client(client_id, ws, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_to_client(
        self, 
        client_id: str, 
        ws, 
        message: BroadcastMessage
    ):
        """Отправляет сообщение конкретному клиенту"""
        try:
            await ws.send_text(message.to_json())
            self._stats["total_messages_sent"] += 1
        except Exception as e:
            logger.warning(f"📡 Ошибка отправки {client_id}: {e}")
            self._stats["errors"] += 1
    
    async def connect(self, client_id: str, websocket):
        """
        Регистрирует новое WebSocket подключение
        
        Args:
            client_id: Уникальный ID клиента
            websocket: WebSocket соединение
        """
        self._connections[client_id] = websocket
        self._subscriptions[client_id] = set()
        self._stats["total_connections"] += 1
        self._stats["active_connections"] = len(self._connections)
        
        logger.info(f"📡 X-Ray клиент подключен: {client_id}")
        
        # Отправляем приветствие
        await self.broadcast(
            "welcome",
            {
                "client_id": client_id,
                "available_channels": list(self._available_channels),
                "message": "Подключено to X-Ray"
            },
            channel="system"
        )
    
    def disconnect(self, client_id: str):
        """Отключает клиента"""
        if client_id in self._connections:
            del self._connections[client_id]
        if client_id in self._subscriptions:
            del self._subscriptions[client_id]
        
        self._stats["active_connections"] = len(self._connections)
        logger.info(f"📡 X-Ray клиент отключен: {client_id}")
    
    def subscribe(self, client_id: str, channels: List[str]):
        """
        Подписывает клиента на каналы
        
        Args:
            client_id: ID клиента
            channels: Список каналов для подписки
        """
        if client_id not in self._subscriptions:
            self._subscriptions[client_id] = set()
        
        # Добавляем только валидные каналы
        valid_channels = set(channels) & self._available_channels
        self._subscriptions[client_id].update(valid_channels)
        
        logger.debug(f"📡 Клиент {client_id} подписан на: {valid_channels}")
    
    def unsubscribe(self, client_id: str, channels: List[str]):
        """Отписывает клиента от каналов"""
        if client_id in self._subscriptions:
            self._subscriptions[client_id] -= set(channels)
    
    async def broadcast(
        self, 
        event_type: str, 
        data: Dict[str, Any],
        channel: str = "all"
    ):
        """
        Транслирует событие всем подписчикам
        
        Args:
            event_type: Тип события
            data: Данные события
            channel: Канал события
        """
        message = BroadcastMessage(
            type=event_type,
            data={**data, "channel": channel},
            timestamp=datetime.now()
        )
        
        await self._message_queue.put(message)
    
    # === Специфичные методы для X-Ray событий ===
    
    async def send_trace_event(self, event_data: Dict):
        """Отправляет событие трассировки"""
        await self.broadcast("trace_event", event_data, channel="trace")
    
    async def send_thought(self, thought_data: Dict):
        """Отправляет мысль"""
        await self.broadcast("thought", thought_data, channel="thought")
    
    async def send_pipeline_status(
        self, 
        request_id: str, 
        current_stage: str,
        stage_data: Dict
    ):
        """Отправляет статус пайплайна"""
        await self.broadcast(
            "pipeline_update",
            {
                "request_id": request_id,
                "current_stage": current_stage,
                "stage_data": stage_data
            },
            channel="pipeline"
        )
    
    async def send_emotion_update(self, emotion_data: Dict):
        """Отправляет обновление эмоций"""
        await self.broadcast("emotion_update", emotion_data, channel="emotion")
    
    async def send_decision(self, decision_data: Dict):
        """Отправляет решение о стратегии"""
        await self.broadcast("decision", decision_data, channel="decision")
    
    # === Методы доступа ===
    
    def get_active_connections(self) -> int:
        """Возвращает количество активных подключений"""
        return len(self._connections)
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        return self._stats.copy()
    
    def get_subscribed_channels(self, client_id: str) -> Set[str]:
        """Возвращает каналы подписки клиента"""
        return self._subscriptions.get(client_id, set())


# Глобальный экземпляр
_broadcaster: Optional[XRayBroadcaster] = None


def get_xray_broadcaster() -> XRayBroadcaster:
    """Возвращает глобальный вещатель"""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = XRayBroadcaster()
        # Запускаем автоматически при первом использовании
        # (в asyncio контексте)
        try:
            loop = asyncio.get_running_loop()
            # Если есть running loop, создаём task
            if not _broadcaster._broadcast_task:
                _broadcaster._broadcast_task = asyncio.create_task(
                    _broadcaster._broadcast_loop()
                )
                logger.info("📡 XRayBroadcaster авто-запущен")
        except RuntimeError:
            # Нет running loop - это нормально при импорте
            pass
    return _broadcaster
