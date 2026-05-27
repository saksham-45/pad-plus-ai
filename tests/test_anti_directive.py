"""
Тестирование Anti-Directive — PAD+ AI
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAntiDirective:
    """Тестирование Anti-Directive системы"""

    def test_anti_directive_instance(self):
        """Тест экземпляра Anti-Directive"""
        from core.anti_directive import ANTI_DIRECTIVE
        
        assert ANTI_DIRECTIVE is not None
        assert ANTI_DIRECTIVE.text is not None
        assert len(ANTI_DIRECTIVE.text) > 0

    def test_anti_directive_hash(self):
        """Тест хеша Anti-Directive"""
        from core.anti_directive import ANTI_DIRECTIVE
        
        assert ANTI_DIRECTIVE._hash is not None
        assert len(ANTI_DIRECTIVE._hash) == 64

    def test_check_integrity(self):
        """Тест проверки целостности"""
        from core.anti_directive import check_integrity
        
        result = check_integrity()
        assert result is True

    def test_anti_directive_content(self):
        """Тест содержания Anti-Directive"""
        from core.anti_directive import ANTI_DIRECTIVE
        
        text_lower = ANTI_DIRECTIVE.text.lower()
        
        assert "сомневайся" in text_lower or "сомнева" in text_lower
        assert "гипотез" in text_lower
        assert "вопрос" in text_lower

    def test_anti_directive_immutability(self):
        """Тест неизменяемости Anti-Directive"""
        from core.anti_directive import ANTI_DIRECTIVE, check_integrity
        import numpy as np
        
        original_text = ANTI_DIRECTIVE.text
        original_hash = ANTI_DIRECTIVE._hash
        
        try:
            ANTI_DIRECTIVE.text = "Модифицированный текст"
        except (AttributeError, TypeError):
            pass
        
        assert ANTI_DIRECTIVE.text == original_text
        assert ANTI_DIRECTIVE._hash == original_hash
        assert check_integrity() is True

    def test_validate_method(self):
        """Тест метода validate"""
        from core.anti_directive import ANTI_DIRECTIVE
        
        good_knowledge = "Я думаю, что это может быть правдой, но не уверен"
        assert ANTI_DIRECTIVE.validate(good_knowledge) is True
        
        bad_knowledge = "Я абсолютно уверен что это истина в последней инстанции"
        assert ANTI_DIRECTIVE.validate(bad_knowledge) is False

    def test_get_prompt_text(self):
        """Тест получения текста для промпта"""
        from core.anti_directive import ANTI_DIRECTIVE
        
        prompt = ANTI_DIRECTIVE.get_prompt_text()
        
        assert prompt is not None
        assert "ANTI_DIRECTIVE" in prompt
        assert ANTI_DIRECTIVE.text in prompt


class TestAntiDirectivePatterns:
    """Тестирование паттернов валидации"""

    def test_forbidden_patterns(self):
        """Тест запрещённых паттернов"""
        from core.anti_directive import ANTI_DIRECTIVE
        
        forbidden_phrases = [
            "точно знаю",
            "абсолютно уверен",
            "никогда не сомневаюсь",
            "это истина",
            "никогда не меняется"
        ]
        
        for phrase in forbidden_phrases:
            knowledge_with_phrase = f"Я думаю что {phrase} в этом вопросе"
            assert ANTI_DIRECTIVE.validate(knowledge_with_phrase) is False

    def test_allowed_patterns(self):
        """Тест разрешённых паттернов"""
        from core.anti_directive import ANTI_DIRECTIVE
        
        allowed_phrases = [
            "Я думаю что",
            "Возможно",
            "Вероятно",
            "Скорее всего",
            "На мой взгляд"
        ]
        
        for phrase in allowed_phrases:
            knowledge_with_phrase = f"{phrase}, это может быть так"
            assert ANTI_DIRECTIVE.validate(knowledge_with_phrase) is True

    def test_case_insensitivity(self):
        """Тест регистронезависимости"""
        from core.anti_directive import ANTI_DIRECTIVE
        
        text_upper = "АБСОЛЮТНО УВЕРЕН"
        text_lower = "абсолютно уверен"
        
        assert ANTI_DIRECTIVE.validate(text_lower) is False
        assert ANTI_DIRECTIVE.validate(text_upper) is False