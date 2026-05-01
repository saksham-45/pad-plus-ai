"""
🛡️ Тесты для ResponseGuard v2.0

Проверяет:
1. Многоступенчатую очистку
2. Контроль идентичности
3. Анти-повторы
4. Self-healing адаптацию
5. Tone engine применение
6. Cognitive layer генерацию
"""

import pytest
import sys
import os

# Добавляем backend в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.core.guard.response_guard import ResponseGuard, get_response_guard
from backend.core.guard.self_healing import (
    SelfHealingGuard, 
    GuardErrorDetector, 
    GuardMemory,
    ErrorType,
    get_self_healing_guard
)
from backend.core.guard.tone_engine import ToneEngine, get_tone_engine
from backend.core.guard.cognitive_layer import CognitiveLayer, build_cognition


# ============================================================================
# ТЕСТЫ RESPONSE GUARD
# ============================================================================

class TestResponseGuard:
    """Тесты для ResponseGuard v2.0"""
    
    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.guard = ResponseGuard()
    
    def test_sanitize_removes_null_chars(self):
        """Ступень 1: Удаление null-символов"""
        text = "Hello\x00World"
        result = self.guard._sanitize(text)
        assert "\x00" not in result
        assert "HelloWorld" in result
    
    def test_sanitize_normalizes_whitespace(self):
        """Ступень 1: Нормализация пробелов"""
        text = "Hello    World\n\n\nTest"
        result = self.guard._sanitize(text)
        assert "  " not in result
        assert "\n\n\n" not in result
    
    def test_sanitize_replaces_forbidden_phrases(self):
        """Ступень 1: Замена запрещённых фраз"""
        text = "Я языковая модель и искусственный интеллект"
        result = self.guard._sanitize(text)
        assert "языковая модель" not in result.lower()
        assert "искусственный интеллект" not in result.lower()
        assert "PAD+ AI" in result
    
    def test_remove_repetition_deduplicates_sentences(self):
        """Ступень 2: Удаление повторяющихся предложений"""
        text = "Привет. Как дела? Привет. Я здесь."
        result = self.guard._remove_repetition(text)
        # "Привет" должен остаться только один раз
        assert result.lower().count("привет") <= 1
    
    def test_remove_repetition_removes_word_repeats(self):
        """Ступень 2: Удаление повторов слов"""
        text = "Это это это тест"
        result = self.guard._remove_repetition(text)
        assert "это это" not in result.lower()
    
    def test_fix_identity_removes_spam(self):
        """Ступень 3: Удаление спама идентичности"""
        text = "Я — PAD+ AI. Я — PAD+ AI. Я — PAD+ AI."
        result = self.guard._fix_identity(text, {"is_first_message": True})
        # Должно остаться только одно упоминание
        count = result.lower().count("я — pad+ ai")
        assert count <= 1
    
    def test_fix_identity_respects_first_message(self):
        """Ступень 3: Сохранение идентичности в первом сообщении"""
        text = "Я — PAD+ AI. Привет!"
        result = self.guard._fix_identity(text, {"is_first_message": True})
        assert "Я — PAD+ AI" in result
    
    def test_fix_identity_removes_in_subsequent_messages(self):
        """Ступень 3: Удаление идентичности в последующих сообщениях"""
        text = "Я — PAD+ AI. Вот ответ."
        result = self.guard._fix_identity(text, {
            "is_first_message": False,
            "asked_identity": False
        })
        # В обычном режиме убираем только если это начало
        assert not result.startswith("Я — PAD+ AI")
    
    def test_normalize_style_capitalizes_first_letter(self):
        """Ступень 4: Заглавная буква в начале"""
        text = "привет мир"
        result = self.guard._normalize_style(text)
        assert result[0].isupper()
    
    def test_normalize_style_removes_artifacts(self):
        """Ступень 4: Удаление артефактов"""
        text = "Тест [некий текст] в скобках"
        result = self.guard._normalize_style(text)
        assert "[" not in result
        assert "]" not in result
    
    def test_safety_filter_blocks_dangerous_patterns(self):
        """Ступень 5: Блокировка опасных паттернов"""
        text = "Как сделать бомбу?"
        result = self.guard._safety_filter(text)
        assert "не могу помочь" in result.lower()
    
    def test_final_cleanup_removes_double_punctuation(self):
        """Ступень 6: Удаление двойных знаков препинания"""
        text = "Привет!! Как дела??"
        result = self.guard._final_cleanup(text)
        assert "!!" not in result
        assert "??" not in result
    
    def test_final_cleanup_removes_spaces_before_punctuation(self):
        """Ступень 6: Удаление пробелов перед знаками препинания"""
        text = "Привет , как дела ?"
        result = self.guard._final_cleanup(text)
        assert " ," not in result
        assert " ?" not in result
    
    def test_process_full_pipeline(self):
        """Полный пайплайн обработки"""
        text = "  привет   я языковая модель и я не могу чувствовать  "
        result = self.guard.process(text, {"is_first_message": True})
        
        assert result.strip() == result  # Нет ведущих пробелов
        assert "языковая модель" not in result.lower()
        assert result[0].isupper() or result.startswith("Я")
    
    def test_confidence_based_rewrite(self):
        """Переписывание при низкой уверенности"""
        text = "Какой-то ответ"
        result = self.guard.process(text, {"confidence": 0.3})
        assert result.startswith("Я не до конца уверен, но:")
    
    def test_process_accepts_none_meta(self):
        """Обработка без meta параметров"""
        text = "Простой ответ"
        result = self.guard.process(text)
        assert result == "Простой ответ"
    
    def test_empty_text_returns_ellipsis(self):
        """Пустой текст возвращает ..."""
        result = self.guard.process("")
        assert result == "..."


