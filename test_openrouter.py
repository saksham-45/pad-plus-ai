#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы OpenRouter провайдера
"""

import asyncio
import sys
import os

# Добавляем путь к backend для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_openrouter():
    """Тестирует работу OpenRouter провайдера"""
    try:
        # Импортируем менеджер провайдеров
        from llm.provider_manager import get_provider_manager
        
        print("=== Тестирование OpenRouter провайдера ===")
        
        # Получаем менеджер провайдеров
        mgr = get_provider_manager()
        
        # Проверяем статус провайдеров
        status = mgr.get_status()
        print(f"Статус провайдеров: {status}")
        
        # Проверяем, есть ли активные провайдеры
        has_active = mgr.has_active_providers()
        print(f"Есть активные провайдеры: {has_active}")
        
        # Тестируем OpenRouter провайдер
        print("\n--- Тестирование OpenRouter ---")
        result = await mgr.test_provider('openrouter')
        print(f"Результат теста: {result}")
        
        # Если есть активные провайдеры, попробуем сгенерировать ответ
        if has_active:
            print("\n--- Генерация ответа ---")
            try:
                response = await mgr.generate("Привет, как дела?", "Тестовый контекст")
                print(f"Сгенерированный ответ: {response.text[:200]}...")
                print(f"Использованный провайдер: {response.provider}")
            except Exception as e:
                print(f"Ошибка при генерации: {e}")
        
        print("\n=== Тест завершён ===")
        
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Убедитесь, что вы находитесь в корне проекта и файлы backend доступны")
    except Exception as e:
        print(f"Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_openrouter())