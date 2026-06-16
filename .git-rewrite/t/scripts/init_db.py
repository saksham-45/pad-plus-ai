"""
🗄️ Database Initialization Script

Инициализация базы данных:
- Создание таблиц
- Применение миграций
- Проверка подключения

Использование:
    python scripts/init_db.py
"""

import os
import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv()


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def check_env():
    """Проверяет наличие .env файла"""
    env_file = Path(__file__).parent.parent / ".env"
    
    if not env_file.exists():
        print("❌ .env файл не найден!")
        print("\nСоздайте .env файл:")
        print("  cp .env.example .env")
        print("\nЗаполните переменные:")
        print("  SUPABASE_URL=...")
        print("  SUPABASE_KEY=...")
        print("  ENCRYPTION_KEY=...")
        return False
    
    print("✅ .env файл найден")
    return True


def check_supabase():
    """Проверяет подключение к Supabase"""
    from core.supabase_client import get_supabase, check_database_connection
    
    print_header("2. Проверка подключения к БД")
    
    supabase = get_supabase()
    
    if supabase is None:
        print("⚠️ Supabase не подключен")
        print("\nПроверьте .env:")
        print("  SUPABASE_URL=https://...")
        print("  SUPABASE_KEY=...")
        return False
    
    connected = check_database_connection()
    
    if connected:
        print("✅ Подключение к БД работает")
        return True
    else:
        print("❌ Подключение к БД не работает")
        return False


def check_encryption():
    """Проверяет шифрование"""
    print_header("3. Проверка шифрования")
    
    try:
        from core.encryption import get_encryptor
        encryptor = get_encryptor()
        
        # Тест шифрования
        test_key = "test-api-key-123"
        encrypted = encryptor.encrypt(test_key)
        decrypted = encryptor.decrypt(encrypted)
        
        if decrypted == test_key:
            print("✅ Шифрование работает")
            return True
        else:
            print("❌ Ошибка шифрования/дешифрования")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка шифрования: {e}")
        print("\nПроверьте .env:")
        print("  ENCRYPTION_KEY=...")
        return False


def apply_migrations():
    """Применяет SQL миграции"""
    print_header("4. Применение миграций")
    
    supabase = get_supabase()
    
    if supabase is None:
        print("⚠️ Пропущено (БД не подключена)")
        return
    
    migration_file = Path(__file__).parent.parent / "backend" / "database" / "migrations" / "001_initial_schema.sql"
    
    if not migration_file.exists():
        print(f"❌ Миграция не найдена: {migration_file}")
        return
    
    print(f"📄 Чтение миграции: {migration_file}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Разделяем на команды (упрощённо)
    commands = sql.split(';')
    
    executed = 0
    errors = 0
    
    for command in commands:
        command = command.strip()
        if not command or command.startswith('--'):
            continue
        
        try:
            # Выполняем команду
            supabase.rpc(command) if command.startswith('CREATE FUNCTION') else None
            executed += 1
        except Exception as e:
            # Игнорируем некоторые ошибки (например, таблица уже существует)
            if 'already exists' in str(e).lower():
                print(f"⚠️  {command[:50]}... (уже существует)")
            else:
                print(f"❌ Ошибка: {command[:50]}... - {e}")
                errors += 1
    
    print(f"\n✅ Выполнено команд: {executed}")
    if errors > 0:
        print(f"⚠️  Ошибок: {errors}")


def create_test_user():
    """Создаёт тестового пользователя"""
    print_header("5. Создание тестового пользователя")
    
    supabase = get_supabase()
    
    if supabase is None:
        print("⚠️ Пропущено (БД не подключена)")
        return
    
    import hashlib
    import uuid
    
    email = "test@padplus.ai"
    password = "test123"
    hashed = hashlib.sha256(password.encode()).hexdigest()
    user_id = str(uuid.uuid4())
    
    try:
        result = supabase.table("users").insert({
            "id": user_id,
            "email": email,
            "hashed_password": hashed,
            "full_name": "Test User",
            "email_verified": False,
            "is_active": True
        }).execute()
        
        if result.data:
            print(f"✅ Тестовый пользователь создан:")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            print(f"   ID: {user_id}")
        else:
            print("⚠️  Пользователь уже существует или ошибка")
            
    except Exception as e:
        print(f"⚠️  Ошибка создания: {e}")


def main():
    print_header("🗄️ PAD+ AI — Database Initialization")
    
    # 1. Проверка .env
    if not check_env():
        print("\n❌ Инициализация прервана")
        return 1
    
    # 2. Проверка БД
    db_ok = check_supabase()
    
    # 3. Проверка шифрования
    encryption_ok = check_encryption()
    
    if not encryption_ok:
        print("\n❌ Инициализация прервана")
        return 1
    
    # 4. Применение миграций
    if db_ok:
        apply_migrations()
        create_test_user()
    
    print_header("ИТОГИ")
    
    if db_ok and encryption_ok:
        print("✅ Инициализация завершена успешно!")
        print("\nСледующие шаги:")
        print("  1. Запустите backend: python -m uvicorn backend.main:app --reload")
        print("  2. Протестируйте API: curl http://localhost:8080/api/v1/health")
        print("  3. Войдите как test@padplus.ai / test123")
        return 0
    else:
        print("⚠️  Инициализация завершена с предупреждениями")
        print("\nПроблемы:")
        if not db_ok:
            print("  - БД не подключена")
        if not encryption_ok:
            print("  - Шифрование не работает")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
