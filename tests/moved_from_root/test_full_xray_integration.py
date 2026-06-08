#!/usr/bin/env python3
"""
✅ ПОЛНЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ ВСЕЙ СИСТЕМЫ

Проверяет реальную работу:
✅ WebSocket подключение X-Ray
✅ Отправка запроса в чат
✅ Получение ответа
✅ Приход X-Ray метрик
✅ Сохранение истории чата
✅ Работа всех модулей

Запуск: python test_full_xray_integration.py
"""

import asyncio
import json
import requests
import websockets
import time
from datetime import datetime

# Конфигурация
BACKEND_URL = "http://localhost:8080"
WS_URL = "ws://localhost:8080/ws"
TEST_USER_EMAIL = "test@test.com"
TEST_USER_PASSWORD = "test123456"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_green(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_red(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_yellow(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_blue(text):
    print(f"{Colors.BLUE}🔍 {text}{Colors.END}")

async def test_full_integration():
    print(f"\n{Colors.BOLD}🚀 ПОЛНЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ X-Ray{Colors.END}")
    print("="*60 + "\n")

    results = {
        "websocket_connect": False,
        "websocket_subscribe": False,
        "xray_metrics_received": False,
        "chat_request_success": False,
        "history_saved": False,
        "total_tests": 5,
        "passed": 0
    }

    # === ТЕСТ 1: ПОДКЛЮЧЕНИЕ К WEBSOCKET X-RAY ===
    print_blue("Тест 1: Подключение к WebSocket X-Ray")
    
    try:
        async with websockets.connect(WS_URL, open_timeout=5) as websocket:
            print_green("WebSocket подключен")
            results["websocket_connect"] = True
            results["passed"] += 1

            # Отправляем подписку
            subscribe_msg = {
                "type": "subscribe",
                "channels": ["trace", "thought", "pipeline", "emotion", "decision", "all"]
            }
            
            await websocket.send(json.dumps(subscribe_msg))
            print_green("Отправлен запрос на подписку")

            # Ожидаем подтверждения
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            msg = json.loads(response)
            
            if msg.get("type") in ["subscribed", "welcome"]:
                print_green("Подписка на каналы подтверждена")
                results["websocket_subscribe"] = True
                results["passed"] += 1

            # === ТЕСТ 2: ОТПРАВКА ЗАПРОСА В ЧАТ ===
            print("\n" + "="*60)
            print_blue("Тест 2: Отправка запроса в чат")

            test_message = "что такое python? ответь коротко"
            
            print(f"Отправляем запрос: {test_message}")

            # Отправляем запрос в чат
            chat_response = requests.post(
                f"{BACKEND_URL}/api/v1/chat",
                json={
                    "message": test_message,
                    "key_id": "d5921032-198a-4261-9c47-27f1e3452680"
                },
                headers={
                    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QHRlc3QuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
                }
            )

            if chat_response.status_code == 200:
                data = chat_response.json()
                print_green(f"Ответ получен, длина: {len(data.get('text', ''))} символов")
                print(f"Ответ: {data.get('text', '')[:150]}...")
                results["chat_request_success"] = True
                results["passed"] += 1
            else:
                print_red(f"Ошибка чата: {chat_response.status_code}")
                print(chat_response.text)

            # === ТЕСТ 3: ПОЛУЧЕНИЕ X-RAY МЕТРИК ===
            print("\n" + "="*60)
            print_blue("Тест 3: Получение X-Ray метрик")

            received_events = {
                "trace_event": 0,
                "thought": 0,
                "pipeline_update": 0,
                "emotion_update": 0,
                "decision": 0
            }

            start_time = time.time()
            timeout = 15

            print("Ожидаем метрики...")
            
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1)
                    event = json.loads(message)
                    event_type = event.get("type")
                    
                    if event_type in received_events:
                        received_events[event_type] += 1
                        print(f"  ➕ Получено событие: {event_type}")

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print_red(f"Ошибка получения события: {e}")
                    break

            total_events = sum(received_events.values())
            if total_events > 0:
                print_green(f"Получено {total_events} X-Ray событий")
                for event_type, count in received_events.items():
                    if count > 0:
                        print(f"  ✅ {event_type}: {count}")
                results["xray_metrics_received"] = True
                results["passed"] += 1
            else:
                print_red("X-Ray метрики не приходят")

            await websocket.close()

    except Exception as e:
        print_red(f"WebSocket ошибка: {e}")

    # === ТЕСТ 4: ПРОВЕРКА СОХРАНЕНИЯ ИСТОРИИ ===
    print("\n" + "="*60)
    print_blue("Тест 4: Проверка сохранения истории чата")

    try:
        history_response = requests.get(
            f"{BACKEND_URL}/api/v1/dialogs",
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QHRlc3QuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
            }
        )

        if history_response.status_code == 200:
            data = history_response.json()
            dialogs_count = len(data.get('data', []))
            print_green(f"В истории {dialogs_count} диалогов")
            
            if dialogs_count > 0:
                results["history_saved"] = True
                results["passed"] += 1
        else:
            print_red(f"Ошибка истории: {history_response.status_code}")

    except Exception as e:
        print_red(f"Ошибка проверки истории: {e}")

    # === ИТОГ ===
    print("\n" + "="*60)
    print(f"{Colors.BOLD}📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ{Colors.END}")
    print("-"*60)

    for test_name, passed in results.items():
        if test_name in ["total_tests", "passed"]:
            continue
        
        status = f"{Colors.GREEN}PASS{Colors.END}" if passed else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {test_name:<30} {status}")

    print("\n" + "-"*60)
    print(f"{Colors.BOLD}ИТОГО: {results['passed']} / {results['total_tests']} тестов пройдено{Colors.END}")

    if results['passed'] == results['total_tests']:
        print(f"\n{Colors.GREEN}✅ ВСЯ СИСТЕМА РАБОТАЕТ КОРРЕКТНО!{Colors.END}")
        print("✅ WebSocket X-Ray работает")
        print("✅ Метрики приходят")
        print("✅ Чат отвечает")
        print("✅ История сохраняется")
    else:
        print(f"\n{Colors.RED}❌ ЕСТЬ ПРОБЛЕМЫ{Colors.END}")

    return results

if __name__ == "__main__":
    asyncio.run(test_full_integration())