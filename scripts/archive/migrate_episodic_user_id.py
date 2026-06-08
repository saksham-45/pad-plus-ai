#!/usr/bin/env python3
"""
🔄 Миграция Episodic Memory — добавление user_id

Миграция добавляет колонку user_id в таблицу episodes.
Старые записи помечаются как "shared" (user_id = NULL).

Использование:
    python scripts/migrate_episodic_user_id.py
"""

import sys
import os
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import sqlite3
from datetime import datetime

print("=" * 70)
print("🔄 Миграция Episodic Memory — добавление user_id")
print("=" * 70)

# Путь к данным
data_dir = Path(__file__).parent.parent / "data"
data_dir.mkdir(exist_ok=True)

db_path = data_dir / "episodic.db"

print(f"\n📁 Путь к БД: {db_path}")

if not db_path.exists():
    print("   БД не найдена, миграция не требуется")
    sys.exit(0)

# Подключение к БД
print("\n🔌 Подключение к SQLite...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Проверяем, существует ли колонка user_id
print("\n🔍 Проверка структуры таблицы...")
cursor.execute("PRAGMA table_info(episodes)")
columns = [row[1] for row in cursor.fetchall()]

if "user_id" in columns:
    print("   ✅ Колонка user_id уже существует")
    needs_column = False
else:
    print("   ❌ Колонка user_id отсутствует")
    needs_column = True

# Считаем количество записей
cursor.execute("SELECT COUNT(*) FROM episodes")
total_count = cursor.fetchone()[0]
print(f"📊 Всего записей: {total_count}")

if total_count == 0:
    print("   БД пуста, миграция не требуется")
    conn.close()
    sys.exit(0)

# Добавляем колонку если нужно
if needs_column:
    print("\n🔄 Добавление колонки user_id...")
    try:
        cursor.execute("ALTER TABLE episodes ADD COLUMN user_id TEXT")
        conn.commit()
        print("   ✅ Колонка user_id добавлена")
    except sqlite3.OperationalError as e:
        print(f"   ⚠️  Ошибка добавления колонки: {e}")

# Считаем сколько записей уже имеют user_id
cursor.execute("SELECT COUNT(*) FROM episodes WHERE user_id IS NOT NULL")
already_migrated = cursor.fetchone()[0]
needs_migration = total_count - already_migrated

print(f"   Уже мигрировано: {already_migrated}")
print(f"   Требует миграции: {needs_migration}")

if needs_migration == 0:
    print("\n✅ Все записи уже мигрированы!")
    conn.close()
    sys.exit(0)

# Миграция - помечаем все записи без user_id как общие (NULL)
print(f"\n🔄 Миграция {needs_migration} записей...")
print("   (старые записи помечаются как общие с user_id = NULL)")

# Записи уже имеют NULL по умолчанию, просто проверяем
cursor.execute("SELECT COUNT(*) FROM episodes WHERE user_id IS NULL")
null_count = cursor.fetchone()[0]
print(f"   ✅ Записей с user_id = NULL: {null_count}")

# Создаём индексы
print("\n🔄 Создание индексов...")
try:
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodes_user_id ON episodes(user_id)")
    conn.commit()
    print("   ✅ Индекс для user_id создан")
except Exception as e:
    print(f"   ⚠️  Ошибка создания индекса: {e}")

# Итоги
print("\n" + "=" * 70)
print("📊 ИТОГИ МИГРАЦИИ")
print("=" * 70)
print(f"   Всего записей: {total_count}")
print(f"   Записей с user_id: {already_migrated}")
print(f"   Записей с NULL (общие): {null_count}")

print("\n✅ МИГРАЦИЯ ЗАВЕРШЕНА!")

# Проверяем результат
print("\n🔍 Проверка результата...")
cursor.execute("SELECT user_id, COUNT(*) FROM episodes GROUP BY user_id")
results = cursor.fetchall()
print("   Распределение по user_id:")
for user_id, count in results:
    display_id = user_id if user_id else "(общие записи)"
    print(f"      {display_id}: {count}")

conn.close()

print("\n" + "=" * 70)
print("📝 СЛЕДУЮЩИЕ ШАГИ:")
print("=" * 70)
print("1. Проверьте работу Episodic Memory с user_id")
print("2. Запустите тесты: pytest tests/integration_tests/test_phase3_episodic_personalization.py")
print("3. Проверьте, что Pipeline сохраняет эпизоды с user_id")
print("=" * 70)
