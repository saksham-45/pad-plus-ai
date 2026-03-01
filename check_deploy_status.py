#!/usr/bin/env python3
"""
Скрипт для проверки статуса деплоя на Render
"""

import requests


def check_deploy_status():
    """Проверка статуса деплоя"""
    print("🔍 Проверка статуса деплоя на Render...")
    
    # Проверяем health
    try:
        response = requests.get(
            "https://padplus-ai-backend.onrender.com/health", 
            timeout=10
        )
        print(f"Health: {response.status_code}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Проверяем chat endpoint
    try:
        payload = {"prompt": "Привет", "context": {}}
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            "https://padplus-ai-backend.onrender.com/api/v1/chat",
            json=payload,
            headers=headers,
            timeout=30
        )
        print(f"Chat: {response.status_code}")
        if response.status_code == 500:
            try:
                error_data = response.json()
                print(f"Error: {error_data.get('error', 'Unknown error')}")
            except Exception:
                pass
    except Exception as e:
        print(f"Chat check failed: {e}")
    
    print("\n💡 Рекомендации:")
    print("1. Залогиньтесь в Render и проверьте статус деплоя")
    print("2. Если пересборка не запустилась - перезапустите сервис вручную")
    print("3. Проверьте логи Render на предмет ошибок")
    print("4. Убедитесь, что последний коммит a21ebea был применен")


if __name__ == "__main__":
    check_deploy_status()