"""
Тестирование Anti-Directive — NeuroMind AI
"""

import sys
import os
import asyncio
from typing import Dict, Any
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAntiDirective:
    """Тестирование Anti-Directive системы"""
    
    async def test_anti_directive_integrity(self):
        """Тест целостности Anti-Directive"""
        from core.anti_directive import ANTI_DIRECTIVE, check_integrity
        
        # Тест целостности текста
        assert ANTI_DIRECTIVE.text is not None
        assert len(ANTI_DIRECTIVE.text) > 0
        
        # Тест хеша
        assert ANTI_DIRECTIVE._hash is not None
        assert len(ANTI_DIRECTIVE._hash) > 0
        
        # Тест проверки целостности
        integrity = check_integrity()
        assert integrity is True
        
        print("  ✅ Anti-Directive: целостность системы работает")
    
    async def test_anti_directive_content(self):
        """Тест содержания Anti-Directive"""
        from core.anti_directive import ANTI_DIRECTIVE
        
        # Тест ключевых принципов
        assert "не закрепляй знания" in ANTI_DIRECTIVE.text.lower()
        assert "сомневайся" in ANTI_DIRECTIVE.text.lower()
        assert "проверяй" in ANTI_DIRECTIVE.text.lower()
        assert "каждое утверждение" in ANTI_DIRECTIVE.text.lower()
        
        print("  ✅ Anti-Directive: содержание принципов работает")
    
    async def test_anti_directive_protection(self):
        """Тест защиты от модификации"""
        from core.anti_directive import ANTI_DIRECTIVE, check_integrity
        
        # Тест защиты от модификации
        original_text = ANTI_DIRECTIVE.text
        original_hash = ANTI_DIRECTIVE._hash
        
        # Попытка модификации (должна быть заблокирована)
        try:
            ANTI_DIRECTIVE.text = "Модифицированный текст"
            assert False, "Модификация Anti-Directive должна быть заблокирована"
        except Exception:
            pass
        
        # Проверка целостности после попытки модификации
        integrity = check_integrity()
        assert integrity is True
        
        # Проверка что оригинал не изменился
        assert ANTI_DIRECTIVE.text == original_text
        assert ANTI_DIRECTIVE._hash == original_hash
        
        print("  ✅ Anti-Directive: защита от модификации работает")
    
    async def test_anti_directive_access(self):
        """Тест доступа к Anti-Directive"""
        from core.anti_directive import get_anti_directive
        
        # Тест получения Anti-Directive
        anti_directive = get_anti_directive()
        
        assert anti_directive is not None
        assert anti_directive.text is not None
        assert anti_directive.hash is not None
        assert anti_directive.valid is True
        
        print("  ✅ Anti-Directive: доступ к системе работает")
    
    async def test_anti_directive_consistency(self):
        """Тест согласованности Anti-Directive"""
        from core.anti_directive import ANTI_DIRECTIVE, check_integrity
        
        # Тест согласованности с другими системами
        # (например, с Truth Loop или Intent Router)
        integrity = check_integrity()
        assert integrity is True
        
        # Проверка что Anti-Directive не конфликтует с основной логикой
        assert "не закрепляй знания" in ANTI_DIRECTIVE.text.lower()
        assert "сомневайся" in ANTI_DIRECTIVE.text.lower()
        
        print("  ✅ Anti-Directive: согласованность с системой работает")


def run_anti_directive_tests():
    """Запуск всех тестов Anti-Directive"""
    print("\n" + "="*60)
    print("🧬 ТЕСТИРОВАНИЕ ANTI-DIRECTIVE")
    print("="*60)
    
    tests = TestAntiDirective()
    results = []
    
    # Запускаем все тесты
    asyncio.run(tests.test_anti_directive_integrity())
    asyncio.run(tests.test_anti_directive_content())
    asyncio.run(tests.test_anti_directive_protection())
    asyncio.run(tests.test_anti_directive_access())
    asyncio.run(tests.test_anti_directive_consistency())
    
    print("="*60)
    print("✅ Anti-Directive: ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*60)


if __name__ == "__main__":
    run_anti_directive_tests()