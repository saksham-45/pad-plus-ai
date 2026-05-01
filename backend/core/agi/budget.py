"""
🧠 CognitiveBudget — Определяет режим мышления

Анализирует сложность запроса и выбирает режим:
- FAST — простые запросы (приветствия, короткие вопросы)
- BALANCED — средние запросы (обычные вопросы)
- DEEP — сложные запросы (анализ, объяснения, творчество)
"""

import logging
from enum import Enum

logger = logging.getLogger("padplus.agi")


class ThinkingMode(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


class CognitiveBudget:
    """
    Определяет бюджет мышления на основе сложности запроса
    """

    # Сложные слова/фразы
    COMPLEX_WORDS = [
        "почему", "как работает", "объясни", "проанализируй",
        "сравни", "разбери", "детально", "подробно", "глубоко",
        "архитектура", "алгоритм", "механизм", "принцип",
        "философ", "этик", "метафиз", "онтолог",
    ]

    # Простые слова/фразы
    SIMPLE_WORDS = [
        "привет", "здравствуй", "как дела", "что делаешь",
        "спасибо", "пока", "до свидания", "ок", "хорошо",
    ]

    def allocate(self, message: str, memory_results: list = None) -> ThinkingMode:
        """
        Выделяет режим мышления на основе сообщения

        Args:
            message: Текст запроса
            memory_results: Результаты поиска в памяти

        Returns:
            ThinkingMode
        """
        complexity = self.estimate_complexity(message, memory_results)

        if complexity < 0.3:
            return ThinkingMode.FAST
        elif complexity < 0.7:
            return ThinkingMode.BALANCED
        else:
            return ThinkingMode.DEEP

    def estimate_complexity(self, message: str, memory_results: list = None) -> float:
        """
        Оценивает сложность запроса (0.0 - 1.0)

        Факторы:
        - Длина сообщения
        - Наличие сложных слов
        - Наличие простых слов
        - Есть ли контекст из памяти
        """
        score = 0.3  # Базовая сложность
        msg_lower = message.lower()

        # Длина сообщения
        if len(message) > 200:
            score += 0.3
        elif len(message) > 100:
            score += 0.2
        elif len(message) > 50:
            score += 0.1

        # Сложные слова
        complex_count = sum(1 for word in self.COMPLEX_WORDS if word in msg_lower)
        if complex_count >= 2:
            score += 0.3
        elif complex_count >= 1:
            score += 0.2

        # Простые слова (уменьшают сложность)
        simple_count = sum(1 for word in self.SIMPLE_WORDS if word in msg_lower)
        if simple_count >= 1:
            score -= 0.2

        # Есть контекст из памяти
        if memory_results and len(memory_results) > 3:
            score += 0.2
        elif memory_results and len(memory_results) > 0:
            score += 0.1

        # Вопросы с несколькими частями
        if message.count("?") > 1:
            score += 0.1

        return max(0.0, min(score, 1.0))


# Глобальный экземпляр
_budget = None


def get_cognitive_budget() -> CognitiveBudget:
    """Возвращает глобальный CognitiveBudget"""
    global _budget
    if _budget is None:
        _budget = CognitiveBudget()
        logger.info("✅ CognitiveBudget инициализирован")
    return _budget
