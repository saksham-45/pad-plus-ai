#!/usr/bin/env python3
"""
Детальная диагностика Render backend
"""

import requests
import json
import time
from datetime import datetime

def check_backend_health():
    """Проверка здоровья backend"""
    print("🔍 Проверка здоровья backend...")
    
    try:
        response = requests.get("https://padplus-ai-backend.onrender.com/health", timeout=10)
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ Backend здоров")
            return True
        else:
            print(f"❌ Backend не здоров: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки health: {e}")
        return False

def test_chat_endpoint_detailed():
    """Детальное тестирование chat endpoint"""
    print("\n💬 Детальное тестирование chat endpoint...")
    
    try:
        # Тестируем простой запрос
        payload = {
            "prompt": "Привет",
            "context": {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://padplus-ai-frontend.onrender.com"
        }
        
        response = requests.post(
            "https://padplus-ai-backend.onrender.com/api/v1/chat",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"Chat response: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Chat endpoint работает")
            return True
        else:
            print(f"❌ Chat endpoint ошибка: {response.text}")
            
            # Пытаемся распарсить JSON ошибки
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print("Не удалось распарсить JSON ошибки")
            
            return False
            
    except Exception as e:
        print(f"❌ Ошибка chat endpoint: {e}")
        return False

def test_other_endpoints():
    """Тестирование других эндпоинтов"""
    print("\n🧪 Тестирование других эндпоинтов...")
    
    endpoints = [
        "/api/v1/health",
        "/api/v1/anti-directive",
        "/api/v1/emotion/state",
        "/api/v1/memory/stats",
        "/api/v1/knowledge/stats"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"https://padplus-ai-backend.onrender.com{endpoint}", timeout=10)
            print(f"{endpoint}: {response.status_code}")
            if response.status_code != 200:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"{endpoint}: ❌ {e}")

def check_cors_headers():
    """Проверка CORS заголовков"""
    print("\n🌐 Проверка CORS заголовков...")
    
    try:
        response = requests.options(
            "https://padplus-ai-backend.onrender.com/api/v1/chat",
            headers={
                "Origin": "https://padplus-ai-frontend.onrender.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            },
            timeout=10
        )
        
        print(f"OPTIONS response: {response.status_code}")
        print(f"CORS headers: {dict(response.headers)}")
        
        # Проверяем наличие CORS заголовков
        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods", 
            "Access-Control-Allow-Headers"
        ]
        
        for header in cors_headers:
            if header in response.headers:
                print(f"✅ {header}: {response.headers[header]}")
            else:
                print(f"❌ Нет {header}")
                
    except Exception as e:
        print(f"❌ Ошибка проверки CORS: {e}")

def main():
    """Основная функция"""
    print("🚀 Детальная диагностика Render backend")
    print(f"Время: {datetime.now()}")
    print("=" * 60)
    
    # Проверяем health
    health_ok = check_backend_health()
    
    # Проверяем CORS
    check_cors_headers()
    
    # Тестируем другие эндпоинты
    test_other_endpoints()
    
    # Тестируем chat endpoint
    chat_ok = test_chat_endpoint_detailed()
    
    print("\n" + "=" * 60)
    print("📊 Результаты диагностики:")
    print(f"Health check: {'✅' if health_ok else '❌'}")
    print(f"Chat endpoint: {'✅' if chat_ok else '❌'}")
    
    if not health_ok or not chat_ok:
        print("\n⚠️  Обнаружены проблемы!")
        print("Нужна дополнительная диагностика через логи Render")
    else:
        print("\n✅ Все системы работают нормально!")

if __name__ == "__main__":
    main()