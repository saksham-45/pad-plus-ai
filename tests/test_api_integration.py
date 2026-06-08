"""
Интеграционные тесты API — NeuroMind AI
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_api_integration():
    """Интеграционные тесты API"""
    print("\n" + "="*60)
    print("🌐 ИНТЕГРАЦИОННЫЕ ТЕСТЫ API")
    print("="*60)
    
    all_results = []
    
    # === ТЕСТ 1: Инициализация роутера ===
    print("\n📦 Тест 1: Инициализация роутера...")
    try:
        from api.routes import router
        
        assert router is not None
        print("  ✅ Router инициализирован")
        all_results.append(("Router", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Router", False))
    
    # === ТЕСТ 2: Эндпоинты Personas ===
    print("\n🎭 Тест 2: Эндпоинты Persona...")
    try:
        from memory.persona import get_persona
        
        persona = get_persona()
        stats = persona.get_stats()
        traits = persona.get_all_traits()
        
        assert "traits_count" in stats
        assert len(traits) > 0
        
        print("  ✅ Persona API:")
        print(f"     Черты: {stats['traits_count']}")
        print(f"     Взаимодействий: {stats['total_interactions']}")
        all_results.append(("Persona API", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Persona API", False))
    
    # === ТЕСТ 3: Эндпоинты Pipeline ===
    print("\n🔄 Тест 3: Эндпоинты Pipeline...")
    try:
        from core.pipeline import get_pipeline
        
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        
        assert "total_calls" in stats
        
        print("  ✅ Pipeline API:")
        print(f"     Вызовов: {stats['total_calls']}")
        all_results.append(("Pipeline API", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Pipeline API", False))
    
    # === ТЕСТ 4: Эндпоинты Hygiene ===
    print("\n🧹 Тест 4: Эндпоинты Hygiene...")
    try:
        from memory.hygiene import get_hygiene
        
        hygiene = get_hygiene()
        stats = hygiene.get_memory_stats()
        
        assert "total_cleanups" in stats
        
        print("  ✅ Hygiene API:")
        print(f"     Очисток: {stats['total_cleanups']}")
        all_results.append(("Hygiene API", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Hygiene API", False))
    
    # === ТЕСТ 5: Mind State API ===
    print("\n🧠 Тест 5: Mind State API...")
    try:
        # Собираем состояние из всех модулей
        state = {}
        
        try:
            from emotion.pad_model import get_pad_model
            pad = get_pad_model()
            state["emotion"] = pad.get_state().to_dict()
        except Exception:
            state["emotion"] = {}
        
        try:
            from memory.rag import get_rag
            rag = get_rag()
            state["rag"] = rag.get_stats()
        except Exception:
            state["rag"] = {}
        
        state["facts"] = state.get("rag", {})
        
        print("  ✅ Mind State собран:")
        print(f"     Эмоции: {len(state.get('emotion', {}))} полей")
        print(f"     RAG: {state.get('rag', {}).get('total_dialogs', 0)} диалогов")
        print(f"     Факты: {state.get('facts', {}).get('total_facts', 0)}")
        all_results.append(("Mind State API", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Mind State API", False))
    
    # === ТЕСТ 6: Chat API ===
    print("\n💬 Тест 6: Chat API...")
    try:
        from core.pipeline import get_pipeline
        
        pipeline = get_pipeline()
        
        async def test_chat():
            result = await pipeline.execute(
                user_message="Тестовое сообщение",
                context=None
            )
            return result
        
        result = asyncio.run(test_chat())
        
        assert result is not None
        
        print("  ✅ Chat API:")
        print(f"     Success: {result.success}")
        print(f"     Provider: {result.provider}")
        all_results.append(("Chat API", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Chat API", False))
    
    # === ТЕСТ 7: RAG API ===
    print("\n📚 Тест 7: RAG API...")
    try:
        from memory.rag import get_rag
        
        rag = get_rag()
        stats = rag.get_stats()
        
        # Тест поиска
        results = rag.search("тест", n_results=3)
        
        print("  ✅ RAG API:")
        print(f"     Диалогов: {stats.get('total_dialogs', 0)}")
        print(f"     Результатов поиска: {len(results)}")
        all_results.append(("RAG API", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("RAG API", False))
    
    # === ТЕСТ 8: Knowledge Graph API ===
    print("\n🕸️ Тест 8: Knowledge Graph API...")
    try:
        from knowledge.graph import get_knowledge_graph
        
        graph = get_knowledge_graph()
        stats = graph.get_stats()
        
        print("  ✅ Knowledge Graph API:")
        print(f"     Узлов: {stats.get('nodes', 0)}")
        print(f"     Связей: {stats.get('edges', 0)}")
        all_results.append(("Knowledge Graph API", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Knowledge Graph API", False))
    
    # === ТЕСТ 9: Safety API ===
    print("\n🛡️ Тест 9: Safety API...")
    try:
        from core.safety_layer import get_safety_layer
        
        safety = get_safety_layer()
        stats = safety.get_stats()
        
        # Тест проверки
        result = safety.check_request("Обычный запрос")
        
        print("  ✅ Safety API:")
        print(f"     Passed: {result.passed}")
        print(f"     Strict mode: {stats.get('strict_mode', False)}")
        all_results.append(("Safety API", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Safety API", False))
    
    # === ТЕСТ 10: Analytics API ===
    print("\n📊 Тест 10: Analytics API...")
    try:
        from analytics.metrics import get_analytics
        
        analytics = get_analytics()
        report = analytics.get_full_report(days=7)
        
        assert "dashboard" in report
        
        print("  ✅ Analytics API:")
        print(f"     Сообщений: {report['dashboard'].get('total_messages', 0)}")
        all_results.append(("Analytics API", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Analytics API", False))
    
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
        print("\n🎉 API: ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print(f"\n⚠️ {total - passed} тест(ов) не пройдено")
    
    return all_results


if __name__ == "__main__":
    results = test_api_integration()
    success = all(r for _, r in results)
    sys.exit(0 if success else 1)