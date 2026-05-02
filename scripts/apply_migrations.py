"""
Скрипт для применения миграций базы данных PAD+ AI

Этот скрипт применяет все миграции из папки backend/database/migrations/
к базе данных PostgreSQL через DATABASE_URL.
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


def apply_migrations():
    """Применяет все миграции к базе данных"""
    print("=" * 60)
    print("ПРИМЕНЕНИЕ МИГРАЦИЙ БАЗЫ ДАННЫХ PAD+ AI")
    print("=" * 60)
    
    # Получаем DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ Ошибка: DATABASE_URL не настроен")
        print("   Для Render это должно быть настроено автоматически")
        return False
    
    print(f"✅ DATABASE_URL найден: {database_url[:30]}...")
    
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
    
    # Подключаемся к PostgreSQL
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("❌ Ошибка: psycopg2 не установлен")
        print("   Установите: pip install psycopg2-binary")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        print("✅ Подключение к PostgreSQL успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return False

    # Проверяем таблицу для отслеживания применённых миграций
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        conn.commit()
        print("✅ Таблица _migrations готова")
    except Exception as e:
        print(f"❌ Ошибка создания таблицы миграций: {e}")
        conn.close()
        return False

    # Получаем список применённых миграций
    cursor.execute("SELECT version FROM _migrations")
    applied_migrations = [row["version"] for row in cursor.fetchall()]
    
    # Применяем миграции
    migrated_count = 0
    failed_count = 0
    
    for migration_file in migration_files:
        # Извлекаем версию из имени файла (например, 001_initial_schema.sql -> 001_initial_schema)
        version = migration_file.stem
        
        # Проверяем, была ли миграция уже применена
        if version in applied_migrations:
            print(f"⏭️  Пропущена (уже применена): {migration_file.name}")
            continue
        
        print(f"\n--- Применение миграции: {migration_file.name} ---")
        
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            # Выполняем SQL
            print(f"🔄 Выполняем миграцию...")
            cursor.execute(migration_sql)
            conn.commit()
            
            # Отмечаем миграцию как применённую
            cursor.execute(
                "INSERT INTO _migrations (version) VALUES (%s)",
                (version,)
            )
            conn.commit()
            
            print(f"✅ Миграция успешно применена: {migration_file.name}")
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Ошибка при применении миграции '{migration_file.name}': {e}")
            conn.rollback()
            failed_count += 1
            import traceback
            traceback.print_exc()
            continue
    
    # Закрываем соединение
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"ГОТОВО! Применено миграций: {migrated_count}/{len(migration_files)}")
    if failed_count > 0:
        print(f"❌ Ошибок: {failed_count}")
    print("=" * 60)
    
    # Проверяем таблицы
    check_tables(database_url)
    
    return failed_count == 0


def check_tables(database_url=None):
    """Проверяет наличие необходимых таблиц"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА НАЛИЧИЯ ТАБЛИЦ")
    print("=" * 60)
    
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ Ошибка: DATABASE_URL не настроен")
        return False
    
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Получаем список таблиц
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\nНайдено таблиц: {len(existing_tables)}")
        
        # Список ожидаемых таблиц
        expected_tables = [
            "users",
            "user_api_keys",
            "chat_sessions",
            "chat_messages",
            "documents",
            "document_collections",
            "user_settings",
            "dialogs",
        ]
        
        for table in expected_tables:
            if table in existing_tables:
                print(f"✅ Таблица '{table}' существует")
            else:
                print(f"❌ Таблица '{table}' НЕ найдена")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке таблиц: {e}")
        return False


if __name__ == "__main__":
    # Применяем миграции
    success = apply_migrations()
    
    if success:
        print("\n✅ Все миграции успешно применены!")
        sys.exit(0)
    else:
        print("\n❌ Ошибки при применении миграций")
        sys.exit(1)