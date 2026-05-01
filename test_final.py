#!/usr/bin/env python3
"""
Финальный тест для проверки OpenRouter
"""

import asyncio
import sys
import os
import importlib

# Добавляем путь к backend для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_final():
    """Финальный тест"""
    try:
        # Перезагружаем модуль
        if 'llm.provider_manager' in sys.modules:
            importlib.reload(sys.modules['llm.provider_manager'])
        
        from llm.provider_manager import get_provider_manager
        
        print("=== Финальный тест OpenRouter ===")
        
        # Получаем менеджер провайдеров
        mgr = get_provider_manager()
        
        # Перезагружаем провайдеров
        mgr.reload_providers()
        
        # Проверяем статус
        status = mgr.get_status()
        print(f"Статус провайдеров: {status}")
        
        # Получаем OpenRouter провайдер
        provider = mgr.providers.get('openrouter')
        if provider:
            print(f"OpenRouter провайдер найден")
            print(f"Model: {provider.model}")
            
            # Сделаем тестовый запрос
            print("\n--- Тестовый запрос ---")
            try:
                response = await provider.generate("Привет", "Тестовый запрос")
                print(f"✅ Успех! Ответ: {response.text[:50]}...")
                print(f"Провайдер: {response.provider}")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
        else:
            print("OpenRouter провайдер не найден")
        
        print("\n=== Тест завершён ===")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_final())