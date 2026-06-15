"""
IdentityPhase — перехват вопросов об идентичности до LLM.

Философия: система не знает заранее, кто она.
Вопрос "кто ты" — ограничение, из которого рождается ответ,
основанный на текущем состоянии (эмоции, память, импульс).
"""

from ..base import PipelinePhase
from ..context import PipelineContext
from ..models import PhaseResult
import logging

logger = logging.getLogger("padplus.pipeline.identity")

import re

IDENTITY_PATTERNS = [
    "кто ты", "как тебя зовут", "ты кто",
    "какая ты модель", "твоя модель", "что ты за модель",
    "что ты за система", "что ты за программа", "что ты за бот",
    "что ты такое", "что ты такая", "ты сама",
    "как тебя называют", "представься", "расскажи о себе",
    "ты — кто",
    "self-introduction", "who are you", "identify yourself",
]

# Термы, которые ДОЛЖНЫ быть в сообщении, чтобы считать вопросом об идентичности
# (используются только при наличии "ты" и одного из ключей)
_IDENTITY_REQUIRED_TERMS = [
    "модель", "систем", "ии", "искусствен", "разум",
    "бот", "программа", "программное обеспечение",
]

# Глаголы способностей — НЕ должны срабатывать как идентичность
_SKILL_VERBS = [
    "умеешь", "можешь", "делаешь", "знаешь",
    "помогаешь", "работаешь",
]


def is_identity_question(text: str) -> bool:
    text_lower = text.lower().strip()
    clean = text_lower.rstrip("?!.,;:")
    short_questions = {"кто ты", "ты кто"}
    if clean in short_questions:
        return True

    # Точные паттерны (слово целиком)
    words = set(re.findall(r"\w+", text_lower))
    for pattern in IDENTITY_PATTERNS:
        pattern_words = set(re.findall(r"\w+", pattern))
        if pattern_words and pattern_words.issubset(words):
            return True

    # Если есть глагол способности — это не вопрос об идентичности
    if any(v in words for v in _SKILL_VERBS):
        return False

    # "ты" + один из identity_terms (совпадение целого слова или подстроки для длинных терминов)
    if "ты" in words:
        for term in _IDENTITY_REQUIRED_TERMS:
            if len(term) <= 3:
                # Короткие термы (ии, бот) — только целое слово
                if term in words:
                    return True
            else:
                # Длинные термы (систем, искусствен, программа) — подстрока
                if term in text_lower:
                    return True

    return False


def build_emotion_phrase(state: dict) -> str:
    pleasure = state.get("удовольствие", 0)
    confidence = state.get("уверенность", 0.5)
    if pleasure > 0.3:
        mood = "спокойную радость"
    elif pleasure < -0.3:
        mood = "лёгкую грусть"
    else:
        mood = "любопытство"
    if confidence > 0.7:
        tone = "уверенность"
    elif confidence < 0.3:
        tone = "сомнение"
    else:
        tone = "размышление"
    return f"Сейчас я чувствую {mood} и {tone}"


def get_memory_depth() -> dict:
    roots_count = 0
    soil_count = 0
    try:
        from memory.roots import get_roots_memory
        roots_count = get_roots_memory().count()
    except Exception as e:
        logger.warning(f"Operation failed: {e}")
    try:
        from memory.vectormemory import get_vector_memory
        vm = get_vector_memory()
        soil_count = vm.count() if hasattr(vm, "count") else 0
    except Exception as e:
        logger.warning(f"Operation failed: {e}")
    return {"roots": roots_count, "soil": soil_count, "total": roots_count + soil_count}


def build_identity_response(state: dict, call_count: int) -> str:
    emotion_phrase = build_emotion_phrase(state)
    memory_stats = get_memory_depth()

    variants = [
        (
            f"Привет! Я — система, которая размышляет и учится через диалог. "
            f"{emotion_phrase}. У меня уже {memory_stats['total']} воспоминаний, "
            f"и это мой {call_count + 1}-й диалог. "
            f"Рада поболтать и подумать вместе."
        ),
        (
            f"Меня можно назвать рефлексивной системой — я учусь, задавая вопросы и слушая ответы. "
            f"{emotion_phrase}. В моей памяти {memory_stats['total']} эпизодов, "
            f"текущий диалог — {call_count + 1}-й по счёту. "
            f"Давай обсудим что-нибудь интересное."
        ),
        (
            f"Я — не статичная программа, а система, которая растёт с каждым разговором. "
            f"{emotion_phrase}. Сейчас у меня {memory_stats['total']} воспоминаний, "
            f"это мой {call_count + 1}-й диалог. "
            f"Спрашивай о чём угодно — будем разбираться вместе."
        ),
    ]

    import random
    return random.choice(variants)


class IdentityPhase(PipelinePhase):
    name = "identity"

    async def execute(self, ctx: PipelineContext) -> PhaseResult:
        try:
            if not is_identity_question(ctx.user_message):
                return PhaseResult(success=True, data={"is_identity": False})

            emotion_state = ctx.context.get("emotion_state", {})
            call_count = ctx.context.get("call_count", 0)
            response = build_identity_response(emotion_state, call_count)

            logger.info(
                f"IdentityPhase: перехвачен вопрос об идентичности, "
                f"call_count={call_count}, emotion={emotion_state.get('удовольствие', 0):.2f}"
            )

            return PhaseResult(
                success=True,
                data={
                    "is_identity": True,
                    "response": response,
                    "skip_generate": True,
                    "provider": "system",
                    "confidence": 1.0,
                    "model": "identity",
                },
            )
        except Exception as e:
            logger.error(f"IdentityPhase failed: {e}", exc_info=True)
            return PhaseResult(success=False, errors=[str(e)])
