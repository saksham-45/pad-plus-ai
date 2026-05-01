#!/usr/bin/env python3
"""
🔄 Миграция фактов из SQLite в ChromaDB

Переносит все факты из FactMemory (SQLite) в FactMemoryChroma (ChromaDB).

Использование:
    python scripts/migrate_facts_to_chroma.py
"""

import sys
import os
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from memory.fact_memory import get_fact_memory
from memory.fact_memory_chroma import get_fact_memory_chroma

print("=" * 70)
print("🔄 Миграция фактов в ChromaDB")
print("=" * 70)

# Получаем старую память (SQLite)
print("\n📥 Инициализация FactMemory (SQLite)...")
old_facts = get_fact_memory()

# Получаем новую память (ChromaDB)
print("📥 Инициализация FactMemoryChroma (ChromaDB)...")
new_facts = get_fact_memory_chroma()

# Получаем все факты из SQLite
print("\n🔍 Получение всех фактов из SQLite...")
all_facts = old_facts.get_all() if hasattr(old_facts, 'get_all') else []

# Если get_all не существует, используем search
if not all_facts:
    print("   Метод get_all не найден, используем search...")
    all_facts = old_facts.search("", min_confidence=0.0, limit=10000)

print(f"📊 Найдено фактов: {len(all_facts)}")

if len(all_facts) == 0:
    print("   Факты не найдены, миграция не требуется")
    sys.exit(0)

# Мигрируем
print(f"\n🔄 Начало миграции {len(all_facts)} фактов...")
migrated = 0
errors = 0

for i, fact in enumerate(all_facts):
    try:
        # Получаем данные из старого факта
        if hasattr(fact, 'to_dict'):
            fact_dict = fact.to_dict()
        else:
            fact_dict = fact
        
        # Извлекаем triple (subject, predicate, object)
        triple = fact_dict.get('triple', {})
        subject = triple.get('subject', '')
        predicate = triple.get('predicate', '')
        object_val = triple.get('object', '')
        
        # Если triple нет, пробуем извлечь из content
        if not subject and not predicate and not object_val:
            content = fact_dict.get('content', '')
            # Пытаемся распарсить "Subject predicate object"
            parts = content.split(' ', 2)
            if len(parts) >= 3:
                subject, predicate, object_val = parts[0], parts[1], parts[2]
            else:
                subject = content
                predicate = "это"
                object_val = "факт"
        
        # Добавляем в новую память
        new_facts.add(
            subject=subject,
            predicate=predicate,
            object=object_val,
            confidence=fact_dict.get('confidence', 0.5),
            source=fact_dict.get('source', 'migrated'),
            metadata={
                'migrated_from': 'sqlite',
                'old_id': fact_dict.get('id', ''),
                'created_at': fact_dict.get('created_at', '')
            }
        )
        
        migrated += 1
        
        # Прогресс каждые 10 фактов
        if (i + 1) % 10 == 0:
            print(f"   Прогресс: {i + 1}/{len(all_facts)} ({(i + 1) / len(all_facts) * 100:.1f}%)")
            
    except Exception as e:
        errors += 1
        print(f"   ❌ Ошибка миграции факта {i}: {e}")

# Итоги
print("\n" + "=" * 70)
print("📊 ИТОГИ МИГРАЦИИ")
print("=" * 70)
print(f"   Всего фактов: {len(all_facts)}")
print(f"   Мигрировано: {migrated}")
print(f"   Ошибок: {errors}")

if errors == 0:
    print("\n✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
else:
    print(f"\n⚠️  МИГРАЦИЯ ЗАВЕРШЕНА С {errors} ОШИБКАМИ")

# Проверяем результат
print("\n🔍 Проверка результата...")
new_stats = new_facts.get_stats()
print(f"   Фактов в ChromaDB: {new_stats.get('total_facts', 0)}")

# Сравниваем
old_stats = old_facts.get_stats() if hasattr(old_facts, 'get_stats') else {}
print(f"   Фактов в SQLite: {old_stats.get('total_facts', len(all_facts))}")

print("\n" + "=" * 70)
print("📝 СЛЕДУЮЩИЕ ШАГИ:")
print("=" * 70)
print("1. Проверьте работу FactMemoryChroma")
print("2. Запустите тесты: pytest tests/integration_tests/test_fact_memory_chroma.py")
print("3. Обновите Pipeline для использования FactMemoryChroma")
print("=" * 70)
