#!/usr/bin/env python3
"""
Тест API OpenRouter провайдера
"""

import sys
import os
import asyncio
import traceback

# Добавляем backend в путь
sys.path.insert(0, 'backend')

# Устанавливаем фейковый ключ для тестирования
os.environ['OPENROUTER_API_KEY'] = 'sk-or-v1-REPLACED1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'

async def test_api():
    print("=== Тест API OpenRouter ===")
    
    try:
        # Тестируем через API маршруты
        from api.routes import llm_test_provider
        
        # Тестируем системный провайдер
        print("\n1. Тест системного провайдера:")
        result = await llm_test_provider("openrouter")
        print(f"Результат: {result}")
        
        # Тестируем получение провайдеров
        print("\n2. Получение списка провайдеров:")
        from api.routes import llm_providers
        providers = await llm_providers()
        print(f"Провайдеры: {providers}")
        
        # Тестируем получение моделей
        print("\n3. Получение моделей:")
        from api.routes import llm_models
        models = await llm_models("openrouter")
        print(f"Модели: {models}")
        
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())