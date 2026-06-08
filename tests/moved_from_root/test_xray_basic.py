#!/usr/bin/env python3
"""
🔬 БАЗОВЫЙ X-Ray ТЕСТ БЕЗ АВТОРИЗАЦИИ

Проверяет что backend работает без логина:
✅ WebSocket подключение
✅ Базовые API эндпоинты
✅ Система отвечает
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

async def test_basic_functionality():
    print(f"\n{Colors.BOLD}🔬 БАЗОВЫЙ X-Ray ТЕСТ (без авторизации){Colors.END}")
    print("=" * 60)
    
    results = {}
    
    # Тест 1: Проверка что backend запущен
    print_blue("Тест 1: Проверка доступности backend")
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        if response.status_code == 200:
            print_green("Backend доступен")
            results["backend_alive"] = True
        else:
            print_red(f"Backend недоступен: {response.status_code}")
            results["backend_alive"] = False
    except Exception as e:
        print_red(f"Backend недоступен: {e}")
        results["backend_alive"] = False
    
    # Тест 2: Проверка провайдеров
    print_blue("Тест 2: Проверка API провайдеров")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/providers", timeout=5)
        if response.status_code == 200:
            providers = response.json()
            print_green(f"Провайдеры доступны: {len(providers)}")
            results["providers_api"] = True
        else:
            print_red(f"Провайдеры недоступны: {response.status_code}")
            results["providers_api"] = False
    except Exception as e:
        print_red(f"Провайдеры недоступны: {e}")
        results["providers_api"] = False
    
    # Тест 3: Проверка health endpoint
    print_blue("Тест 3: Проверка health endpoint")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print_green("Health endpoint работает")
            results["health_api"] = True
        else:
            print_red(f"Health endpoint недоступен: {response.status_code}")
            results["health_api"] = False
    except Exception as e:
        print_red(f"Health endpoint недоступен: {e}")
        results["health_api"] = False
    
    # Тест 4: WebSocket подключение
    print_blue("Тест 4: WebSocket подключение")
    try:
        async with websockets.connect(WS_URL, ping_timeout=5, close_timeout=5) as websocket:
            print_green("WebSocket подключен")
            results["websocket_connect"] = True
            
            # Отправляем ping
            await websocket.send(json.dumps({"type": "ping"}))
            print_green("Ping отправлен")
            
            # Ждем ответ
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2)
                print_green(f"WebSocket ответ получен: {response}")
                results["websocket_response"] = True
            except asyncio.TimeoutError:
                print_yellow("WebSocket ответ не получен (таймаут)")
                results["websocket_response"] = False
                
    except Exception as e:
        print_red(f"WebSocket не подключен: {e}")
        results["websocket_connect"] = False
        results["websocket_response"] = False
    
    # Тест 5: Проверка метрик
    print_blue("Тест 5: Проверка метрик системы")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/metrics/system", timeout=5)
        if response.status_code == 200:
            print_green("Метрики системы доступны")
            results["metrics_system"] = True
        else:
            print_red(f"Метрики системы недоступны: {response.status_code}")
            results["metrics_system"] = False
    except Exception as e:
        print_red(f"Метрики системы недоступны: {e}")
        results["metrics_system"] = False
    
    # Результаты
    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ{Colors.END}")
    print("-" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{test_name.ljust(25)} {status}{Colors.END}")
    
    print("-" * 60)
    print(f"ИТОГО: {passed_tests} / {total_tests} тестов пройдено")
    
    if passed_tests == total_tests:
        print_green("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ - Система работает!")
    elif passed_tests >= total_tests * 0.7:
        print_yellow("⚠️  Большинство тестов пройдено")
    else:
        print_red("❌ ЕСТЬ СЕРЬЕЗНЫЕ ПРОБЛЕМЫ")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
