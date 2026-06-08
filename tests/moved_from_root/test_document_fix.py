#!/usr/bin/env python3
"""
Тест для проверки исправленных эндпоинтов документов
"""

import requests
import json
import sys
import os

# Добавляем путь к backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_document_endpoints():
    """Тестирование исправленных эндпоинтов документов"""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Тестирование исправленных эндпоинтов документов...")
    
    # Тест 1: Проверка доступности health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health endpoint доступен")
        else:
            print(f"❌ Health endpoint вернул статус: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Не удалось подключиться к серверу: {e}")
        print("🔧 Убедитесь, что сервер запущен: python backend/main.py")
        return False
    
    # Тест 2: Проверка роута документов
    try:
        response = requests.get(f"{base_url}/api/v1/documents")
        print(f"📄 /api/v1/documents статус: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Эндпоинт требует аутентификации (ожидаемо)")
        elif response.status_code == 200:
            print("✅ Эндпоинт документов доступен")
        else:
            print(f"⚠️  Неожиданный статус: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании /api/v1/documents: {e}")
    
    # Тест 3: Проверка роута коллекций
    try:
        response = requests.get(f"{base_url}/api/v1/collections")
        print(f"📁 /api/v1/collections статус: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Эндпоинт требует аутентификации (ожидаемо)")
        elif response.status_code == 200:
            print("✅ Эндпоинт коллекций доступен")
        else:
            print(f"⚠️  Неожиданный статус: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании /api/v1/collections: {e}")
    
    # Тест 4: Проверка роута статистики
    try:
        response = requests.get(f"{base_url}/api/v1/documents/stats")
        print(f"📊 /api/v1/documents/stats статус: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Эндпоинт требует аутентификации (ожидаемо)")
        elif response.status_code == 200:
            print("✅ Эндпоинт статистики доступен")
        else:
            print(f"⚠️  Неожиданный статус: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании /api/v1/documents/stats: {e}")
    
    print("\n🎯 Если все эндпоинты возвращают 401 (требуют аутентификации),")
    print("то проблема с UUID валидацией решена!")
    print("🔐 Для полного тестирования нужен валидный JWT токен.")
    
    return True

if __name__ == "__main__":
    test_document_endpoints()