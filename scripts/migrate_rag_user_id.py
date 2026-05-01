#!/usr/bin/env python3
"""
🔄 Миграция RAG памяти — добавление user_id

Миграция добавляет поле user_id во все существующие записи RAG памяти.
Старые записи помечаются как "shared" (user_id = None).

Использование:
    python scripts/migrate_rag_user_id.py
"""

import sys
import os
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import chromadb
from chromadb.config import Settings
from datetime import datetime

print("=" * 70)
print("🔄 Миграция RAG памяти — добавление user_id")
print("=" * 70)

# Путь к данным
data_dir = Path(__file__).parent.parent / "data"
data_dir.mkdir(exist_ok=True)

chroma_path = data_dir / "chroma"
chroma_path.mkdir(exist_ok=True)

print(f"\n📁 Путь к ChromaDB: {chroma_path}")

# Инициализация ChromaDB
print("\n🔌 Подключение к ChromaDB...")
client = chromadb.PersistentClient(path=str(chroma_path))

# Получаем коллекцию
try:
    collection = client.get_collection("neuromind_dialogs_v3")
    print(f"✅ Коллекция найдена: neuromind_dialogs_v3")
except Exception:
    try:
        collection = client.get_collection("rag_memory")
        print(f"✅ Коллекция найдена: rag_memory")
    except Exception:
        print("❌ Коллекция не найдена")
        print("   RAG память пуста, миграция не требуется")
        sys.exit(0)

# Получаем количество записей
total_count = collection.count()
print(f"📊 Всего записей: {total_count}")

if total_count == 0:
    print("   RAG память пуста, миграция не требуется")
    sys.exit(0)

# Получаем все записи
print("\n📥 Загрузка всех записей для миграции...")
results = collection.get(include=["metadatas"])

if not results or not results['ids']:
    print("   Нет записей для миграции")
    sys.exit(0)

# Считаем сколько записей уже имеют user_id
already_migrated = 0
needs_migration = 0

for meta in results['metadatas']:
    if meta and 'user_id' in meta:
        already_migrated += 1
    else:
        needs_migration += 1

print(f"   Уже мигрировано: {already_migrated}")
print(f"   Требует миграции: {needs_migration}")

if needs_migration == 0:
    print("\n✅ Все записи уже мигрированы!")
    sys.exit(0)

# Миграция
print(f"\n🔄 Начало миграции {needs_migration} записей...")

migrated_count = 0
errors = 0

for i, doc_id in enumerate(results['ids']):
    try:
        meta = results['metadatas'][i] if results['metadatas'] else {}
        
        # Пропускаем уже мигрированные
        if meta and 'user_id' in meta:
            continue
        
        # Добавляем user_id = None (общая запись)
        meta['user_id'] = None
        meta['migrated_at'] = datetime.now().isoformat()
        meta['migration_version'] = '2.0'
        
        # Обновляем метаданные
        collection.update(
            ids=[doc_id],
            metadatas=[meta]
        )
        
        migrated_count += 1
        
        # Прогресс каждые 10 записей
        if (i + 1) % 10 == 0:
            print(f"   Прогресс: {i + 1}/{len(results['ids'])} ({(i + 1) / len(results['ids']) * 100:.1f}%)")
            
    except Exception as e:
        errors += 1
        print(f"   ❌ Ошибка миграции {doc_id}: {e}")

# Итоги
print("\n" + "=" * 70)
print("📊 ИТОГИ МИГРАЦИИ")
print("=" * 70)
print(f"   Всего записей: {total_count}")
print(f"   Мигрировано: {migrated_count}")
print(f"   Ошибок: {errors}")
print(f"   Уже мигрировано: {already_migrated}")

if errors == 0:
    print("\n✅ Миграция завершена успешно!")
else:
    print(f"\n⚠️  Миграция завершена с {errors} ошибками")

# Проверяем результат
print("\n🔍 Проверка результата...")
final_results = collection.get(include=["metadatas"])
final_migrated = sum(1 for meta in final_results['metadatas'] if meta and 'user_id' in meta)
print(f"   Записей с user_id: {final_migrated}/{total_count}")

if final_migrated == total_count:
    print("\n✅ ВСЕ ЗАПИСИ УСПЕШНО МИГРИРОВАНЫ!")
else:
    print(f"\n⚠️  Не все записи мигрированы: {final_migrated}/{total_count}")

print("\n" + "=" * 70)
print("📝 СЛЕДУЮЩИЕ ШАГИ:")
print("=" * 70)
print("1. Проверьте работу RAG поиска с user_id")
print("2. Запустите тесты: pytest tests/optimization_tests/test_rag_user_id.py")
print("3. Обновите код для использования user_id в get_context()")
print("=" * 70)
