#!/usr/bin/env python3
"""
Скрипт для мониторинга статуса Render backend
"""

import requests
import time


def check_backend_status():
    """Проверка статуса backend"""
    try:
        response = requests.get(
            "https://padplus-ai-backend.onrender.com/health", 
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False


def check_chat_endpoint():
    """Проверка chat endpoint"""
    try:
        payload = {"prompt": "Привет", "context": {}}
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            "https://padplus-ai-backend.onrender.com/api/v1/chat",
            json=payload,
            headers=headers,
            timeout=30
        )
        return response.status_code == 200
    except Exception:
        return False


def main():
    """Мониторинг статуса"""
    print("🔍 Мониторинг статуса Render backend...")
    print("Ожидаем пересборку после последнего коммита...")
    
    start_time = time.time()
    max_wait = 300  # 5 минут максимум ожидания
    
    while time.time() - start_time < max_wait:
        print(f"\n⏱️  Прошло: {int(time.time() - start_time)}s")
        
        # Проверяем health
        health_ok = check_backend_status()
        print(f"Health: {'✅' if health_ok else '❌'}")
        
        if health_ok:
            # Проверяем chat endpoint
            chat_ok = check_chat_endpoint()
            print(f"Chat: {'✅' if chat_ok else '❌'}")
            
            if chat_ok:
                print("\n🎉 Backend пересобран и работает!")
                print("✅ Все системы функционируют нормально!")
                return True
            else:
                print("⚠️  Backend работает, но chat endpoint еще не готов")
        else:
            print("⚠️  Backend еще пересобирается...")
        
        print("⏳ Ждем 30 секунд...")
        time.sleep(30)
    
    print("\n⏰ Превышено время ожидания пересборки")
    print("Проверьте статус вручную через несколько минут")
    return False


if __name__ == "__main__":
    main()