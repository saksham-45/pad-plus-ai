#!/usr/bin/env python3
"""
Скрипт для ожидания пересборки Render backend
"""

import requests
import time


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
    """Мониторинг пересборки"""
    print("⏳ Ожидание пересборки Render backend...")
    print("Проверяем, когда chat endpoint начнет работать...")
    
    start_time = time.time()
    max_wait = 600  # 10 минут максимум ожидания
    
    while time.time() - start_time < max_wait:
        print(f"\n⏱️  Прошло: {int(time.time() - start_time)}s")
        
        # Проверяем chat endpoint
        chat_ok = check_chat_endpoint()
        print(f"Chat: {'✅' if chat_ok else '❌'}")
        
        if chat_ok:
            print("\n🎉 Backend пересобран и работает!")
            print("✅ Chat endpoint теперь функционирует!")
            return True
        else:
            print("⚠️  Backend еще пересобирается...")
        
        print("⏳ Ждем 60 секунд...")
        time.sleep(60)
    
    print("\n⏰ Превышено время ожидания пересборки")
    print("Render может быть перегружен или есть другие проблемы")
    return False


if __name__ == "__main__":
    main()