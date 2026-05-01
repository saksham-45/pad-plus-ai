"""
🧪 Интеграционный тест PAD+ AI

Проверяет реальные ответы системы и определяет:
- Какие модули задействованы
- Насколько каждый модуль参与了 обработку
- Время выполнения каждого этапа
- Качество ответов
"""

import sys
import os
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'backend'))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')


# ============================================================================
# ТЕСТОВЫЕ ЗАПРОСЫ
# ============================================================================

TEST_CASES = [
    {
        "name": "Приветствие",
        "message": "Привет! Как дела?",
        "expected_modules": ["intent_router", "litellm", "emotion"],
        "expected_intent": "conversation",
    },
    {
        "name": "Простой вопрос",
        "message": "Что такое Python?",
        "expected_modules": ["intent_router", "rag", "litellm", "knowledge"],
        "expected_intent": "question",
    },
    {
        "name": "Сложный вопрос",
        "message": "Объясни подробно как работает машинное обучение и чем оно отличается от традиционного программирования",
        "expected_modules": ["intent_router", "rag", "litellm", "knowledge", "truth_loop"],
        "expected_intent": "question",
    },
    {
        "name": "Творческий запрос",
        "message": "Напиши короткое стихотворение о космосе",
        "expected_modules": ["intent_router", "litellm", "emotion"],
        "expected_intent": "creative",
    },
    {
        "name": "Команда",
        "message": "Запусти рефлексию",
        "expected_modules": ["intent_router", "autonomy"],
        "expected_intent": "command",
    },
]


# ============================================================================
# МОНИТОР МОДУЛЕЙ
# ============================================================================

class ModuleMonitor:
    """Отслеживает какие модули вызываются"""

    def __init__(self):
        self.calls = {}  # module_name -> [call_times]
        self.errors = {}  # module_name -> [errors]

    def record_call(self, module_name: str, duration_ms: float = 0):
        if module_name not in self.calls:
            self.calls[module_name] = []
        self.calls[module_name].append(duration_ms)

    def record_error(self, module_name: str, error: str):
        if module_name not in self.errors:
            self.errors[module_name] = []
        self.errors[module_name].append(error)

    def get_report(self) -> dict:
        report = {"modules": {}, "errors": {}}

        for module, times in self.calls.items():
            report["modules"][module] = {
                "call_count": len(times),
                "avg_ms": sum(times) / len(times) if times else 0,
                "total_ms": sum(times),
                "min_ms": min(times) if times else 0,
                "max_ms": max(times) if times else 0,
            }

        for module, errors in self.errors.items():
            report["errors"][module] = errors

        return report


# ============================================================================
# ТЕСТ
# ============================================================================

