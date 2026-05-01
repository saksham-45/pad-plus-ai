#!/usr/bin/env python3
"""
Детальный тест для отладки OpenRouter провайдера
"""

import asyncio
import sys
import os
import httpx
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Добавляем путь к backend для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def debug_openrouter():
    """Детальная отладка OpenRouter провайдера"""
    try:
        # Импортируем менеджер провайдеров
        from llm.provider_manager import get_provider_manager, OpenRouterProvider
        
        print("=== Детальная отладка OpenRouter ===")
        
        # Проверяем переменные окружения
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openrouter_enabled = os.getenv("OPENROUTER_ENABLED")
        
        print(f"OPENROUTER_API_KEY: {openrouter_key}")
        print(f"OPENROUTER_ENABLED: {openrouter_enabled}")
        
        # Создаем провайдер вручную для отладки
        if openrouter_key and openrouter_enabled == "true":
            provider = OpenRouterProvider(openrouter_key, True, "openai/gpt-3.5-turbo")
            
            print(f"\n--- Провайдер создан ---")
            print(f"API Key: {provider.api_key[:10]}..." if provider.api_key else "None")
            print(f"Enabled: {provider.enabled}")
            print(f"Model: {provider.model}")
            
            # Проверяем заголовки
            headers = {
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://padplus-ai.onrender.com",
                "X-Title": "PAD+ AI"
            }
            
            print(f"\n--- Заголовки запроса ---")
            for key, value in headers.items():
                print(f"{key}: {value}")
            
            # Делаем тестовый запрос вручную
            print(f"\n--- Тестовый запрос к OpenRouter ---")
            data = {
                "model": provider.model,
                "messages": [
                    {"role": "system", "content": "Тестовый запрос"},
                    {"role": "user", "content": "Привет"}
                ]
            }
            
            print(f"Data: {data}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"Success! Response: {result}")
                else:
                    print(f"Error: {response.status_code}")
        
        else:
            print("OpenRouter не настроен или отключен")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_openrouter())