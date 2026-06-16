"""
Тестирование модуля Persona — Личность
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_persona():
    """Тестирование персоны"""
    print("\n" + "="*60)
    print("🎭 ТЕСТИРОВАНИЕ PERSONA")
    print("="*60)
    
    all_results = []
    
    # === ТЕСТ 1: Инициализация ===
    print("\n📦 Тест 1: Инициализация персоны...")
    try:
        from memory.persona import get_persona
        
        persona = get_persona()
        assert persona is not None
        print("  ✅ Персона инициализирована")
        all_results.append(("Инициализация", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Инициализация", False))
        return all_results
    
    # === ТЕСТ 2: Черты характера ===
    print("\n🧬 Тест 2: Черты характера...")
    try:
        traits = persona.get_all_traits()
        assert len(traits) > 0
        print(f"  ✅ Загружено {len(traits)} черт")
        
        # Проверяем структуру
        for key, trait in list(traits.items())[:3]:
            assert hasattr(trait, 'name')
            assert hasattr(trait, 'value')
            assert 0 <= trait.value <= 1
            print(f"     • {trait.name}: {trait.value:.2f}")
        
        all_results.append(("Черты характера", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Черты характера", False))
    
    # === ТЕСТ 3: Корректировка черт ===
    print("\n⚙️ Тест 3: Корректировка черт...")
    try:
        # Получаем текущее значение
        initial_traits = persona.get_all_traits()
        first_key = list(initial_traits.keys())[0]
        initial_value = initial_traits[first_key].value
        
        # Корректируем
        success = persona.adjust_trait(first_key, 0.1)
        assert success
        
        # Проверяем изменение
        updated_traits = persona.get_all_traits()
        new_value = updated_traits[first_key].value
        
        # Возвращаем обратно
        persona.adjust_trait(first_key, -0.1)
        
        print(f"  ✅ Корректировка работает")
        print(f"     {first_key}: {initial_value:.2f} → {new_value:.2f}")
        all_results.append(("Корректировка черт", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Корректировка черт", False))
    
    # === ТЕСТ 4: Доминирующие черты ===
    print("\n👑 Тест 4: Доминирующие черты...")
    try:
        dominant = persona.get_dominant_traits(n=3)
        assert len(dominant) > 0
        print(f"  ✅ Найдено {len(dominant)} доминирующих черт")
        for trait_name in dominant:
            print(f"     • {trait_name}")
        all_results.append(("Доминирующие черты", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Доминирующие черты", False))
    
    # === ТЕСТ 5: Рефлексия ===
    print("\n🪞 Тест 5: Саморефлексия...")
    try:
        # Добавляем рефлексию
        persona.add_reflection(
            insight="Тестовая рефлексия",
            action="Проверка функционала",
            confidence=0.8
        )
        
        # Получаем историю
        reflections = persona.get_recent_reflections(limit=5)
        assert len(reflections) > 0
        
        print(f"  ✅ Рефлексия работает")
        print(f"     Всего рефлексий: {len(persona.reflections)}")
        all_results.append(("Саморефлексия", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Саморефлексия", False))
    
    # === ТЕСТ 6: Контекст для промптов ===
    print("\n📝 Тест 6: Контекст личности...")
    try:
        context = persona.get_persona_context()
        assert len(context) > 0
        assert "Черты характера" in context or "Доминирующие" in context
        print(f"  ✅ Контекст генерируется")
        print(f"     Длина: {len(context)} символов")
        all_results.append(("Контекст личности", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Контекст личности", False))
    
    # === ТЕСТ 7: Статистика ===
    print("\n📊 Тест 7: Статистика...")
    try:
        stats = persona.get_stats()
        assert "traits_count" in stats
        assert "total_interactions" in stats
        print(f"  ✅ Статистика:")
        print(f"     Черты: {stats['traits_count']}")
        print(f"     Взаимодействий: {stats['total_interactions']}")
        print(f"     Рефлексий: {stats['reflections_count']}")
        all_results.append(("Статистика", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Статистика", False))
    
    # === ТЕСТ 8: Ценности и принципы ===
    print("\n💎 Тест 8: Ценности и принципы...")
    try:
        values = persona.values
        principles = persona.principles
        
        assert len(values) > 0
        assert len(principles) > 0
        
        print(f"  ✅ Ценности: {len(values)}")
        for v in list(values)[:3]:
            print(f"     • {v}")
        print(f"  ✅ Принципы: {len(principles)}")
        all_results.append(("Ценности и принципы", True))
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        all_results.append(("Ценности и принципы", False))
    
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
        print("\n🎉 PERSONA: ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print(f"\n⚠️ {total - passed} тест(ов) не пройдено")
    
    return all_results


if __name__ == "__main__":
    results = test_persona()
    success = all(r for _, r in results)
    sys.exit(0 if success else 1)