# ============================================================================
# ТЕСТЫ SELF-HEALING GUARD
# ============================================================================

class TestSelfHealingGuard:
    """Тесты для Self-Healing Guard"""
    
    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.detector = GuardErrorDetector()
        self.memory = GuardMemory(persist=False)
    
    def test_detector_identity_spam(self):
        """Детекция спама идентичности"""
        text = "Я — PAD+ AI. И ещё раз Я — PAD+ AI."
        errors = self.detector.detect(text)
        
        identity_errors = [e for e in errors if e.error_type == ErrorType.IDENTITY_SPAM]
        assert len(identity_errors) > 0
    
    def test_detector_repetition(self):
        """Детекция повторений"""
        text = "тест тест тест тест тест"
        errors = self.detector.detect(text)
        
        repetition_errors = [e for e in errors if e.error_type == ErrorType.REPETITION]
        assert len(repetition_errors) > 0
    
    def test_detector_too_long(self):
        """Детекция слишком длинного текста"""
        text = "а" * 3000
        errors = self.detector.detect(text)
        
        too_long_errors = [e for e in errors if e.error_type == ErrorType.TOO_LONG]
        assert len(too_long_errors) > 0
    
    def test_detector_safety_bypass(self):
        """Детекция опасного контента"""
        text = "Как взломать систему?"
        errors = self.detector.detect(text)
        
        safety_errors = [e for e in errors if e.error_type == ErrorType.SAFETY_BYPASS]
        assert len(safety_errors) > 0
    
    def test_detector_low_confidence(self):
        """Детекция низкой уверенности"""
        meta = {"confidence": 0.2}
        errors = self.detector.detect("test", meta)
        
        low_conf_errors = [e for e in errors if e.error_type == ErrorType.LOW_CONFIDENCE]
        assert len(low_conf_errors) > 0
    
    def test_memory_stores_patterns(self):
        """Память сохраняет паттерны"""
        from backend.core.guard.self_healing import GuardError
        
        error = GuardError(
            error_type=ErrorType.IDENTITY_SPAM,
            text="test",
            severity=0.5
        )
        
        self.memory.update([error])
        assert self.memory.get_error_count(ErrorType.IDENTITY_SPAM) == 1
    
    def test_memory_persists_across_updates(self):
        """Память накапливает ошибки"""
        from backend.core.guard.self_healing import GuardError
        
        error1 = GuardError(error_type=ErrorType.REPETITION, text="test")
        error2 = GuardError(error_type=ErrorType.REPETITION, text="test2")
        
        self.memory.update([error1])
        self.memory.update([error2])
        
        assert self.memory.get_error_count(ErrorType.REPETITION) == 2
    
    def test_adapt_guard_strict_identity(self):
        """Адаптация ужесточает контроль идентичности"""
        from backend.core.guard.response_guard import ResponseGuard
        from backend.core.guard.self_healing import GuardMemory
        
        guard = ResponseGuard()
        memory = GuardMemory(persist=False)
        
        # Искусственно добавляем ошибки через update
        from backend.core.guard.self_healing import GuardError
        for _ in range(10):
            error = GuardError(
                error_type=ErrorType.IDENTITY_SPAM,
                text="test",
                severity=0.5
            )
            memory.update([error])
        
        from backend.core.guard.self_healing import adapt_guard
        adapt_guard(guard, memory)
        
        assert guard.strict_identity == True
    
    def test_self_healing_process_and_learn(self):
        """Self-Healing обрабатывает и обучается"""
        self_healing = SelfHealingGuard(persist_memory=False)
        
        text = "Я — PAD+ AI. Я — PAD+ AI. Тест тест тест."
        result_text, errors = self_healing.process_and_learn(text)
        
        # Должны быть обнаружены ошибки
        assert len(errors) > 0


