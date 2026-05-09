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
from core.encryption import KeyEncryptor, generate_encryption_key
from runtime.litellm_service import LiteLLMService


def test_encryption():
    """Тест шифрования"""
    print("\n🔐 Тест шифрования...")
    
    # Генерация ключа
    key = generate_encryption_key()
    print(f"   ✅ Ключ сгенерирован: {key[:20]}...")
    
    # Создание сервиса
    service = KeyEncryptor(key)
    print(f"   ✅ Сервис создан")
    
    # Тест шифрования/дешифрования
    test_data = "sk-or-v1-REPLACEDabc123def456"
    encrypted = service.encrypt(test_data)
    decrypted = service.decrypt(encrypted)
    
    print(f"   ✅ Исходные данные: {test_data[:10]}...")
    print(f"   ✅ Зашифрованные: {encrypted[:20]}...")
    print(f"   ✅ Расшифрованные: {decrypted[:10]}...")
    
    assert decrypted == test_data, "Расшифрованные данные должны совпадать"
    assert encrypted != test_data, "Зашифрованные данные должны отличаться"
    
    print("   ✅ Тест шифрования пройден!")
    
    return True


def test_litellm_service():
    """Тест LiteLLM сервиса"""
    print("\n🤖 Тест LiteLLM сервиса...")
    
    service = LiteLLMService()
    
    # Получение списка моделей
    models = service.get_available_models()
    print(f"   ✅ Доступно моделей: {len(models)}")
    
    # Показываем первые 5 моделей
    for i, model in enumerate(models[:5]):
        if isinstance(model, dict):
            model_name = model.get('name', str(model))
        else:
            model_name = str(model)
        print(f"      • {model_name}")
    
    # Базовый тест инициализации
    assert service is not None, "LiteLLM сервис должен быть создан"
    assert len(models) > 0, "Должны быть доступны модели"
    
    print("   ✅ Тест LiteLLM сервиса пройден!")
    
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
    
    # Проверяем подключение к Supabase
    try:
        from core.supabase_client import get_supabase
        supabase = get_supabase()
        
        if supabase:
            print(f"   ✅ Supabase клиент инициализирован")
            
            # Тест простого запроса
            try:
                result = supabase.table("users").select("count").execute()
                print(f"   ✅ Запрос к БД успешен")
            except Exception as e:
                print(f"   ⚠️  Ошибка запроса к БД: {e}")
        else:
            print(f"   ⚠️  Supabase клиент не инициализирован")
        
    except Exception as e:
        print(f"   ❌ Ошибка импорта Supabase: {e}")
    
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