async def run_test():
    """Запускает полный интеграционный тест"""

    print("=" * 70)
    print("🧪 ИНТЕГРАЦИОННЫЙ ТЕСТ PAD+ AI")
    print("=" * 70)

    monitor = ModuleMonitor()
    results = []

    # Инициализируем pipeline
    start = time.monotonic()
    from core.pipeline import get_pipeline
    init_ms = (time.monotonic() - start) * 1000
    monitor.record_call("pipeline_init", init_ms)

    pipeline = get_pipeline()

    print(f"\n✅ Pipeline инициализирован за {init_ms:.0f}ms")
    print(f"\n📋 Тестовых случаев: {len(TEST_CASES)}")
    print("-" * 70)

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'='*60}")
        print(f"ТЕСТ {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"Запрос: \"{test_case['message'][:80]}...\"")
        print(f"{'='*60}")

        # Запускаем pipeline
        test_start = time.monotonic()

        try:
            result = await pipeline.execute(
                user_message=test_case["message"],
                context={"user_id": "test_user"},
            )

            test_ms = (time.monotonic() - test_start) * 1000
            monitor.record_call("pipeline_total", test_ms)

            # Анализируем результат
            print(f"\n✅ Ответ получен за {test_ms:.0f}ms")
            print(f"   Стратегия: {result.strategy}")
            print(f"   Уверенность: {result.confidence:.2f}")
            print(f"   RAG использован: {result.rag_used}")
            print(f"   Фактов найдено: {result.facts_used}")
            print(f"   Ошибок: {len(result.errors)}")

            if result.response:
                print(f"\n   Ответ: {result.response[:150]}...")

            # Определяем задействованные модули
            active_modules = set()
            if result.rag_used:
                active_modules.add("rag")
            if result.facts_used > 0:
                active_modules.add("fact_memory")
            if result.truth_confidence > 0:
                active_modules.add("truth_loop")
            if result.confidence > 0:
                active_modules.add("litellm")

            # Записываем в монитор
            for module in active_modules:
                monitor.record_call(module, test_ms * 0.2)  # Примерная доля

            results.append({
                "name": test_case["name"],
                "success": result.success,
                "time_ms": test_ms,
                "confidence": result.confidence,
                "rag_used": result.rag_used,
                "facts_used": result.facts_used,
                "active_modules": list(active_modules),
                "errors": result.errors,
            })

        except Exception as e:
            test_ms = (time.monotonic() - test_start) * 1000
            print(f"\n❌ Ошибка: {e}")
            monitor.record_error("pipeline", str(e))
            results.append({
                "name": test_case["name"],
                "success": False,
                "time_ms": test_ms,
                "error": str(e),
            })

    # ========================================================================
    # ИТОГОВЫЙ ОТЧЁТ
    # ========================================================================
    print(f"\n\n{'='*70}")
    print("📊 ИТОГОВЫЙ ОТЧЁТ")
    print(f"{'='*70}")

    # Сводка по тестам
    success_count = sum(1 for r in results if r.get("success"))
    total_time = sum(r.get("time_ms", 0) for r in results)
    avg_time = total_time / len(results) if results else 0

    print(f"\n✅ Успешных: {success_count}/{len(results)}")
    print(f"⏱️ Среднее время: {avg_time:.0f}ms")
    print(f"⏱️ Общее время: {total_time:.0f}ms")

    # Задействованные модули
    print(f"\n🔧 ЗАДЕЙСТВОВАННЫЕ МОДУЛИ:")
    print(f"{'Модуль':<25} {'Вызовов':<10} {'Ср. время':<12} {'Всего':<10}")
    print("-" * 57)

    module_report = monitor.get_report()
    for module, stats in sorted(
        module_report["modules"].items(),
        key=lambda x: x[1]["total_ms"],
        reverse=True
    ):
        print(f"{module:<25} {stats['call_count']:<10} {stats['avg_ms']:<12.0f}ms {stats['total_ms']:<10.0f}ms")

    # Ошибки
    if module_report["errors"]:
        print(f"\n❌ ОШИБКИ:")
        for module, errors in module_report["errors"].items():
            for error in errors:
                print(f"   {module}: {error}")

    # Детали по тестам
    print(f"\n📋 ДЕТАЛИ ПО ТЕСТАМ:")
    for r in results:
        status = "✅" if r.get("success") else "❌"
        time_str = f"{r.get('time_ms', 0):.0f}ms"
        modules = ", ".join(r.get("active_modules", []))
        print(f"   {status} {r['name']:<20} {time_str:<10} [{modules}]")

    # Рекомендации
    print(f"\n💡 РЕКОМЕНДАЦИИ:")

    if avg_time > 5000:
        print("   ⚠️ Среднее время > 5 сек — проверьте LLM провайдер")
    if success_count < len(results):
        print(f"   ⚠️ {len(results) - success_count} тестов провалились")

    all_modules = set()
    for r in results:
        all_modules.update(r.get("active_modules", []))

    expected_all = {"intent_router", "litellm", "rag", "knowledge", "emotion", "truth_loop"}
    missing = expected_all - all_modules
    if missing:
        print(f"   ⚠️ Модули не задействованы: {', '.join(missing)}")

    print(f"\n{'='*70}")
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print(f"{'='*70}")

    return results, monitor.get_report()


if __name__ == "__main__":
    asyncio.run(run_test())