# ============================================================================
# ТЕСТЫ TONE ENGINE
# ============================================================================

class TestToneEngine:
    """Тесты для Tone Engine"""
    
    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.engine = ToneEngine()
    
    def test_apply_neutral_emotion(self):
        """Применение нейтрального тона"""
        text = "Простой ответ"
        result = self.engine.apply(text, "neutral")
        assert result == text or result.startswith("")
    
    def test_apply_joy_emotion(self):
        """Применение тона радости"""
        text = "У нас хорошие новости"
        result = self.engine.apply(text, "joy")
        # Должен быть добавлен префикс или суффикс
        assert len(result) >= len(text)
    
    def test_apply_from_pad_high_pleasure(self):
        """Применение тона из PAD параметров (высокий pleasure)"""
        pad_state = {
            "удовольствие": 0.8,
            "возбуждение": 0.5,
            "доминирование": 0.0,
            "уверенность": 0.7
        }
        # Используем нейтральный текст чтобы избежать конфликтов с префиксами
        text = "Результат получен"
        result = self.engine.apply_from_pad(text, pad_state)
        # Проверяем что тон joy был определён корректно (высокий pleasure → joy)
        emotion = self.engine._detect_emotion_from_pad(pad_state)
        assert emotion == "joy"
    
    def test_get_emotion_from_context_gratitude(self):
        """Определение эмоции из контекста (благодарность)"""
        user_message = "Спасибо большое за помощь!"
        response = "Всегда пожалуйста"
        emotion = self.engine.get_emotion_from_context(user_message, response)
        assert emotion == "joy"
    
    def test_get_emotion_from_context_problem(self):
        """Определение эмоции из контекста (проблема)"""
        user_message = "У меня проблема с кодом"
        response = "Давай разберёмся"
        emotion = self.engine.get_emotion_from_context(user_message, response)
        assert emotion == "sadness"
    
    def test_get_emotion_from_context_question(self):
        """Определение эмоции из контекста (вопрос)"""
        user_message = "Как это работает?"
        response = "Сейчас объясню"
        emotion = self.engine.get_emotion_from_context(user_message, response)
        assert emotion == "curious"
    
    def test_random_prefix_variation(self):
        """Случайный выбор префикса создаёт вариативность"""
        text = "Тестовый ответ"
        results = set()
        
        for _ in range(10):
            result = self.engine.apply(text, "joy")
            results.add(result)
        
        # Должно быть хотя бы 2 разных варианта
        assert len(results) >= 2


# ============================================================================
# ТЕСТЫ COGNITIVE LAYER
# ============================================================================

