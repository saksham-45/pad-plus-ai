#!/usr/bin/env python3
"""
Тест для проверки модели в провайдере
"""

import asyncio
import sys
import os

# Добавляем путь к backend для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def debug_provider():
    """Проверяем модель в провайдере"""
    try:
        from llm.provider_manager import get_provider_manager
        
        print("=== Проверка модели в провайдере ===")
        
        # Получаем менеджер провайдеров
        mgr = get_provider_manager()
        
        # Перезагружаем провайдеров
        mgr.reload_providers()
        
        # Получаем OpenRouter провайдер
        provider = mgr.providers.get('openrouter')
        if provider:
            print(f"OpenRouter провайдер найден")
            print(f"API Key: {provider.api_key[:10]}..." if provider.api_key else "None")
            print(f"Enabled: {provider.enabled}")
            print(f"Model: {provider.model}")
            print(f"Healthy: {provider.healthy}")
            
            # Проверим, какая модель будет использоваться
            actual_model = provider.model
            if actual_model.lower() == "free":
                actual_model = "openrouter/free"
            
            print(f"Фактическая модель: {actual_model}")
            
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
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_provider())