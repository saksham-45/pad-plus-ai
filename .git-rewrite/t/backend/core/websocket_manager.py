"""
🔌 WebSocketManager — Real-time коммуникация

- Push уведомления
- Стриминг ответов
- Обновление состояния в реальном времени
- Broadcast события
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable, Set
from enum import Enum
import asyncio
import json
import logging

logger = logging.getLogger("PAD+.websocket")


class EventType(Enum):
    """Типы событий"""
    # Диалог
    MESSAGE_START = "message_start"
    MESSAGE_CHUNK = "message_chunk"
    MESSAGE_END = "message_end"
    
    # Состояние
    EMOTION_UPDATE = "emotion_update"
    PERSONA_UPDATE = "persona_update"
    HEALTH_UPDATE = "health_update"
    
    # Система
    SYSTEM_ALERT = "system_alert"
    COGNITIVE_LOAD = "cognitive_load"
    LEARNING_EVENT = "learning_event"
    
    # Аналитика
    STATS_UPDATE = "stats_update"
    MEMORY_UPDATE = "memory_update"


@dataclass
class WSMessage:
    """WebSocket сообщение"""
    event: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_json(self) -> str:
        return json.dumps({
            "event": self.event,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }, ensure_ascii=False)


class WebSocketManager:
    """
    🔌 Менеджер WebSocket соединений

    Features:
    - Управление множественными соединениями
    - Broadcast сообщения
    - Room-based подписки
    - Heartbeat для проверки связи (Вторая очередь улучшений)
    """

    # === HEARTBEAT НАСТРОЙКИ ===
    HEARTBEAT_INTERVAL = 30  # Секунды между ping
    HEARTBEAT_TIMEOUT = 300  # 5 минут таймаут при бездействии

    def __init__(self):
        # Активные соединения: client_id -> websocket
        self._connections: Dict[str, Any] = {}

        # Heartbeat задачи: client_id -> asyncio.Task
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}

        # Last activity time: client_id -> datetime
        self._last_activity: Dict[str, datetime] = {}

        # Rooms: room_name -> set of client_ids
        self._rooms: Dict[str, Set[str]] = {
            "general": set(),      # Общие обновления
            "analytics": set(),    # Аналитика
            "system": set(),       # Системные события
            "dialogue": set()      # Диалоги
        }

        # Подписки на события
        self._event_subscriptions: Dict[str, Set[str]] = {}

        # Статистика
        self._stats = {
            "total_connections": 0,
            "total_messages_sent": 0,
            "total_broadcasts": 0,
            "errors": 0,
            "heartbeat_pings": 0,
            "heartbeat_timeouts": 0
        }
    
    async def connect(self, client_id: str, websocket: Any):
        """Регистрирует новое соединение"""
        self._connections[client_id] = websocket
        self._last_activity[client_id] = datetime.now()

        # Автоматически подписываем на general
        self._rooms["general"].add(client_id)

        self._stats["total_connections"] += 1

        logger.info(f"🔌 Client connected: {client_id}")

        # Запускаем heartbeat для клиента
        self._start_heartbeat(client_id)

        # Отправляем приветствие
        await self.send_to(client_id, EventType.SYSTEM_ALERT.value, {
            "message": "Connected to PAD+ AI",
            "client_id": client_id,
            "heartbeat_interval": self.HEARTBEAT_INTERVAL
        })

    def _start_heartbeat(self, client_id: str):
        """Запускает heartbeat задачу для клиента"""
        if client_id in self._heartbeat_tasks:
            self._stop_heartbeat(client_id)
        
        self._heartbeat_tasks[client_id] = asyncio.create_task(
            self._heartbeat_loop(client_id)
        )
        logger.debug(f"💓 Heartbeat started for {client_id}")

    async def _heartbeat_loop(self, client_id: str):
        """Heartbeat loop — отправляет ping каждые HEARTBEAT_INTERVAL секунд"""
        try:
            while client_id in self._connections:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                # Проверяем timeout
                last_activity = self._last_activity.get(client_id)
                if last_activity:
                    inactive_time = (datetime.now() - last_activity).total_seconds()
                    if inactive_time > self.HEARTBEAT_TIMEOUT:
                        logger.warning(f"⏰ Heartbeat timeout for {client_id} ({inactive_time:.0f}s)")
                        self._stats["heartbeat_timeouts"] += 1
                        await self.disconnect_async(client_id)
                        break
                
                # Отправляем ping
                await self._send_ping(client_id)
                
        except asyncio.CancelledError:
            pass  # Нормальное завершение
        except Exception as e:
            logger.error(f"❌ Heartbeat error for {client_id}: {e}")
            self._stats["errors"] += 1

    async def _send_ping(self, client_id: str):
        """Отправляет ping клиенту"""
        if client_id not in self._connections:
            return
        
        try:
            await self.send_to(client_id, "ping", {
                "timestamp": datetime.now().isoformat()
            })
            self._stats["heartbeat_pings"] += 1
        except Exception as e:
            logger.warning(f"⚠️ Failed to send ping to {client_id}: {e}")

    async def handle_pong(self, client_id: str):
        """Обрабатывает pong от клиента — обновляет last_activity"""
        if client_id in self._last_activity:
            self._last_activity[client_id] = datetime.now()

    def _stop_heartbeat(self, client_id: str):
        """Останавливает heartbeat задачу"""
        if client_id in self._heartbeat_tasks:
            task = self._heartbeat_tasks[client_id]
            task.cancel()
            del self._heartbeat_tasks[client_id]
            logger.debug(f"💓 Heartbeat stopped for {client_id}")

    async def disconnect_async(self, client_id: str):
        """Асинхронно отключает клиента (для heartbeat timeout)"""
        if client_id in self._connections:
            try:
                await self._connections[client_id].close(code=1000, reason="Heartbeat timeout")
            except Exception:
                pass
        self.disconnect(client_id)

    def disconnect(self, client_id: str):
        """Удаляет соединение"""
        # Останавливаем heartbeat
        self._stop_heartbeat(client_id)
        
        # Удаляем last activity
        if client_id in self._last_activity:
            del self._last_activity[client_id]
        
        if client_id in self._connections:
            del self._connections[client_id]

        # Удаляем из всех rooms
        for room in self._rooms.values():
            room.discard(client_id)

        # Удаляем из подписок
        for subscribers in self._event_subscriptions.values():
            subscribers.discard(client_id)

        logger.info(f"🔌 Client disconnected: {client_id}")
    
    async def send_to(
        self,
        client_id: str,
        event: str,
        data: Dict[str, Any]
    ) -> bool:
        """Отправляет сообщение конкретному клиенту"""
        if client_id not in self._connections:
            return False
        
        try:
            message = WSMessage(event=event, data=data)
            await self._connections[client_id].send_text(message.to_json())
            self._stats["total_messages_sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Send error to {client_id}: {e}")
            self._stats["errors"] += 1
            return False
    
    async def broadcast(
        self,
        event: str,
        data: Dict[str, Any],
        room: str = None
    ):
        """Broadcast сообщение всем или в конкретную room"""
        message = WSMessage(event=event, data=data)
        
        clients = self._rooms.get(room, set()) if room else self._connections.keys()
        
        tasks = []
        for client_id in list(clients):
            if client_id in self._connections:
                tasks.append(
                    self._safe_send(client_id, message)
                )
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self._stats["total_broadcasts"] += 1
    
    async def _safe_send(self, client_id: str, message: WSMessage):
        """Безопасная отправка с обработкой ошибок"""
        try:
            await self._connections[client_id].send_text(message.to_json())
            self._stats["total_messages_sent"] += 1
        except Exception as e:
            logger.warning(f"Failed to send to {client_id}: {e}")
            self._stats["errors"] += 1
    
    async def stream_response(
        self,
        client_id: str,
        query: str,
        chunks: List[str]
    ):
        """Стримит ответ по частям"""
        # Начало
        await self.send_to(client_id, EventType.MESSAGE_START.value, {
            "query": query,
            "total_chunks": len(chunks)
        })
        
        # Чанки
        for i, chunk in enumerate(chunks):
            await self.send_to(client_id, EventType.MESSAGE_CHUNK.value, {
                "chunk": chunk,
                "index": i,
                "total": len(chunks)
            })
            await asyncio.sleep(0.01)  # Небольшая задержка
        
        # Конец
        await self.send_to(client_id, EventType.MESSAGE_END.value, {
            "query": query,
            "chunks_sent": len(chunks)
        })
    
    def subscribe(self, client_id: str, event_type: str):
        """Подписывает клиента на тип событий"""
        if event_type not in self._event_subscriptions:
            self._event_subscriptions[event_type] = set()
        self._event_subscriptions[event_type].add(client_id)
    
    def unsubscribe(self, client_id: str, event_type: str):
        """Отписывает клиента от типа событий"""
        if event_type in self._event_subscriptions:
            self._event_subscriptions[event_type].discard(client_id)
    
    async def emit(self, event: str, data: Dict[str, Any]):
        """Отправляет событие подписчикам"""
        subscribers = self._event_subscriptions.get(event, set())
        
        tasks = []
        for client_id in list(subscribers):
            if client_id in self._connections:
                tasks.append(self.send_to(client_id, event, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def join_room(self, client_id: str, room: str):
        """Добавляет клиента в room"""
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(client_id)
    
    def leave_room(self, client_id: str, room: str):
        """Удаляет клиента из room"""
        if room in self._rooms:
            self._rooms[room].discard(client_id)
    
    def get_active_connections(self) -> int:
        """Возвращает количество активных соединений"""
        return len(self._connections)
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        return {
            "active_connections": len(self._connections),
            "total_connections": self._stats["total_connections"],
            "total_messages_sent": self._stats["total_messages_sent"],
            "total_broadcasts": self._stats["total_broadcasts"],
            "errors": self._stats["errors"],
            "rooms": {r: len(c) for r, c in self._rooms.items()}
        }


# Глобальный экземпляр
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Возвращает глобальный менеджер WebSocket"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager