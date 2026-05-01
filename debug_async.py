#!/usr/bin/env python3
"""
Асинхронная диагностика OpenRouter провайдера
"""

import sys
import os
import asyncio
import traceback

# Добавляем backend в путь
sys.path.insert(0, 'backend')

async def test_async():
    print("=== Асинхронная диагностика OpenRouter ===")
    
    try:
        # 1. Проверка переменных окружения
        print("\n1. Проверка переменных окружения:")
        openrouter_key = os.getenv('OPENROUTER_API_KEY')
        print(f"OPENROUTER_API_KEY: {'✓ Найден' if openrouter_key else '✗ Не найден'}")
        if openrouter_key:
            print(f"Длина ключа: {len(openrouter_key)}")
            print(f"Первые 10 символов: {openrouter_key[:10]}...")
        
        # 2. Проверка загрузки модулей
        print("\n2. Проверка загрузки модулей:")
        try:
            from llm.provider_manager import ProviderManager, OpenRouterProvider
            print("✓ Модули импортированы")
        except Exception as e:
            print(f"✗ Ошибка импорта: {e}")
            return
        
        # 3. Создание провайдера
        print("\n3. Создание OpenRouter провайдера:")
        try:
            provider = OpenRouterProvider()
            print("✓ OpenRouterProvider создан")
            print(f"Модель по умолчанию: {provider.model}")
            print(f"API URL: {provider.API_URL}")
            print(f"API Key: {'✓ Найден' if provider.api_key else '✗ Не найден'}")
        except Exception as e:
            print(f"✗ Ошибка создания провайдера: {e}")
            traceback.print_exc()
            return
        
        # 4. Проверка аутентификации
        print("\n4. Проверка аутентификации:")
        try:
            result = await provider.check_health()
            print(f"Результат теста: {result}")
            print(f"Провайдер здоров: {provider.healthy}")
        except Exception as e:
            print(f"✗ Ошибка тестирования: {e}")
            traceback.print_exc()
        
        # 5. Проверка через ProviderManager
        print("\n5. Проверка через ProviderManager:")
        try:
            mgr = ProviderManager()
            mgr.setup_from_env()
            p = mgr.providers.get('openrouter')
            print(f"Провайдер в менеджере: {'✓ Найден' if p else '✗ Не найден'}")
            if p:
                print(f"Модель: {p.model}")
                print(f"API URL: {p.API_URL}")
                
                # Тест через менеджер
                result = await p.check_health()
                print(f"Тест через менеджер: {result}")
                print(f"Провайдер здоров: {p.healthy}")
        except Exception as e:
            print(f"✗ Ошибка через ProviderManager: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"✗ Критическая ошибка: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_async())