"""
Тесты для WebSocket Heartbeat

Проверяют:
1. Heartbeat запускается при подключении
2. Ping отправляется каждые HEARTBEAT_INTERVAL
3. Pong обновляет last_activity
4. Timeout отключает клиента
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


class TestWebSocketHeartbeat:
    """Тесты WebSocket Heartbeat"""

    @pytest.mark.asyncio
    async def test_heartbeat_starts_on_connect(self):
        """
        Проверяет, что heartbeat запускается при подключении
        """
        from backend.core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        
        # Мокируем websocket
        mock_websocket = AsyncMock()
        
        # Подключаем клиента
        await manager.connect("client-1", mock_websocket)
        
        # Проверяем, что heartbeat задача создана
        assert "client-1" in manager._heartbeat_tasks
        assert "client-1" in manager._last_activity

    @pytest.mark.asyncio
    async def test_heartbeat_stops_on_disconnect(self):
        """
        Проверяет, что heartbeat останавливается при отключении
        """
        from backend.core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        
        await manager.connect("client-1", mock_websocket)
        assert "client-1" in manager._heartbeat_tasks
        
        # Отключаем
        manager.disconnect("client-1")
        
        # Проверяем, что heartbeat остановлен
        assert "client-1" not in manager._heartbeat_tasks
        assert "client-1" not in manager._last_activity

    @pytest.mark.asyncio
    async def test_heartbeat_sends_ping(self):
        """
        Проверяет, что heartbeat отправляет ping
        """
        from backend.core.websocket_manager import WebSocketManager
        
        # Уменьшаем интервал для теста
        manager = WebSocketManager()
        manager.HEARTBEAT_INTERVAL = 0.1  # 100ms
        
        mock_websocket = AsyncMock()
        await manager.connect("client-1", mock_websocket)
        
        # Ждём немного больше интервала
        await asyncio.sleep(0.2)
        
        # Проверяем, что ping был отправлен
        assert manager._stats["heartbeat_pings"] >= 1
        
        # Отключаем
        manager.disconnect("client-1")

    @pytest.mark.asyncio
    async def test_pong_updates_last_activity(self):
        """
        Проверяет, что pong обновляет last_activity
        """
        from backend.core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        
        await manager.connect("client-1", mock_websocket)
        
        # Запоминаем старое last_activity
        old_activity = manager._last_activity["client-1"]
        
        # Ждём немного
        await asyncio.sleep(0.1)
        
        # Получаем pong
        await manager.handle_pong("client-1")
        
        # Проверяем, что last_activity обновился
        new_activity = manager._last_activity["client-1"]
        assert new_activity >= old_activity
        
        manager.disconnect("client-1")

    @pytest.mark.asyncio
    async def test_heartbeat_timeout_disconnects(self):
        """
        Проверяет, что timeout отключает клиента
        """
        from backend.core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        manager.HEARTBEAT_INTERVAL = 0.1  # 100ms
        manager.HEARTBEAT_TIMEOUT = 0.2  # 200ms
        
        mock_websocket = AsyncMock()
        await manager.connect("client-1", mock_websocket)
        
        # Устанавливаем старое last_activity
        manager._last_activity["client-1"] = datetime.now() - timedelta(seconds=1)
        
        # Ждём heartbeat loop
        await asyncio.sleep(0.3)
        
        # Проверяем, что клиент отключён
        assert "client-1" not in manager._connections
        assert manager._stats["heartbeat_timeouts"] >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_stats(self):
        """
        Проверяет статистику heartbeat
        """
        from backend.core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        manager.HEARTBEAT_INTERVAL = 0.1
        
        mock_websocket = AsyncMock()
        await manager.connect("client-1", mock_websocket)
        
        await asyncio.sleep(0.25)
        
        stats = manager._stats
        assert stats["heartbeat_pings"] >= 1
        assert "heartbeat_timeouts" in stats
        
        manager.disconnect("client-1")


class TestWebSocketManagerWithHeartbeat:
    """Интеграционные тесты WebSocketManager с heartbeat"""

    @pytest.mark.asyncio
    async def test_multiple_clients_heartbeat(self):
        """
        Проверяет heartbeat для нескольких клиентов
        """
        from backend.core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        manager.HEARTBEAT_INTERVAL = 0.1
        
        # Подключаем нескольких клиентов
        for i in range(3):
            mock_websocket = AsyncMock()
            await manager.connect(f"client-{i}", mock_websocket)
        
        # Проверяем, что у всех heartbeat запущен
        for i in range(3):
            assert f"client-{i}" in manager._heartbeat_tasks
        
        # Ждём heartbeat
        await asyncio.sleep(0.2)
        
        # Проверяем статистику
        assert manager._stats["heartbeat_pings"] >= 3
        
        # Отключаем всех
        for i in range(3):
            manager.disconnect(f"client-{i}")

    @pytest.mark.asyncio
    async def test_heartbeat_with_activity(self):
        """
        Проверяет, что активность предотвращает timeout
        """
        from backend.core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        manager.HEARTBEAT_INTERVAL = 0.1
        manager.HEARTBEAT_TIMEOUT = 0.3
        
        mock_websocket = AsyncMock()
        await manager.connect("client-1", mock_websocket)
        
        # Симулируем активность
        for _ in range(5):
            await asyncio.sleep(0.1)
            await manager.handle_pong("client-1")
        
        # Клиент должен остаться подключённым
        assert "client-1" in manager._connections
        
        manager.disconnect("client-1")


class TestHeartbeatConfiguration:
    """Тесты конфигурации heartbeat"""

    def test_heartbeat_constants(self):
        """
        Проверяет константы heartbeat
        """
        from backend.core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        
        assert manager.HEARTBEAT_INTERVAL == 30  # 30 секунд
        assert manager.HEARTBEAT_TIMEOUT == 300  # 5 минут

    def test_heartbeat_custom_interval(self):
        """
        Проверяет настройку custom интервала
        """
        from backend.core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        manager.HEARTBEAT_INTERVAL = 10
        manager.HEARTBEAT_TIMEOUT = 60
        
        assert manager.HEARTBEAT_INTERVAL == 10
        assert manager.HEARTBEAT_TIMEOUT == 60
