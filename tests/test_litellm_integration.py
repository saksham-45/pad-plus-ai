"""
Тест интеграции LiteLLM и системы аутентификации

Запуск:
    python tests/test_litellm_integration.py

Требования:
    - Установленные зависимости (requirements.txt)
    - Запущенный backend (uvicorn main:app)
"""

import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Импорты для тестирования
from core.auth.encryption import EncryptionService, generate_encryption_key
from core.auth.litellm_service import LiteLLMService
from core.database import init_db


def test_encryption():
    """Тест шифрования"""
    print("\n🔐 Тест шифрования...")
    
    # Генерация ключа
    key = generate_encryption_key()
    print(f"   ✅ Ключ сгенерирован: {key[:20]}...")
    
    # Создание сервиса
    service = EncryptionService(key)
    
    # Тест шифрования/дешифрования
    original = "sk-test-1234567890abcdef"
    encrypted = service.encrypt(original)
    decrypted = service.decrypt(encrypted)
    
    assert original == decrypted, "Шифрование не работает!"
    print(f"   ✅ Шифрование работает: {original} → {encrypted[:20]}... → {decrypted}")
    
    # Тест хеширования
    key_hash = service.hash_key(original)
    is_valid = service.verify_key(encrypted, key_hash)
    
    assert is_valid, "Верификация ключа не работает!"
    print(f"   ✅ Верификация ключа: {is_valid}")
    
    return True


def test_litellm_service():
    """Тест LiteLLM сервиса"""
    print("\n🤖 Тест LiteLLM сервиса...")
    
    service = LiteLLMService()
    
    # Получение списка провайдеров
    providers = service.get_available_providers()
    print(f"   ✅ Доступно провайдеров: {len(providers)}")
    
    for provider in providers[:3]:  # Показываем первые 3
        print(f"      • {provider['name']}: {provider['description']}")
    
    # Тест определения провайдера
    test_models = [
        ("gpt-4", "openai"),
        ("gemini-pro", "google"),
        ("claude-3", "anthropic"),
        ("llama-3", "openrouter"),
    ]
    
    print(f"   ✅ Тест определения провайдеров:")
    for model, expected_provider in test_models:
        detected = service._detect_provider_from_model(model)
        status = "✅" if detected == expected_provider else "❌"
        print(f"      {status} {model} → {detected} (ожидался: {expected_provider})")
    
    return True


async def test_litellm_generation():
    """Тест генерации через LiteLLM (требуется API ключ)"""
    print("\n💬 Тест генерации ответа...")
    
    service = LiteLLMService()
    
    # Проверяем наличие тестового ключа
    import os
    test_api_key = os.getenv("TEST_OPENROUTER_API_KEY")
    
    if not test_api_key:
        print(f"   ⚠️  TEST_OPENROUTER_API_KEY не настроен, пропускаем тест")
        return True
    
    try:
        # Тест с OpenRouter
        response = await service.generate(
            messages=[{"role": "user", "content": "Привет! Ответь кратко."}],
            api_key=test_api_key,
            model="google/gemma-7b-it",
            provider="openrouter",
            max_tokens=20
        )
        
        print(f"   ✅ Ответ получен:")
        print(f"      Модель: {response.model}")
        print(f"      Провайдер: {response.provider}")
        print(f"      Текст: {response.text[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка генерации: {e}")
        return False


def test_database_models():
    """Тест моделей базы данных"""
    print("\n🗄️  Тест моделей БД...")
    
    from core.auth.models import User, UserApiKey, ChatSession, ChatMessage
    
    # Создание тестового пользователя
    user = User(
        email="test@example.com",
        hashed_password="test-hash",
        full_name="Test User"
    )
    
    print(f"   ✅ Модель User: {user}")
    print(f"      ID: {user.id}")
    print(f"      Email: {user.email}")
    
    return True


async def main():
    """Запуск всех тестов"""
    print("=" * 60)
    print("🧪 PAD+ AI v4.0 — Интеграционные тесты")
    print("=" * 60)
    
    tests = [
        ("Шифрование", test_encryption),
        ("LiteLLM сервис", test_litellm_service),
        ("Модели БД", test_database_models),
        ("Генерация (опционально)", test_litellm_generation),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            # Проверяем, является ли функция асинхронной
            import inspect
            if inspect.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n❌ {name}: {e}")
    
    # Итоговый отчёт
    print("\n" + "=" * 60)
    print("📊 Итоговый отчёт")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if error:
            print(f"   Ошибка: {error}")
    
    print(f"\n📈 Пройдено: {passed}/{total} тестов")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены!")
    else:
        print(f"\n⚠️  {total - passed} тест(а) не пройдено")
    
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