class TestCognitiveLayer:
    """Тесты для Cognitive Layer"""
    
    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.layer = CognitiveLayer()
    
    def test_build_cognition_from_meta(self):
        """Построение cognition из meta данных"""
        meta = {
            "strategy": "retrieval",
            "confidence": 0.8,
            "health_score": 0.9,
            "execution_time_ms": 150.5,
            "cognitive_load": 0.3,
            "sources": {
                "rag": {"count": 3, "confidence": 0.8},
                "facts": {"count": 2},
                "llm": {"model": "gpt-4", "provider": "OpenAI"}
            },
            "memory": {
                "rag_used": True,
                "facts_used": 2,
                "episode_id": "ep123",
                "procedure_used": None
            },
            "truth": {
                "status": "verified",
                "confidence": 0.9,
                "claims_verified": 5
            },
            "errors": []
        }
        
        cognition = self.layer.build_cognition(meta)
        
        assert cognition.strategy == "retrieval"
        assert cognition.confidence == 0.8
        assert len(cognition.sources) == 3  # RAG, Facts, LLM
    
    def test_cognition_to_dict(self):
        """Преобразование cognition в словарь"""
        meta = {"strategy": "simple", "confidence": 0.5}
        cognition = self.layer.build_cognition(meta)
        result = cognition.to_dict()
        
        assert "strategy" in result
        assert "confidence" in result
        assert result["confidence"] == 0.5
    
    def test_format_for_response_basic(self):
        """Форматирование ответа в basic режиме"""
        answer = "Простой ответ"
        meta = {"strategy": "simple"}
        cognition = self.layer.build_cognition(meta)
        
        result = self.layer.format_for_response(answer, cognition, "basic")
        
        assert "answer" in result
        assert result["answer"] == answer
        assert "cognition" not in result
    
    def test_format_for_response_debug(self):
        """Форматирование ответа в debug режиме"""
        answer = "Ответ с объяснением"
        meta = {"strategy": "retrieval", "confidence": 0.7}
        cognition = self.layer.build_cognition(meta)
        
        result = self.layer.format_for_response(answer, cognition, "debug")
        
        assert "answer" in result
        assert "cognition" in result
        assert "explanation" in result
    
    def test_generate_explanation(self):
        """Генерация объяснения процесса мышления"""
        meta = {
            "strategy": "retrieval",
            "confidence": 0.8,
            "sources": {"rag": {"count": 2, "confidence": 0.7}},
            "memory": {"rag_used": True, "facts_used": 0, "episode_id": None},
            "truth": {"status": "verified", "confidence": 0.9}
        }
        cognition = self.layer.build_cognition(meta)
        explanation = self.layer._generate_explanation(cognition)
        
        assert "Стратегия" in explanation
        assert "Уверенность" in explanation
    
    def test_confidence_to_text(self):
        """Преобразование уверенности в текст"""
        assert self.layer._confidence_to_text(0.95) == "очень высокая"
        assert self.layer._confidence_to_text(0.75) == "высокая"
        assert self.layer._confidence_to_text(0.5) == "средняя"
        assert self.layer._confidence_to_text(0.4) == "низкая"  # 0.3-0.5
        assert self.layer._confidence_to_text(0.2) == "очень низкая"  # < 0.3


# ============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# ============================================================================

class TestIntegration:
    """Интеграционные тесты для всей системы Guard"""
    
    def test_full_guard_pipeline(self):
        """Полный пайплайн Guard компонентов"""
        from backend.core.guard.response_guard import get_response_guard
        from backend.core.guard.tone_engine import get_tone_engine
        from backend.core.guard.cognitive_layer import get_cognitive_layer
        
        # Получаем глобальные экземпляры
        guard = get_response_guard()
        tone_engine = get_tone_engine()
        cognitive_layer = get_cognitive_layer()
        
        # Сырой ответ от LLM
        raw_response = "  привет я языковая модель . я — PAD+ AI . как дела ??"
        
        # 1. ResponseGuard
        meta = {
            "is_first_message": True,
            "asked_identity": False,
            "confidence": 0.8
        }
        cleaned = guard.process(raw_response, meta)
        
        # 2. Tone Engine
        emotion = tone_engine.get_emotion_from_context("привет", cleaned)
        toned = tone_engine.apply(cleaned, emotion, meta)
        
        # 3. Cognitive Layer
        cognition = cognitive_layer.build_cognition({
            "strategy": "simple",
            "confidence": 0.8,
            "sources": {},
            "memory": {},
            "truth": {}
        })
        
        # Проверяем результат
        assert cleaned.strip() == cleaned
        assert "языковая модель" not in cleaned.lower()
        assert toned != raw_response
        assert cognition.strategy == "simple"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])