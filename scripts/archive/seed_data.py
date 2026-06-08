"""
🌱 Seed Data Script - Создание тестовых данных

Этот скрипт создает тестовые данные для разработки и тестирования:
- Тестовый пользователь
- Настройки пользователя по умолчанию
- Тестовые диалоги (опционально)

Использование:
    python scripts/seed_data.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.supabase_client import get_supabase

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

# Настройки тестового пользователя
TEST_USER_EMAIL = os.getenv("SEED_USER_EMAIL", "test@padplus.ai")
TEST_USER_PASSWORD = os.getenv("SEED_USER_PASSWORD", "TestPassword123!")
TEST_USER_FULL_NAME = os.getenv("SEED_USER_FULL_NAME", "Тестовый Пользователь")

# ============================================================================
# ФУНКЦИИ
# ============================================================================

def check_supabase_connection():
    """Проверяет подключение к Supabase"""
    print("🔌 Проверка подключения к Supabase...")
    
    supabase = get_supabase()
    if not supabase:
        print("❌ Ошибка: Не удалось подключиться к Supabase")
        print("   Проверьте переменные окружения SUPABASE_URL и SUPABASE_KEY")
        return None
    
    print("✅ Подключение к Supabase успешно")
    return supabase


def check_tables_exist(supabase):
    """Проверяет наличие необходимых таблиц"""
    print("\n📋 Проверка наличия таблиц...")
    
    expected_tables = [
        "users",
        "user_settings",
        "user_api_keys",
        "dialogs",
        "messages"
    ]
    
    missing_tables = []
    
    for table in expected_tables:
        try:
            result = supabase.table(table).select("count").limit(1).execute()
            print(f"   ✅ Таблица '{table}' существует")
        except Exception as e:
            print(f"   ❌ Таблица '{table}' не найдена")
            missing_tables.append(table)
    
    if missing_tables:
        print(f"\n⚠️ Отсутствуют таблицы: {', '.join(missing_tables)}")
        print("   Выполните миграции базы данных перед запуском seed скрипта")
        return False
    
    return True


def create_test_user(supabase):
    """Создает тестового пользователя"""
    print(f"\n👤 Создание тестового пользователя: {TEST_USER_EMAIL}")
    
    try:
        # Проверяем, существует ли уже пользователь
        result = supabase.table("users").select("id").eq("email", TEST_USER_EMAIL).execute()
        
        if result.data and len(result.data) > 0:
            print(f"   ⚠️ Пользователь '{TEST_USER_EMAIL}' уже существует")
            user_id = result.data[0]["id"]
            return user_id, False  # Возвращаем False, так как пользователь не был создан
        
        # Создаем пользователя через Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "options": {
                "data": {
                    "full_name": TEST_USER_FULL_NAME
                }
            }
        })
        
        if not auth_response.user:
            print(f"   ❌ Ошибка создания пользователя: {auth_response}")
            return None, False
        
        user_id = auth_response.user.id
        print(f"   ✅ Пользователь создан с ID: {user_id}")
        
        # Создаем профиль в public.users
        profile_data = {
            "id": user_id,
            "email": TEST_USER_EMAIL,
            "hashed_password": "",  # Не используется, пароль в auth.users
            "full_name": TEST_USER_FULL_NAME,
            "avatar_url": None,
            "email_verified": False,
            "is_active": True
        }
        
        try:
            supabase.table("users").insert(profile_data).execute()
            print("   ✅ Профиль пользователя создан")
        except Exception as e:
            print(f"   ⚠️ Не удалось создать профиль: {e}")
        
        return user_id, True
        
    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            print(f"   ⚠️ Пользователь уже зарегистрирован в системе аутентификации")
            # Пытаемся получить ID существующего пользователя
            result = supabase.table("users").select("id").eq("email", TEST_USER_EMAIL).execute()
            if result.data:
                return result.data[0]["id"], False
        else:
            print(f"   ❌ Ошибка: {error_msg}")
        
        return None, False


def ensure_user_settings(supabase, user_id):
    """Гарантирует наличие настроек пользователя"""
    print(f"\n⚙️  Проверка настроек пользователя...")
    
    try:
        # Проверяем, есть ли уже настройки
        result = supabase.table("user_settings").select("id").eq("user_id", user_id).execute()
        
        if result.data and len(result.data) > 0:
            print("   ✅ Настройки пользователя уже существуют")
            return True
        
        # Создаем настройки по умолчанию
        settings_data = {
            "user_id": user_id,
            "persona_tone": "friendly",
            "persona_detail_level": "moderate",
            "persona_emotion_level": "balanced",
            "persona_specialization": "general",
            "notification_email": True,
            "notification_push": False,
            "notification_sound": True,
            "notification_frequency": "immediate",
            "theme": "dark",
            "font_size": "medium",
            "compact_mode": False
        }
        
        result = supabase.table("user_settings").insert(settings_data).execute()
        
        if result.data:
            print("   ✅ Настройки пользователя созданы")
            return True
        else:
            print("   ❌ Не удалось создать настройки пользователя")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False


def create_test_api_key(supabase, user_id):
    """Создает тестовый API ключ (опционально)"""
    print(f"\n🔑 Создание тестового API ключа...")
    
    # Получаем encryptor
    try:
        from core.encryption import get_encryptor
        encryptor = get_encryptor()
    except Exception as e:
        print(f"   ⚠️ Шифрование не настроено: {e}")
        print("   Пропускаем создание API ключа")
        return False
    
    # Проверяем, есть ли уже ключи
    try:
        result = supabase.table("user_api_keys").select("id").eq("user_id", user_id).execute()
        
        if result.data and len(result.data) > 0:
            print("   ⚠️ У пользователя уже есть API ключи")
            return False
        
        # Создаем тестовый ключ (заглушка)
        test_key = "test-key-not-for-production-use"
        encrypted_key = encryptor.encrypt(test_key)
        
        key_data = {
            "user_id": user_id,
            "provider": "openrouter",
            "provider_display_name": "OpenRouter",
            "name": "Тестовый ключ",
            "api_key_encrypted": encrypted_key,
            "model_preference": "auto",
            "is_default": True,
            "is_active": True
        }
        
        result = supabase.table("user_api_keys").insert(key_data).execute()
        
        if result.data:
            print("   ✅ Тестовый API ключ создан")
            return True
        else:
            print("   ❌ Не удалось создать API ключ")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False


def print_summary(user_id, user_created):
    """Выводит сводку о созданных данных"""
    print("\n" + "=" * 60)
    print("📊 СВОДКА")
    print("=" * 60)
    
    if user_id:
        print(f"✅ Пользователь: {TEST_USER_EMAIL}")
        print(f"   ID: {user_id}")
        if user_created:
            print(f"   Пароль: {TEST_USER_PASSWORD}")
        else:
            print("   (существовал ранее)")
        
        print(f"\n🔐 Для входа используйте:")
        print(f"   Email: {TEST_USER_EMAIL}")
        print(f"   Пароль: {TEST_USER_PASSWORD}")
        
        print(f"\n📝 Для тестирования API:")
        print(f"   1. Войдите через POST /api/v1/auth/login")
        print(f"   2. Используйте полученный токен в заголовке Authorization")
        print(f"   3. Пример: Authorization: Bearer <ваш_токен>")
    else:
        print("❌ Не удалось создать тестовые данные")
    
    print("\n" + "=" * 60)


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    """Основная функция"""
    print("=" * 60)
    print("🌱 PAD+ AI - Seed Data Script")
    print("=" * 60)
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Проверяем подключение к Supabase
    supabase = check_supabase_connection()
    if not supabase:
        return False
    
    # 2. Проверяем наличие таблиц
    if not check_tables_exist(supabase):
        return False
    
    # 3. Создаем тестового пользователя
    user_id, user_created = create_test_user(supabase)
    
    if not user_id:
        print("\n❌ Не удалось создать пользователя. Завершение.")
        return False
    
    # 4. Гарантируем наличие настроек пользователя
    ensure_user_settings(supabase, user_id)
    
    # 5. Создаем тестовый API ключ (опционально)
    create_test_api_key(supabase, user_id)
    
    # 6. Выводим сводку
    print_summary(user_id, user_created)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)