#!/usr/bin/env python3
"""
🔄 Миграция: Индексы для user_id

Добавляет индексы для user_id во всех таблицах БД для ускорения поиска.

Использование:
    python scripts/migrate_add_user_id_indexes.py
"""

import sqlite3
from pathlib import Path
import sys

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

print("=" * 70)
print("🔄 Миграция: Индексы для user_id")
print("=" * 70)

# Путь к данным
data_dir = Path(__file__).parent.parent / "data"
data_dir.mkdir(exist_ok=True)

# Файлы БД
DB_FILES = [
    "episodic.db",
    "memory.db",
    "facts.db",
    "core.db",
    "knowledge.db",
    "llm.db"
]

# Индексы для каждой таблицы
INDEXES = {
    "episodes": ["user_id", "timestamp"],
    "memory_soil": [],  # Нет user_id в этой таблице
    "facts": [],  # Проверим структуру
}

print(f"\n📁 Путь к данным: {data_dir}")

for db_file in DB_FILES:
    db_path = data_dir / db_file
    
    if not db_path.exists():
        print(f"\n⏭️  Пропущено: {db_file} (не существует)")
        continue
    
    print(f"\n📊 Обработка: {db_file}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Получаем список таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        # Пропускаем системные таблицы
        if table.startswith("sqlite_"):
            continue
        
        # Получаем колонки таблицы
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Проверяем наличие user_id
        if "user_id" not in columns:
            print(f"   ⏭️  Таблица {table}: нет колонки user_id")
            continue
        
        # Создаём индекс для user_id
        index_name = f"idx_{table}_user_id"
        
        # Проверяем существование индекса
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            (index_name,)
        )
        
        if cursor.fetchone():
            print(f"   ✅ Таблица {table}: индекс {index_name} уже существует")
        else:
            try:
                cursor.execute(f"CREATE INDEX {index_name} ON {table}(user_id)")
                print(f"   ✅ Таблица {table}: создан индекс {index_name}")
            except sqlite3.Error as e:
                print(f"   ❌ Таблица {table}: ошибка создания индекса: {e}")
        
        # Также создаём композитный индекс user_id + timestamp если есть timestamp
        if "timestamp" in columns or "created_at" in columns:
            time_column = "timestamp" if "timestamp" in columns else "created_at"
            composite_index_name = f"idx_{table}_user_id_{time_column}"
            
            # Проверяем существование индекса
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                (composite_index_name,)
            )
            
            if cursor.fetchone():
                print(f"   ✅ Таблица {table}: композитный индекс {composite_index_name} уже существует")
            else:
                try:
                    cursor.execute(f"CREATE INDEX {composite_index_name} ON {table}(user_id, {time_column} DESC)")
                    print(f"   ✅ Таблица {table}: создан композитный индекс {composite_index_name}")
                except sqlite3.Error as e:
                    print(f"   ❌ Таблица {table}: ошибка создания композитного индекса: {e}")
    
    conn.commit()
    conn.close()

print("\n" + "=" * 70)
print("✅ Миграция завершена!")
print("=" * 70)

print("\n📝 СЛЕДУЮЩИЕ ШАГИ:")
print("1. Проверьте работу поиска по user_id")
print("2. Запустите тесты: pytest tests/ -v")
print("3. Проверьте производительность через EXPLAIN QUERY PLAN")
print("=" * 70)
