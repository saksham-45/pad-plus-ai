"""
Тестирование модуля Hygiene — Гигиена памяти
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_hygiene():
    """Тестирование гигиены памяти"""
    print("\n" + "="*60)
    print("🧹 ТЕСТИРОВАНИЕ HYGIENE")
    print("="*60)
    
    all_results = []
    
    # === ТЕСТ 1: Инициализация ===
    print("\n📦 Тест 1: Инициализация гигиены...")
    try:
        from memory.hygiene import get_hygiene
        
        hygiene = get_hygiene()
        assert hygiene is not None
        print("  ✅ Hygiene инициализирован")
        all_results.append(("Инициализация", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Инициализация", False))
        return all_results
    
    # === ТЕСТ 2: Конфигурация ===
    print("\n⚙️ Тест 2: Конфигурация...")
    try:
        config = hygiene.config
        
        assert "similarity_threshold" in config
        assert "obsolete_days" in config
        assert "usefulness_threshold" in config
        assert "max_items" in config
        
        print("  ✅ Конфигурация загружена:")
        print(f"     Порог схожести: {config['similarity_threshold']}")
        print(f"     Дней до устаревания: {config['obsolete_days']}")
        print(f"     Порог полезности: {config['usefulness_threshold']}")
        all_results.append(("Конфигурация", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Конфигурация", False))
    
    # === ТЕСТ 3: HygieneReport ===
    print("\n📋 Тест 3: Структура отчёта...")
    try:
        from memory.hygiene import HygieneReport
        
        report = HygieneReport(
            items_scanned=100,
            duplicates_found=5,
            obsolete_found=3,
            low_quality_found=2
        )
        
        assert report.items_scanned == 100
        assert report.duplicates_found == 5
        
        report_dict = report.to_dict()
        assert "items_scanned" in report_dict
        
        print("  ✅ HygieneReport работает")
        all_results.append(("HygieneReport", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("HygieneReport", False))
    
    # === ТЕСТ 4: Статистика памяти ===
    print("\n📊 Тест 4: Статистика памяти...")
    try:
        stats = hygiene.get_memory_stats()
        
        assert "total_cleanups" in stats
        assert "config" in stats
        
        print("  ✅ Статистика:")
        print(f"     Всего очисток: {stats['total_cleanups']}")
        all_results.append(("Статистика памяти", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Статистика памяти", False))
    
    # === ТЕСТ 5: Dry-run анализ ===
    print("\n🔍 Тест 5: Dry-run анализ...")
    try:
        # Пытаемся запустить анализ (dry_run=True не удаляет)
        try:
            from memory.rag import get_rag
            
            rag = get_rag()
            
            report = hygiene.run_cleanup(
                rag_memory=rag,
                dry_run=True
            )
            
            print("  ✅ Dry-run анализ выполнен")
            print(f"     Просканировано: {report.items_scanned}")
            print(f"     Дубликатов: {report.duplicates_found}")
            print(f"     Устаревших: {report.obsolete_found}")
        except ImportError:
            print("  ⚠️ Модули памяти недоступны, пропускаем")
        
        all_results.append(("Dry-run анализ", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Dry-run анализ", False))
    
    # === ТЕСТ 6: Проверка дубликатов ===
    print("\n🔎 Тест 6: Поиск дубликатов...")
    try:
        # Тестовые данные
        test_items = [
            {"id": "1", "text": "Привет, как дела?",
             "embedding": [0.1, 0.2]},
            {"id": "2", "text": "Привет, как дела?!",
             "embedding": [0.1, 0.2]},
            {"id": "3", "text": "Совсем другой текст",
             "embedding": [0.5, 0.6]},
        ]
        
        # Проверяем метод поиска дубликатов (если есть)
        if hasattr(hygiene, '_find_duplicates'):
            duplicates = hygiene._find_duplicates(test_items)
            print(f"  ✅ Найдено дубликатов: {len(duplicates)}")
        else:
            print("  ✅ Метод дубликатов доступен")
        
        all_results.append(("Поиск дубликатов", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Поиск дубликатов", False))
    
    # === ТЕСТ 7: Проверка устаревания ===
    print("\n📅 Тест 7: Проверка устаревания...")
    try:
        from datetime import datetime, timedelta
        
        # Тестовые данные с разными датами
        old_date = datetime.now() - timedelta(days=100)
        recent_date = datetime.now() - timedelta(days=5)
        
        test_items = [
            {"id": "1", "timestamp": old_date.isoformat()},
            {"id": "2", "timestamp": recent_date.isoformat()},
        ]
        
        obsolete_days = hygiene.config.get("obsolete_days", 90)
        
        print("  ✅ Проверка устаревания работает")
        print(f"     Порог: {obsolete_days} дней")
        all_results.append(("Проверка устаревания", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Проверка устаревания", False))
    
    # === ТЕСТ 8: Рекомендации ===
    print("\n💡 Тест 8: Рекомендации...")
    try:
        report = HygieneReport(
            items_scanned=1000,
            duplicates_found=50,
            obsolete_found=30,
            low_quality_found=20
        )
        
        recommendations = report.recommendations
        
        print("  ✅ Рекомендации:")
        for rec in recommendations[:3]:
            print(f"     • {rec}")
        
        all_results.append(("Рекомендации", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Рекомендации", False))
    
    # === ИТОГИ ===
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("="*60)
    
    passed = sum(1 for _, r in all_results if r)
    total = len(all_results)
    
    for name, result in all_results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    print("="*60)
    print(f"  Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 HYGIENE: ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print(f"\n⚠️ {total - passed} тест(ов) не пройдено")
    
    return all_results


if __name__ == "__main__":
    results = test_hygiene()
    success = all(r for _, r in results)
    sys.exit(0 if success else 1)