"""
Тест подключения к Redis (Upstash)
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def test_redis_connection():
    """Тестирует подключение к Redis"""
    print("🔍 Тестирование подключения к Redis...")
    print(f"📍 REDIS_URL: {os.getenv('REDIS_URL', 'НЕ НАЙДЕН')}")
    
    try:
        # Пытаемся импортировать redis
        import redis.asyncio as redis_client
        print("✅ Пакет redis установлен")
    except ImportError:
        print("❌ Пакет redis не установлен!")
        print("💡 Установите: pip install redis")
        return False
    
    try:
        # Создаем клиент
        r = redis_client.from_url(
            os.getenv('REDIS_URL'),
            encoding="utf-8",
            decode_responses=True
        )
        
        # Пробуем подключиться
        print("🔌 Подключение к Redis...")
        await r.ping()
        print("✅ УСПЕШНО! Redis подключен!")
        
        # Тестируем операции
        print("\n🧪 Тестирование операций...")
        
        # SET
        await r.set('test_key', 'test_value')
        print("✅ SET: test_key = test_value")
        
        # GET
        value = await r.get('test_key')
        print(f"✅ GET: test_key = {value}")
        
        if value == 'test_value':
            print("✅ Данные совпадают!")
        else:
            print("❌ Данные не совпадают!")
            return False
        
        # DELETE
        await r.delete('test_key')
        print("✅ DELETE: test_key удален")
        
        # Проверяем удаление
        value = await r.get('test_key')
        if value is None:
            print("✅ Ключ действительно удален")
        else:
            print("❌ Ключ не удален")
            return False
        
        # Закрываем соединение
        await r.close()
        print("\n🎉 Все тесты пройдены успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("\n💡 Возможные причины:")
        print("   1. Неверный REDIS_URL в .env файле")
        print("   2. Проблемы с сетью/брандмауэром")
        print("   3. Неверный токен доступа")
        print("   4. База данных Upstash не активна")
        return False

async def main():
    success = await test_redis_connection()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())