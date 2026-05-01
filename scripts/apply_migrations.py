"""
Скрипт для применения миграций базы данных PAD+ AI

Этот скрипт применяет все миграции из папки backend/database/migrations/
к базе данных Supabase.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.supabase_client import get_supabase

def apply_migrations():
    """Применяет все миграции к базе данных"""
    print("=" * 60)
    print("ПРИМЕНЕНИЕ МИГРАЦИЙ БАЗЫ ДАННЫХ PAD+ AI")
    print("=" * 60)
    
    # Получаем клиент Supabase
    supabase = get_supabase()
    if not supabase:
        print("❌ Ошибка: Не удалось подключиться to Supabase")
        print("   Проверьте переменные окружения SUPABASE_URL и SUPABASE_KEY")
        return False
    
    print("✅ Подключение к Supabase успешно")
    
    # Путь к миграциям
    migrations_dir = Path(__file__).parent.parent / "backend" / "database" / "migrations"
    
    if not migrations_dir.exists():
        print(f"❌ Папка с миграциями не найдена: {migrations_dir}")
        return False
    
    # Получаем список миграций
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print("❌ Миграции не найдены")
        return False
    
    print(f"📁 Найдено миграций: {len(migration_files)}")
    
    # Применяем миграции
    for migration_file in migration_files:
        print(f"\n--- Применение миграции: {migration_file.name} ---")
        
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            # Выполняем миграцию
            # Используем RPC для выполнения SQL или прямой запрос через Supabase
            # К сожалению, Supabase client не поддерживает прямое выполнение SQL
            # Поэтому выводим инструкцию для ручного применения
            
            print(f"⚠️ Миграция '{migration_file.name}' требует ручного применения")
            print(f"   Содержимое файла: {migration_file}")
            print(f"   Примените этот SQL через Supabase Dashboard > SQL Editor")
            
        except Exception as e:
            print(f"❌ Ошибка при чтении миграции: {e}")
            continue
    
    print("\n" + "=" * 60)
    print("ИНСТРУКЦИЯ ПО ПРИМЕНЕНИЮ МИГРАЦИЙ:")
    print("=" * 60)
    print("""
1. Откройте Supabase Dashboard: https://app.supabase.com
2. Выберите ваш проект
3. Перейдите в SQL Editor
4. Скопируйте и выполните содержимое следующих файлов по порядку:
   - backend/database/migrations/001_initial_schema.sql (если есть)
   - backend/database/migrations/002_*.sql
   - ...
   - backend/database/migrations/005_documents_and_collections.sql
   - backend/database/migrations/004_user_settings_and_dialogs.sql

5. После применения всех миграций проверьте наличие таблиц:
   - documents
   - document_collections
   - dialogs
   - user_settings
   - и другие

6. Перезапустите backend сервер
""")
    
    return True


def check_tables():
    """Проверяет наличие необходимых таблиц"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА НАЛИЧИЯ ТАБЛИЦ")
    print("=" * 60)
    
    supabase = get_supabase()
    if not supabase:
        print("❌ Ошибка: Не удалось подключиться к Supabase")
        return False
    
    # Список ожидаемых таблиц
    expected_tables = [
        "documents",
        "document_collections",
        "dialogs",
        "user_settings",
        "users",
        "user_api_keys",
    ]
    
    # Проверяем наличие таблиц через information_schema
    try:
        result = supabase.table("information_schema.tables")\
            .select("table_name")\
            .eq("table_schema", "public")\
            .execute()
        
        existing_tables = [row["table_name"] for row in result.data]
        
        print(f"\nНайдено таблиц: {len(existing_tables)}")
        
        for table in expected_tables:
            if table in existing_tables:
                print(f"✅ Таблица '{table}' существует")
            else:
                print(f"❌ Таблица '{table}' НЕ найдена")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке таблиц: {e}")
        print("   Возможно, таблица 'information_schema.tables' недоступна")
        return False


if __name__ == "__main__":
    # Проверяем наличие таблиц
    check_tables()
    
    # Применяем миграции
    apply_migrations()