"""Адаптивные стратегии для выбора диагностов и патчей."""

from __future__ import annotations

from typing import Any


class AdaptiveStrategies:
    """Стратегии выбора на основе MetaLearner.

    Использует статистику успешности для принятия решений:
    - какой паттерн выбрать для данного детектора
    - стоит ли доверять диагносту (на основе веса)
    - изменять ли пороги severity для детекторов с низкой точностью
    """

    def __init__(self, meta_learner):
        self.meta = meta_learner

    def select_pattern(self, detector: str, available_patterns: list[str]) -> str | None:
        """Выбирает лучший паттерн для детектора с учётом статистики."""
        candidates = list(available_patterns)
        if not candidates:
            return None

        candidates.sort(key=lambda p: (
            self.meta.get_pattern_priority(p),
            self.meta.get_detector_weight(detector),
        ), reverse=True)

        best = candidates[0]
        confidence = self.meta.get_confidence(detector, best)

        if confidence < 0.15 and len(candidates) > 1:
            return candidates[1]
        return best

    def should_skip_detector(self, detector: str) -> bool:
        """Проверяет, стоит ли пропустить диагноста из-за низкого веса."""
        weight = self.meta.get_detector_weight(detector)
        total = 0
        ds = self.meta.detector_stats.get(detector)
        if ds:
            total = ds.total
        if total < 5:
            return False
        if weight < 0.2:
            return True
        return False

    def adjust_severity_threshold(self, detector: str, base_threshold: str) -> str:
        """Повышает порог severity для ненадёжных диагностов."""
        weight = self.meta.get_detector_weight(detector)
        if weight < 0.3:
            sev_order = ["info", "warning", "error", "critical"]
            idx = sev_order.index(base_threshold) if base_threshold in sev_order else 1
            new_idx = min(idx + 1, len(sev_order) - 1)
            return sev_order[new_idx]
        return base_threshold

    def get_confidence_description(self, detector: str, pattern: str) -> dict[str, Any]:
        conf = self.meta.get_confidence(detector, pattern)
        if conf >= 0.8:
            level = "high"
        elif conf >= 0.5:
            level = "medium"
        else:
            level = "low"
        return {
            "confidence": round(conf, 3),
            "level": level,
            "detector_weight": self.meta.get_detector_weight(detector),
            "pattern_priority": self.meta.get_pattern_priority(pattern),
        }
