from fastapi import APIRouter
import logging

logger = logging.getLogger("padplus.experience")

router = APIRouter(prefix="/api/v1/admin/persona", tags=["Persona"])


@router.get("/deltas")
async def get_persona_deltas():
    from core.pipeline.phases.impulse_update import _IMPULSE_DELTAS

    return {
        "emotion": {
            "event_mapping": {
                "new_knowledge": {"pleasure": 0.1, "curiosity": 0.2, "confidence": 0.05},
                "contradiction": {"pleasure": -0.1, "confidence": -0.2, "arousal": 0.1},
                "user_praise": {"pleasure": 0.3, "social_connection": 0.2, "confidence": 0.1},
                "user_criticism": {"pleasure": -0.2, "social_connection": -0.1, "confidence": -0.1},
                "fallback": {"pleasure": -0.3, "anxiety": 0.2},
                "self_reflection": {"curiosity": 0.1, "arousal": 0.05},
            },
            "note": "определено в emotion.pad_model.PADModel.apply_event. intensity = base * significance.",
        },
        "impulse": {
            "deltas": {k: v for k, v in sorted(_IMPULSE_DELTAS.items())},
            "note": "delta умножается на significance. 'current' = метка с макс. весом.",
        },
        "persona_system": {
            "deltas": {},
            "note": "PersonaEvolutionPhase эволюционирует через evolve_from_dialog (анализ тональности и ключевых слов). Фиксированные таблицы дельт заменены на адаптивный анализ.",
        },
        "persona_user_style": {
            "deltas": {
                "factual_question": [["technical_level", 0.01]],
                "philosophical_question": [["formality", -0.01]],
                "positive_feedback": [["verbosity", 0.01]],
            },
            "note": "adjust_style клипирует в ±0.1. delta умножается на significance. Определено в PersonaEvolutionPhase.execute.",
        },
    }
