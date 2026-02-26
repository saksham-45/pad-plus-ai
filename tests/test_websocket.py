"""
Тестирование WebSocket API — NeuroMind AI
"""

import sys
import os
import asyncio
import json
from typing import Dict, Any
from websockets import connect, WebSocketClientProtocol
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestWebSocketAPI:
    """Тестирование WebSocket API"""
    
    async def test_websocket_connection(self):
        """Тест подключения к WebSocket"""
        uri = "ws://localhost:8000/ws"
        
        async with connect(uri) as websocket:
            # Отправляем ping
            await websocket.send(json.dumps({
                "type": "ping"
            }))
            
            # Получаем ответ
            response = await websocket.recv()
            response_data = json.loads(response)
            
            assert response_data["type"] == "pong"
            print("  ✅ WebSocket: ping/pong работает")
    
    async def test_websocket_subscribe(self):
        """Тест подписки на каналы"""
        uri = "ws://localhost:8000/ws"
        
        async with connect(uri) as websocket:
            # Подписываемся на эмоции и память
            await websocket.send(json.dumps({
                "type": "subscribe",
                "channels": ["emotion", "memory"]
            }))
            
            # Получаем подтверждение
            response = await websocket.recv()
            response_data = json.loads(response)
            
            assert response_data["type"] == "subscribed"
            assert "emotion" in response_data["channels"]
            assert "memory" in response_data["channels"]
            print("  ✅ WebSocket: подписка на каналы работает")
    
    async def test_websocket_chat(self):
        """Тест чата через WebSocket"""
        uri = "ws://localhost:8000/ws"
        
        async with connect(uri) as websocket:
            # Отправляем сообщение в чат
            await websocket.send(json.dumps({
                "type": "chat",
                "prompt": "Привет, как дела?",
                "user_id": "test",
                "session_id": "test"
            }))
            
            # Получаем ответ
            response = await websocket.recv()
            response_data = json.loads(response)
            
            assert response_data["type"] == "chat_response"
            assert "response" in response_data
            assert "confidence" in response_data
            print("  ✅ WebSocket: чат работает")
    
    async def test_websocket_mind_state(self):
        """Тест получения состояния системы"""
        uri = "ws://localhost:8000/ws"
        
        async with connect(uri) as websocket:
            # Запрашиваем состояние системы
            await websocket.send(json.dumps({
                "type": "get_state"
            }))
            
            # Получаем ответ
            response = await websocket.recv()
            response_data = json.loads(response)
            
            assert response_data["type"] == "mind_state"
            assert "state" in response_data
            assert "emotion" in response_data["state"]
            assert "memory" in response_data["state"]
            print("  ✅ WebSocket: mind state работает")
    
    async def test_websocket_error_handling(self):
        """Тест обработки ошибок"""
        uri = "ws://localhost:8000/ws"
        
        async with connect(uri) as websocket:
            # Отправляем невалидное сообщение
            await websocket.send(json.dumps({
                "type": "invalid_type"
            }))
            
            # Получаем ошибку
            response = await websocket.recv()
            response_data = json.loads(response)
            
            assert response_data["type"] == "error"
            assert "message" in response_data
            print("  ✅ WebSocket: обработка ошибок работает")


def run_websocket_tests():
    """Запуск всех тестов WebSocket"""
    print("\n" + "="*60)
    print("🌐 ТЕСТИРОВАНИЕ WEBSOCKET API")
    print("="*60)
    
    tests = TestWebSocketAPI()
    results = []
    
    # Запускаем все тесты
    asyncio.run(tests.test_websocket_connection())
    asyncio.run(tests.test_websocket_subscribe())
    asyncio.run(tests.test_websocket_chat())
    asyncio.run(tests.test_websocket_mind_state())
    asyncio.run(tests.test_websocket_error_handling())
    
    print("="*60)
    print("✅ WebSocket API: ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*60)


if __name__ == "__main__":
    run_websocket_tests()