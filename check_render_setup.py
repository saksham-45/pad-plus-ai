#!/usr/bin/env python3
"""
Скрипт для проверки настроек OpenRouter на Render.com
"""

import sys
import os
import asyncio
import traceback
import requests

# Добавляем backend в путь
sys.path.insert(0, 'backend')

async def check_render_setup():
    """Проверка настроек для Render.com"""
    print("=== Проверка настроек OpenRouter для Render.com ===")
    
    # Проверка 1: Переменные окружения
    print("\n1. Проверка переменных окружения:")
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    openrouter_enabled = os.getenv('OPENROUTER_ENABLED', 'false').lower() == 'true'
    openrouter_model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-3.5-turbo')
    
    print(f"   OPENROUTER_API_KEY: {'✓ Найден' if openrouter_key else '✗ Не найден'}")
    print(f"   OPENROUTER_ENABLED: {'✓ Включен' if openrouter_enabled else '✗ Отключен'}")
    print(f"   OPENROUTER_MODEL: {openrouter_model}")
    
    # Проверка 2: Backend провайдеры
    print("\n2. Проверка backend провайдеров:")
    try:
        from llm.provider_manager import get_provider_manager
        
        manager = get_provider_manager()
        providers = manager.get_providers_status()
        
        openrouter_status = providers.get('openrouter', {})
        print(f"   OpenRouter enabled: {'✓' if openrouter_status.get('enabled') else '✗'}")
        print(f"   OpenRouter has_key: {'✓' if openrouter_status.get('has_key') else '✗'}")
        print(f"   OpenRouter healthy: {'✓' if openrouter_status.get('healthy') else '✗'}")
        
    except Exception as e:
        print(f"   ✗ Ошибка проверки провайдеров: {e}")
    
    # Проверка 3: API эндпоинты
    print("\n3. Проверка API эндпоинтов:")
    try:
        from api.routes import llm_providers, llm_models, llm_test_provider
        
        # Проверка получения провайдеров
        providers_result = await llm_providers()
        print(f"   GET /llm/providers: {'✓' if 'providers' in providers_result else '✗'}")
        
        # Проверка получения моделей
        models_result = await llm_models("openrouter")
        print(f"   GET /llm/models: {'✓' if 'models' in models_result else '✗'}")
        
        # Проверка тестирования провайдера
        test_result = await llm_test_provider("openrouter")
        print(f"   POST /llm/test/openrouter: {'✓' if 'provider' in test_result else '✗'}")
        
    except Exception as e:
        print(f"   ✗ Ошибка проверки API: {e}")
    
    # Проверка 4: Frontend интеграция
    print("\n4. Проверка frontend интеграции:")
    try:
        # Проверка существования frontend файлов
        frontend_files = [
            'frontend/src/Settings.jsx',
            'frontend/src/Settings.css'
        ]
        
        for file_path in frontend_files:
            if os.path.exists(file_path):
                print(f"   {file_path}: ✓ Найден")
            else:
                print(f"   {file_path}: ✗ Не найден")
        
    except Exception as e:
        print(f"   ✗ Ошибка проверки frontend: {e}")
    
    # Проверка 5: Docker и Render конфигурация
    print("\n5. Проверка Docker и Render конфигурации:")
    try:
        config_files = [
            'Dockerfile',
            'frontend/Dockerfile',
            'render.yaml'
        ]
        
        for file_path in config_files:
            if os.path.exists(file_path):
                print(f"   {file_path}: ✓ Найден")
            else:
                print(f"   {file_path}: ✗ Не найден")
        
    except Exception as e:
        print(f"   ✗ Ошибка проверки конфигурации: {e}")
    
    print("\n=== Рекомендации для Render.com ===")
    print("1. Добавьте в Environment Variables на Render:")
    print("   OPENROUTER_API_KEY=ваш_ключ")
    print("   OPENROUTER_ENABLED=true")
    print("   OPENROUTER_MODEL=openrouter/free")
    print("2. Перезапустите сервис после добавления переменных")
    print("3. Проверьте логи Render на наличие ошибок")
    print("4. Протестируйте через Settings → LLM Providers")

if __name__ == "__main__":
    asyncio.run(check_render_setup())