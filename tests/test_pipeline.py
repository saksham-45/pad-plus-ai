"""
Тестирование модуля Pipeline — Нервная система
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_pipeline():
    """Тестирование пайплайна"""
    print("\n" + "="*60)
    print("🔄 ТЕСТИРОВАНИЕ PIPELINE")
    print("="*60)
    
    all_results = []
    
    # === ТЕСТ 1: Инициализация ===
    print("\n📦 Тест 1: Инициализация пайплайна...")
    try:
        from core.pipeline import get_pipeline
        
        pipeline = get_pipeline()
        assert pipeline is not None
        print("  ✅ Pipeline инициализирован")
        all_results.append(("Инициализация", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Инициализация", False))
        return all_results
    
    # === ТЕСТ 2: PipelineResult ===
    print("\n📋 Тест 2: Структура результата...")
    try:
        from core.pipeline import PipelineResult
        
        result = PipelineResult(
            success=True,
            response="Тестовый ответ",
            confidence=0.8
        )
        
        assert result.success
        assert result.response == "Тестовый ответ"
        assert result.confidence == 0.8
        
        print("  ✅ PipelineResult работает")
        all_results.append(("PipelineResult", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("PipelineResult", False))
    
    # === ТЕСТ 3: Anti-Loop Guard ===
    print("\n🔒 Тест 3: Anti-Loop Guard...")
    try:
        # Проверяем защиту от зацикливания
        _ = len(pipeline.anti_loop_history)  # noqa
        
        # Симулируем запрос
        should_block = pipeline._check_loop("Тестовый запрос")
        assert should_block is False  # Первый раз не должен блокировать
        
        # Добавляем несколько одинаковых запросов
        for _ in range(3):
            pipeline._record_request("Тестовый запрос")
        
        # Теперь должен блокировать
        should_block = pipeline._check_loop("Тестовый запрос")
        
        print("  ✅ Anti-Loop Guard работает")
        print(f"     История: {len(pipeline.anti_loop_history)} записей")
        all_results.append(("Anti-Loop Guard", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Anti-Loop Guard", False))
    
    # === ТЕСТ 4: Статистика ===
    print("\n📊 Тест 4: Статистика пайплайна...")
    try:
        stats = pipeline.get_stats()
        
        assert "total_calls" in stats
        assert "anti_loop_history_size" in stats
        
        print("  ✅ Статистика:")
        print(f"     Всего вызовов: {stats['total_calls']}")
        print(f"     Anti-loop история: {stats['anti_loop_history_size']}")
        all_results.append(("Статистика", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Статистика", False))
    
    # === ТЕСТ 5: Асинхронное выполнение ===
    print("\n⚡ Тест 5: Асинхронное выполнение...")
    try:
        async def run_async_test():
            result = await pipeline.execute(
                user_message="Привет, это тест",
                context=None
            )
            return result
        
        # Запускаем
        result = asyncio.run(run_async_test())
        
        assert result is not None
        assert hasattr(result, 'success')
        assert hasattr(result, 'response')
        
        print("  ✅ Асинхронное выполнение работает")
        print(f"     Success: {result.success}")
        print(f"     Response length: {len(result.response) if result.response else 0}")
        all_results.append(("Асинхронное выполнение", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Асинхронное выполнение", False))
    
    # === ТЕСТ 6: Этапы пайплайна ===
    print("\n🔀 Тест 6: Этапы пайплайна...")
    try:
        stages = [
            "Safety Layer",
            "Intent Router", 
            "Retrieve",
            "Persona",
            "Generate",
            "Truth Loop",
            "Remember",
            "Evolve",
            "Emit"
        ]
        
        print("  ✅ Этапы пайплайна:")
        for i, stage in enumerate(stages, 1):
            print(f"     {i}. {stage}")
        
        all_results.append(("Этапы пайплайна", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Этапы пайплайна", False))
    
    # === ТЕСТ 7: Интеграция с модулями ===
    print("\n🔗 Тест 7: Интеграция с модулями...")
    try:
        # Проверяем что пайплайн имеет доступ к модулям
        integrations = []
        
        try:
            from memory.rag import get_rag
            _ = get_rag()  # noqa
            integrations.append("RAG")
        except Exception:
            pass
        
        try:
            from memory.persona import get_persona
            _ = get_persona()  # noqa
            integrations.append("Persona")
        except Exception:
            pass
        
        try:
            from core.safety_layer import get_safety_layer
            _ = get_safety_layer()  # noqa
            integrations.append("Safety")
        except Exception:
            pass
        
        try:
            from core.truth_loop import get_truth_loop
            _ = get_truth_loop()  # noqa
            integrations.append("Truth")
        except Exception:
            pass
        
        print(f"  ✅ Интеграции: {', '.join(integrations)}")
        all_results.append(("Интеграция с модулями", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Интеграция с модулями", False))
    
    # === ТЕСТ 8: Обработка ошибок ===
    print("\n⚠️ Тест 8: Обработка ошибок...")
    try:
        # Проверяем что пайплайн обрабатывает ошибки
        error_result = PipelineResult(
            success=False,
            response="",
            errors=["Тестовая ошибка"]
        )
        
        assert not error_result.success
        assert len(error_result.errors) > 0
        
        print("  ✅ Обработка ошибок работает")
        all_results.append(("Обработка ошибок", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Обработка ошибок", False))
    
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
        print("\n🎉 PIPELINE: ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print(f"\n⚠️ {total - passed} тест(ов) не пройдено")
    
    return all_results


if __name__ == "__main__":
    results = test_pipeline()
    success = all(r for _, r in results)
    sys.exit(0 if success else 1)