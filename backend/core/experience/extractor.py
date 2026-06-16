import logging
from typing import Optional

from .models import ExperienceSignals, InteractionType

logger = logging.getLogger("padplus.experience")


class ExperienceExtractor:
    def extract_signals(
        self,
        user_message: str,
        ai_response: str,
        truth_confidence: Optional[float] = None,
        intent: str = "",
        strategy: str = "simple",
        episodic_memory=None,
    ) -> ExperienceSignals:
        signals = ExperienceSignals(
            truth_confidence=truth_confidence or 0.0,
            intent=intent,
            strategy=strategy,
        )

        self._detect_sentiment(user_message, signals)
        self._detect_contradiction(truth_confidence, signals)
        self._estimate_complexity(user_message, ai_response, signals)
        self._check_repetition(user_message, episodic_memory, signals)
        self._check_new_information(ai_response, signals)

        return signals

    def classify_interaction(self, signals: ExperienceSignals) -> InteractionType:
        if signals.contradiction_detected:
            return InteractionType.CONTRADICTION
        if signals.sentiment == "negative":
            return InteractionType.CRITICISM
        if signals.sentiment == "positive":
            return InteractionType.PRAISE
        if signals.is_repetition:
            return InteractionType.REPETITION
        if signals.complexity > 0.7 or signals.intent in ("exploration", "reasoning"):
            return InteractionType.EXPLORATION
        if signals.intent in ("error_recovery", "fallback"):
            return InteractionType.ERROR_RECOVERY
        return InteractionType.NEW_KNOWLEDGE

    def compute_significance(self, signals: ExperienceSignals) -> float:
        base = 0.3
        if signals.contradiction_detected:
            base += 0.4
        if signals.sentiment == "negative":
            base += 0.2
        if signals.has_new_information:
            base += 0.15
        if signals.complexity > 0.7:
            base += 0.1
        if signals.is_repetition:
            base -= 0.15
        return min(max(base, 0.0), 1.0)

    def build_delta(self, interaction_type: InteractionType, signals: ExperienceSignals) -> str:
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

    def _detect_sentiment(self, text: str, signals: ExperienceSignals):
        text_lower = text.lower()
        positive_words = {"спасибо", "отлично", "помогло", "класс", "здорово", "да", "верно", "точно", "хорошо"}
        negative_words = {"нет", "не", "ошибка", "плохо", "неверно", "неправильно", "не так", "не понял"}
        pos = sum(1 for w in positive_words if w in text_lower)
        neg = sum(1 for w in negative_words if w in text_lower)
        if pos > neg:
            signals.sentiment = "positive"
        elif neg > pos:
            signals.sentiment = "negative"
        else:
            signals.sentiment = "neutral"

    def _detect_contradiction(self, truth_confidence: Optional[float], signals: ExperienceSignals):
        if truth_confidence is not None and truth_confidence < 0.4:
            signals.contradiction_detected = True

    def _estimate_complexity(self, user_msg: str, ai_resp: str, signals: ExperienceSignals):
        msg_len = len(user_msg) + len(ai_resp)
        has_question = "?" in user_msg or "?" in ai_resp
        scores = [min(msg_len / 1000, 0.6)]
        if has_question:
            scores.append(0.2)
        signals.complexity = min(sum(scores), 1.0)

    def _check_repetition(self, user_message: str, episodic_memory, signals: ExperienceSignals):
        from difflib import SequenceMatcher
        if not episodic_memory:
            return
        recent = getattr(episodic_memory, "get_recent", None)
        if not recent:
            return
        try:
            entries = recent(5)
            for entry in entries:
                prev_msg = ""
                if isinstance(entry, dict):
                    prev_msg = entry.get("user_message", entry.get("text", ""))
                elif hasattr(entry, "user_message"):
                    prev_msg = entry.user_message
                if not prev_msg:
                    continue
                ratio = SequenceMatcher(None, user_message.lower(), prev_msg.lower()).ratio()
                if ratio > 0.8:
                    signals.is_repetition = True
                    return
        except Exception as e:
            logger.warning(f"Operation failed: {e}")
    def _check_new_information(self, ai_response: str, signals: ExperienceSignals):
        new_info_keywords = {"на самом деле", "оказывается", "важно отметить", "интересный факт"}
        signals.has_new_information = any(kw in ai_response.lower() for kw in new_info_keywords)
