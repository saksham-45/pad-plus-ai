#!/usr/bin/env python3
"""
Тест для проверки, какая модель используется в OpenRouterProvider
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь к backend для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def debug_model():
    """Проверяем, какая модель используется"""
    try:
        from llm.provider_manager import OpenRouterProvider
        
        print("=== Проверка модели OpenRouter ===")
        
        # Проверяем переменные окружения
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_enabled = os.getenv("OPENROUTER_ENABLED")
        
        print(f"OPENROUTER_API_KEY: {openrouter_key}")
        print(f"OPENROUTER_ENABLED: {openrouter_enabled}")
        
        if openrouter_key and openrouter_enabled == "true":
            # Создаем провайдер с разными моделями
            models_to_test = [
                "openrouter/free",
                "openai/gpt-3.5-turbo", 
                "anthropic/claude-3-sonnet",
                "google/gemini-pro"
            ]
            
            for model in models_to_test:
                print(f"\n--- Тестирование модели: {model} ---")
                try:
                    provider = OpenRouterProvider(openrouter_key, True, model)
                    print(f"Провайдер создан с моделью: {provider.model}")
                    
                    # Проверим, какая модель будет использоваться
                    actual_model = provider.model
                    if actual_model.lower() == "free":
                        actual_model = "openrouter/free"
                    
                    print(f"Фактическая модель: {actual_model}")
                    
                    # Сделаем тестовый запрос
                    response = await provider.generate("Привет", "Тестовый запрос")
                    print(f"✅ Успех! Ответ: {response.text[:50]}...")
                    print(f"Провайдер: {response.provider}")
                    break
                    
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
                    continue
            
        else:
            print("OpenRouter не настроен или отключен")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_model())