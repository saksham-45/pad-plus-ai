#!/usr/bin/env python3
"""
Скрипт для проверки логов Render и диагностики 500 ошибки
"""

import requests
from datetime import datetime


def check_backend_health():
    """Проверка здоровья backend"""
    print("🔍 Проверка здоровья backend...")
    
    try:
        # Проверяем health endpoint
        response = requests.get(
            "https://padplus-ai-backend.onrender.com/health", 
            timeout=10
        )
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


def test_chat_endpoint():
    """Тестирование chat endpoint"""
    print("\n💬 Тестирование chat endpoint...")
    
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
            return False
            
    except Exception as e:
        print(f"❌ Ошибка chat endpoint: {e}")
        return False


def check_cors_headers():
    """Проверка CORS заголовков"""
    print("\n🌐 Проверка CORS заголовков...")
    
    try:
        # Делаем OPTIONS запрос для проверки CORS
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
    print("🚀 Диагностика Render backend")
    print(f"Время: {datetime.now()}")
    print("=" * 50)
    
    # Проверяем health
    health_ok = check_backend_health()
    
    # Проверяем CORS
    check_cors_headers()
    
    # Тестируем chat endpoint
    chat_ok = test_chat_endpoint()
    
    print("\n" + "=" * 50)
    print("📊 Результаты диагностики:")
    print(f"Health check: {'✅' if health_ok else '❌'}")
    print(f"Chat endpoint: {'✅' if chat_ok else '❌'}")
    
    if not health_ok or not chat_ok:
        print("\n⚠️  Обнаружены проблемы! Нужна дополнительная диагностика.")
    else:
        print("\n✅ Все системы работают нормально!")


if __name__ == "__main__":
    main()