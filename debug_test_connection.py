#!/usr/bin/env python3
"""
Тест OpenRouter провайдера с методом test_connection
"""

import sys
import os
import asyncio
import traceback

# Добавляем backend в путь
sys.path.insert(0, 'backend')

# Устанавливаем фейковый ключ для тестирования
os.environ['OPENROUTER_API_KEY'] = 'sk-or-v1-REPLACED1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'

async def test_test_connection():
    print("=== Тест OpenRouter test_connection ===")
    
    try:
        from llm.provider_manager import ProviderManager, OpenRouterProvider
        
        # 1. Проверка провайдера
        print("\n1. Проверка OpenRouter провайдера:")
        provider = OpenRouterProvider()
        print(f"Модель: {provider.model}")
        print(f"API Key: {'✓ Найден' if provider.api_key else '✗ Не найден'}")
        
        # 2. Проверка через test_connection
        print("\n2. Проверка через test_connection:")
        result = await provider.test_connection()
        print(f"Результат: {result}")
        print(f"Провайдер здоров: {provider.healthy}")
        
        # 3. Проверка через ProviderManager
        print("\n3. Проверка через ProviderManager:")
        mgr = ProviderManager()
        mgr.setup_from_env()
        p = mgr.providers.get('openrouter')
        print(f"Провайдер в менеджере: {'✓ Найден' if p else '✗ Не найден'}")
        if p:
            result = await p.test_connection()
            print(f"Тест через менеджер: {result}")
            print(f"Провайдер здоров: {p.healthy}")
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_test_connection())