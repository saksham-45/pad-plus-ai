"""
🔀 ModelRouter v2 — Автовыбор модели

Выбирает модель на основе режима мышления:
- FAST → лёгкие/быстрые модели
- BALANCED → средние модели
- DEEP → мощные модели

Учитывает Circuit Breaker — не использует заблокированные модели.
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger("padplus.agi")


class ModelTier(Enum):
    CHEAP = "cheap"       # Лёгкие/быстрые
    MID = "mid"           # Средние
    SMART = "smart"       # Мощные


class ModelRouter:
    """
    Выбирает модель на основе режима мышления
    """

    # Модели по уровням (провайдер/модель)
    MODELS = {
        ModelTier.CHEAP: [
            "groq/llama-3.1-8b-instant",
            "groq/gemma2-9b-it",
        ],
        ModelTier.MID: [
            "groq/llama-3.1-70b-versatile",
            "groq/llama-3.3-70b-versatile",
            "google/gemini-2.0-flash",
        ],
        ModelTier.SMART: [
            "openai/gpt-4o",
            "anthropic/claude-3-5-sonnet-20241022",
            "google/gemini-1.5-pro",
        ],
    }

    # Маппинг ThinkingMode → ModelTier
    MODE_TO_TIER = {
        "fast": ModelTier.CHEAP,
        "balanced": ModelTier.MID,
        "deep": ModelTier.SMART,
    }

    def select(
        self,
        thinking_mode: str = "balanced",
        user_tier: str = "free",
        circuit_breaker=None,
    ) -> str:
        """
        Выбирает модель

        Args:
            thinking_mode: fast, balanced, deep
            user_tier: free, premium
            circuit_breaker: CircuitBreaker для проверки доступности

        Returns:
            model_name (provider/model)
        """
        # Определяем tier по режиму
        tier = self.MODE_TO_TIER.get(thinking_mode, ModelTier.MID)

        # Premium пользователи получают модели уровнем выше
        if user_tier == "premium":
            if tier == ModelTier.CHEAP:
                tier = ModelTier.MID
            elif tier == ModelTier.MID:
                tier = ModelTier.SMART

        # Получаем список моделей для tier
        models = list(self.MODELS[tier])

        # Фильтруем по circuit breaker
        if circuit_breaker:
            models = [m for m in models if circuit_breaker.allow(m)]

        # Если все модели заблокированы — пробуем следующий tier
        if not models and tier != ModelTier.SMART:
            tier = ModelTier.SMART
            models = list(self.MODELS[tier])
            if circuit_breaker:
                models = [m for m in models if circuit_breaker.allow(m)]

        # Если всё ещё пусто — fallback на первую доступную
        if not models:
            models = ["groq/llama-3.1-70b-versatile"]

        # Выбираем первую доступную
        selected = models[0]
        logger.info(f"🔀 ModelRouter: {thinking_mode} → {selected}")
        return selected

    def get_available_models(self, tier: str = "free") -> list:
        """Возвращает список всех доступных моделей"""
        all_models = []
        for tier_enum in ModelTier:
            all_models.extend(self.MODELS[tier_enum])
        return all_models


# Глобальный экземпляр
_router = None


def get_model_router() -> ModelRouter:
    """Возвращает глобальный ModelRouter"""
    global _router
    if _router is None:
        _router = ModelRouter()
        logger.info("✅ ModelRouter инициализирован")
    return _router
