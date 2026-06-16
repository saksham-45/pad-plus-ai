import logging
from typing import Optional

from .extractor import ExperienceExtractor
from .models import ExperienceRecord, ExperienceSignals
from .store import ExperienceStore

logger = logging.getLogger("padplus.experience")

_extractor: Optional[ExperienceExtractor] = None
_store: Optional[ExperienceStore] = None


def get_extractor() -> ExperienceExtractor:
    global _extractor
    if _extractor is None:
        _extractor = ExperienceExtractor()
    return _extractor


def get_store() -> ExperienceStore:
    global _store
    if _store is None:
        _store = ExperienceStore()
    return _store


def capture_experience(
    dialog_id: str,
    user_message: str,
    ai_response: str,
    impulse_before: Optional[dict] = None,
    emotion_before: Optional[dict] = None,
    persona_before: Optional[dict] = None,
    truth_confidence: Optional[float] = None,
    intent: str = "",
    strategy: str = "simple",
    lessons: Optional[list] = None,
    strategy_success: float = 0.0,
    episodic_memory=None,
) -> Optional[ExperienceRecord]:
    try:
        extractor = get_extractor()
        store = get_store()

        signals = extractor.extract_signals(
            user_message=user_message,
            ai_response=ai_response,
            truth_confidence=truth_confidence,
            intent=intent,
            strategy=strategy,
            episodic_memory=episodic_memory,
        )

        interaction_type = extractor.classify_interaction(signals)
        significance = extractor.compute_significance(signals)
        delta = extractor.build_delta(interaction_type, signals)

        expectation = f"ожидалось: импульс={intent or 'unknown'}, стратегия={strategy}"
        reality = f"получено: тип={interaction_type.value}, сентимент={signals.sentiment}"

        record = ExperienceRecord(
            dialog_id=dialog_id,
            user_message=user_message,
            ai_response=ai_response,
            interaction_type=interaction_type,
            signals=signals,
            significance=significance,
            expectation=expectation,
            reality=reality,
            delta=delta,
            lessons=lessons or [],
            strategy_success=strategy_success,
            impulse_before=impulse_before or {},
            emotion_before=emotion_before or {},
            persona_before=persona_before or {},
        )

        store.save(record)
        return record

    except Exception as e:
        logger.warning("Experience capture failed (read-only): %s", e)
        return None
