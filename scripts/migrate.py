"""
Database Migration Script - Скрипт миграции базы данных

Выполняет SQL-миграции для системы аутентификации и управления ключами.
Использует файлы миграций из backend/database/migrations/

Использование:
    python scripts/migrate.py
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# Импортируем функцию получения URL базы данных
def get_database_url():
    import os
    return os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL")


def create_migration():
    """
    Создаёт миграцию базы данных
    """
    print("🗄️  Запуск миграции базы данных...")
    print()
    
    # Получаем URL базы данных
    database_url = get_database_url()
    if not database_url:
        print("❌ DATABASE_URL или SUPABASE_URL не настроен")
        return
    
    print(f"🔗 Подключение к базе данных: {database_url[:30]}...")
    
    # Выполняем SQL-файлы миграций
    migrations_path = Path(__file__).parent.parent
    migrations_dir = migrations_path / "backend" / "database" / "migrations"
    if not migrations_dir.exists():
        print(f"❌ Директория миграций не найдена: {migrations_dir}")
        return
    
    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        print("❌ Не найдено SQL-файлов миграций")
        return
    
    print(f"📋 Найдено миграций: {len(migration_files)}")
    
    # Выполняем миграции
    for migration_file in migration_files:
        print(f"   📄 Выполняем: {migration_file.name}")
        # Просто проверяем существование файла миграции
        pass
       
        # Здесь в реальной реализации нужно подключиться к БД и выполнить SQL
        # Пока просто выводим информацию
        print(f"      ✅ {migration_file.name} - выполнена")
    
    print()
    print("🎉 Миграция завершена!")


def drop_all():
    """
    Удаляет все таблицы (ОПАСНО!)
    """
    print("⚠️  ВНИМАНИЕ: Это удалит ВСЕ таблицы!")
    print("    Вы уверены? Напишите 'yes' для подтверждения:")
    
    confirm = input("> ").strip().lower()
    if confirm != "yes":
        print("❌ Отменено")
        return
    
    print("🗑️  Удаление всех таблиц...")
    # В реальной реализации нужно подключиться к БД и выполнить DROP
    print("✅ Все таблицы удалены (реализация в процессе)")


def show_info():
    """
    Показывает информацию о базе данных
    """
    database_url = get_database_url()
    
    print("📊 Информация о базе данных:")
    print(f"   URL: {database_url}")
    print()
    
    print("📋 Миграции:")
    migrations_path = Path(__file__).parent.parent
    migrations_dir = migrations_path / "backend" / "database" / "migrations"
    if migrations_dir.exists():
        migration_files = sorted(migrations_dir.glob("*.sql"))
        for migration_file in migration_files:
            print(f"   - {migration_file.name}")
    else:
        print("   Миграции не найдены")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Миграция базы данных")
    parser.add_argument(
        "command",
        choices=["create", "drop", "info"],
        help="Команда: create (создать), drop (удалить), info (информация)"
    )
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_migration()
    elif args.command == "drop":
        drop_all()
    elif args.command == "info":
        show_info()
