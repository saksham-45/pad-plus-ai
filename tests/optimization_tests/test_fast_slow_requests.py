"""
Тесты автоматического определения быстрых/медленных запросов

Проверяет функцию is_fast_request() в frontend_routes.py
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


class TestFastRequestDetection:
    """Тесты определения быстрых запросов"""

    def test_greetings_are_fast(self):
        """Приветствия определяются как быстрые"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Привет!") is True
        assert is_fast_request("Здравствуй!") is True
        assert is_fast_request("Hello!") is True
        assert is_fast_request("Hi!") is True

    def test_thanks_are_fast(self):
        """Благодарности определяются как быстрые"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Спасибо!") is True
        assert is_fast_request("Благодарю!") is True
        assert is_fast_request("Thank you!") is True

    def test_goodbyes_are_fast(self):
        """Прощания определяются как быстрые"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Пока!") is True
        assert is_fast_request("До свидания!") is True
        assert is_fast_request("Goodbye!") is True

    def test_short_answers_are_fast(self):
        """Короткие ответы определяются как быстрые"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Да") is True
        assert is_fast_request("Нет") is True
        assert is_fast_request("OK") is True
        assert is_fast_request("Хорошо") is True

    def test_short_questions_are_fast(self):
        """Короткие вопросы определяются как быстрые"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Что это?") is True
        assert is_fast_request("Кто это?") is True
        assert is_fast_request("Где ты?") is True
        assert is_fast_request("Когда придёшь?") is True

    def test_complex_questions_are_slow(self):
        """Сложные вопросы определяются как медленные"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Почему небо голубое?") is False
        assert is_fast_request("Как работает квантовая физика?") is False
        assert is_fast_request("Объясни теорию относительности") is False
        assert is_fast_request("Сравни Python и JavaScript") is False

    def test_analysis_requests_are_slow(self):
        """Запросы на анализ определяются как медленные"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Проанализируй этот текст") is False
        assert is_fast_request("Составь план изучения Python") is False
        assert is_fast_request("Как сделать домашнюю страницу?") is False

    def test_memory_requests_are_slow(self):
        """Запросы к памяти определяются как медленные"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Вспомни, что я спрашивал") is False
        assert is_fast_request("Что я спрашивал на прошлой неделе?") is False
        assert is_fast_request("Что ты знаешь о квантовой физике?") is False

    def test_opinion_requests_are_slow(self):
        """Запросы мнения определяются как медленные"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Какое твоё мнение об этом?") is False
        assert is_fast_request("Что ты думаешь о политике?") is False

    def test_long_text_is_slow(self):
        """Длинный текст определяется как медленный"""
        from backend.api.frontend_routes import is_fast_request
        
        long_text = "Это очень длинный вопрос который содержит много слов " * 3
        assert is_fast_request(long_text) is False

    def test_auto_mode_parameter(self):
        """Проверяет, что auto_mode параметр работает"""
        from backend.api.frontend_routes import ChatRequest
        
        # По умолчанию auto_mode=True
        request1 = ChatRequest(message="Привет!")
        assert request1.auto_mode is True
        
        # Можно отключить
        request2 = ChatRequest(message="Привет!", auto_mode=False)
        assert request2.auto_mode is False

    def test_chat_response_fields(self):
        """Проверяет, что ChatResponse имеет новые поля"""
        from backend.api.frontend_routes import ChatResponse
        from datetime import datetime
        
        response = ChatResponse(
            text="Ответ",
            model="test-model",
            provider="test",
            usage={"total_tokens": 100},
            timestamp=datetime.now().isoformat(),
            is_fast_mode=True,
            confidence=0.85,
            truth_confidence=0.92,
            rag_used=True,
            facts_used=3
        )
        
        assert response.is_fast_mode is True
        assert response.confidence == 0.85
        assert response.truth_confidence == 0.92
        assert response.rag_used is True
        assert response.facts_used == 3


class TestFastRequestEdgeCases:
    """Тесты граничных случаев"""

    def test_empty_string(self):
        """Пустая строка"""
        from backend.api.frontend_routes import is_fast_request
        
        result = is_fast_request("")
        # Пустая строка — быстрая (короткая)
        assert result is True

    def test_whitespace_only(self):
        """Только пробелы"""
        from backend.api.frontend_routes import is_fast_request
        
        result = is_fast_request("   ")
        assert result is True

    def test_mixed_case(self):
        """Смешанный регистр"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("ПРИВЕТ!") is True
        assert is_fast_request("ПрИвЕт!") is True
        assert is_fast_request("СПАСИБО!") is True

    def test_with_emoji(self):
        """С эмодзи"""
        from backend.api.frontend_routes import is_fast_request
        
        assert is_fast_request("Привет! 👋") is True
        assert is_fast_request("Спасибо! 😊") is True

    def test_question_without_mark(self):
        """Вопрос без вопросительного знака"""
        from backend.api.frontend_routes import is_fast_request
        
        # Короткий вопрос без "?" — быстрый
        assert is_fast_request("Как дела") is True
        
        # Длинный вопрос без "?" — всё ещё быстрый (если нет сложных паттернов)
        result = is_fast_request("Расскажи мне историю")
        assert result is True

    def test_partial_matches(self):
        """Частичные совпадения паттернов"""
        from backend.api.frontend_routes import is_fast_request
        
        # "привет" содержится в "приветствие"
        assert is_fast_request("У меня приветливое настроение") is True
        
        # "спасибо" содержится в "спасибочки"
        assert is_fast_request("Спасибочки!") is True
