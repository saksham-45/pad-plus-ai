"""
Симулятор 100+ записей опыта для тестирования Experience Layer.

Генерирует реалистичные диалоги с разными типами взаимодействий,
чтобы можно было проанализировать распределение и отладить API.

Запуск:
    python -m core.experience.seed [--count 150]
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta

from .store import ExperienceStore
from .models import ExperienceRecord, InteractionType, ExperienceSignals


def _pick_user_message(intent: str) -> str:
    msgs = {
        "understand": [
            "Почему небо голубое?",
            "Объясни квантовую запутанность простыми словами",
            "Как работает фотосинтез?",
            "Что такое PAD-модель эмоций?",
            "Расскажи про теорему Геделя",
            "Как устроены black holes?",
            "Что такое энтропия?",
            "Объясни разницу между SQL и NoSQL",
            "Как работают нейронные сети?",
            "Что такое рекурсия?",
        ],
        "explore": [
            "А что если время не линейно?",
            "Расскажи гипотезу симуляции",
            "Какие есть теории сознания?",
            "Может ли ИИ чувствовать?",
            "Что будет, если объединить квантовые компьютеры с ИИ?",
            "Расскажи про第四百二十二个维度",
            "Есть ли жизнь на Энцеладе?",
            "Что такое тёмная материя?",
            "Как выглядит четвёртое измерение?",
            "Может ли время идти вспять?",
        ],
        "create": [
            "Напиши стих про осень",
            "Придумай название для стартапа",
            "Напиши рецепт пиццы",
            "Составь план тренировок",
            "Напиши короткий рассказ про робота",
            "Сгенерируй идеи для подарка девушке",
            "Напиши тост на свадьбу",
            "Составь меню на неделю",
            "Придумай сценарий для короткометражки",
            "Напиши код калькулятора на Python",
        ],
        "criticize": [
            "Это неправильно, фотосинтез работает иначе",
            "Ты ошибся, PAD не так расшифровывается",
            "Неверно, проверь факты",
            "Это неполный ответ",
            "Ты меня неправильно понял",
            "Это слишком сложно для обычного пользователя",
            "Ответ не по теме",
            "Ты упустил важные детали",
            "Это не соответствует действительности",
            "Слишком поверхностно",
        ],
        "praise": [
            "Отлично, спасибо! Всё понятно",
            "Классный ответ, помогло",
            "Спасибо, очень подробно",
            "Лучший ответ, который я получал",
            "Вау, круто! Спасибо большое",
            "Отлично сработано",
            "То что нужно, спасибо",
            "Супер, всё работает",
            "Благодарю, очень помог",
            "Здорово, теперь я понял",
        ],
        "repeat": [
            "Я уже спрашивал, почему небо голубое",
            "Ты мне уже это рассказывал",
            "Повтори ещё раз про PAD",
            "Я не запомнил, объясни снова",
            "Можешь ещё раз рассказать?",
            "Так, а что такое энтропия? (спрашивал уже)",
            "Напомни про теорему Геделя",
            "Повтори разницу между SQL и NoSQL",
            "Я уже спрашивал, но забыл",
            "Ещё раз про нейронные сети",
        ],
        "error_report": [
            "Ошибка: ты выдал битый JSON",
            "Твой ответ оборвался на середине",
            "Сервер вернул 500 ошибку",
            "Ответ пришёл пустой",
            "Ты завис на 30 секунд",
            "Выдал какую-то абракадабру",
            "Код который ты написал не компилится",
            "Твой ответ содержит ссылки на несуществующие источники",
            "Потерял контекст, отвечаешь не про то",
            "Ты дублируешь сообщения",
        ],
    }
    return random.choice(msgs.get(intent, msgs["understand"]))


def _pick_ai_response(intent: str, sentiment: str) -> str:
    base = {
        "understand": (
            "Всё дело в рассеянии света Рэлея. Коротковолновый голубой свет рассеивается "
            "сильнее длинноволнового красного, поэтому небо кажется голубым."
        ),
        "explore": (
            "Гипотеза симуляции предполагает, что наша реальность — это компьютерная "
            "симуляция. Аргументы Бострома: цивилизация足够 развитая сможет запускать "
            "симуляции предков, и таких симуляций будет больше, чем базовых реальностей."
        ),
        "create": (
            "Вот простая реализация калькулятора на Python:\n\n"
            "def calc(a, op, b):\n"
            "    if op == '+': return a + b\n"
            "    if op == '-': return a - b\n"
            "    return 'unknown op'"
        ),
        "criticize": (
            "Вы правы, я допустил неточность. PAD расшифровывается как "
            "Pleasure-Arousal-Dominance, а не как я указал ранее. Спасибо за поправку."
        ),
        "praise": (
            "Рад, что смог помочь! Если будут ещё вопросы — обращайтесь."
        ),
        "repeat": (
            "Извините, что повторяюсь. Рассеяние Рэлея: голубой свет рассеивается "
            "сильнее из-за своей короткой длины волны."
        ),
        "error_report": (
            "Извините за сбой. Я перезапустился и готов продолжить. "
            "Пожалуйста, повторите ваш последний запрос."
        ),
    }
    resp = base.get(intent, base["understand"])
    if sentiment == "negative":
        resp += " Приношу извинения за неточность."
    return resp


def _calc_reality(intent: str, sentiment: str) -> str:
    if sentiment == "negative":
        return "пользователь не удовлетворён"
    if sentiment == "positive":
        return "пользователь доволен"
    if intent == "repeat":
        return "повторный запрос — предыдущий ответ не закрепился"
    return "штатное взаимодействие"


def _calc_delta(interaction_type: InteractionType) -> str:
    mapping = {
        InteractionType.CONTRADICTION: "понимание было неполным — требуется уточнение",
        InteractionType.PRAISE: "подход сработал — закрепить",
        InteractionType.CRITICISM: "ответ не удовлетворил — нужна коррекция стратегии",
        InteractionType.EXPLORATION: "пользователь исследует — углубить контекст",
        InteractionType.ERROR_RECOVERY: "произошёл сбой — повысить защиту",
        InteractionType.REPETITION: "повтор запроса — предыдущий ответ не запомнился",
        InteractionType.NEW_KNOWLEDGE: "штатное взаимодействие",
    }
    return mapping.get(interaction_type, "не определено")


def seed(count: int = 120):
    store = ExperienceStore()
    now = datetime.now()

    # Распределение: ~40% understand, ~15% explore, ~10% create, ~10% criticism, ~10% praise, ~5% repeat, ~5% error
    intent_weights = {
        "understand": 0.38,
        "explore": 0.15,
        "create": 0.10,
        "criticize": 0.12,
        "praise": 0.10,
        "repeat": 0.07,
        "error_report": 0.08,
    }

    intents = list(intent_weights.keys())
    weights = list(intent_weights.values())

    created = 0
    for i in range(count):
        intent = random.choices(intents, weights=weights, k=1)[0]
        sentiment = random.choices(
            ["positive", "negative", "neutral"],
            weights=[0.20, 0.25, 0.55],
            k=1
        )[0]

        user_msg = _pick_user_message(intent)
        ai_resp = _pick_ai_response(intent, sentiment)
        interaction_type = _map_to_interaction_type(intent, sentiment)

        contradictory = random.random() < 0.25 and sentiment == "negative"
        is_repeat = intent == "repeat"
        has_new_info = random.random() < 0.5 and intent in ("understand", "explore")

        signals = ExperienceSignals(
            contradiction_detected=contradictory,
            sentiment=sentiment,
            complexity=round(random.uniform(0.2, 0.9), 2),
            has_new_information=has_new_info,
            is_repetition=is_repeat,
            user_emotion=sentiment,
            truth_confidence=round(random.uniform(0.3, 0.95), 2),
            intent=intent,
            strategy=random.choice(["simple", "rag", "verify", "deep"]),
        )

        significance = _compute_sig(interaction_type, contradictory, sentiment, is_repeat, signals.complexity)
        reality = _calc_reality(intent, sentiment)
        delta = _calc_delta(interaction_type)

        timestamp_dt = now - timedelta(seconds=(count - i) * random.randint(30, 600))

        record = ExperienceRecord(
            dialog_id=str(uuid.uuid4())[:8],
            user_message=user_msg,
            ai_response=ai_resp,
            interaction_type=interaction_type,
            signals=signals,
            significance=round(significance, 3),
            expectation=f"ожидалось: импульс={intent}",
            reality=reality,
            delta=delta,
            lessons=[],
            strategy_success=round(random.uniform(0.3, 0.95), 2),
            impulse_before={"current": intent, "weight": round(random.uniform(0.3, 0.9), 2)},
            emotion_before={
                "удовольствие": round(random.uniform(0.2, 0.8), 2),
                "возбуждение": round(random.uniform(0.3, 0.9), 2),
                "доминирование": round(random.uniform(0.3, 0.7), 2),
            },
            persona_before={},
            timestamp=timestamp_dt.isoformat(),
        )
        store.save(record)
        created += 1

    print(f"Создано {created} записей опыта в {store.data_dir}")


def _map_to_interaction_type(intent: str, sentiment: str) -> InteractionType:
    if intent == "error_report":
        return InteractionType.ERROR_RECOVERY
    if intent == "repeat":
        return InteractionType.REPETITION
    if intent == "criticize":
        return InteractionType.CRITICISM
    if intent == "praise":
        return InteractionType.PRAISE
    if intent == "explore":
        return InteractionType.EXPLORATION
    if sentiment == "negative":
        return InteractionType.CONTRADICTION
    return InteractionType.NEW_KNOWLEDGE


def _compute_sig(it: InteractionType, contradictory: bool, sentiment: str, is_repeat: bool, complexity: float) -> float:
    base = 0.3
    if contradictory or it == InteractionType.CONTRADICTION:
        base += 0.4
    if sentiment == "negative":
        base += 0.15
    if complexity > 0.7:
        base += 0.1
    if is_repeat:
        base -= 0.15
    if it == InteractionType.ERROR_RECOVERY:
        base += 0.2
    return min(max(base + random.uniform(-0.05, 0.05), 0.0), 1.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=120, help="Количество записей")
    args = parser.parse_args()
    seed(args.count)


if __name__ == "__main__":
    main()
