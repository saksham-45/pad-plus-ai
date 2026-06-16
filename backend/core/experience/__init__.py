"""
Experience Layer v0 — read-only наблюдение за опытом системы.

Фиксирует разницу между ожиданием и реальностью после каждого
диалогового цикла. Ничего не изменяет — только накапливает
ExperienceRecord для последующего анализа.

v0: capture only, no side effects.
"""

from .models import ExperienceRecord, InteractionType, ExperienceSignals, ExperienceDeltas
from .extractor import ExperienceExtractor
from .store import ExperienceStore
from .experience import capture_experience, get_extractor, get_store

__all__ = [
    "ExperienceRecord",
    "InteractionType",
    "ExperienceSignals",
    "ExperienceDeltas",
    "ExperienceExtractor",
    "ExperienceStore",
    "capture_experience",
    "get_extractor",
    "get_store",
]
