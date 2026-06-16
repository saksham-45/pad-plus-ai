from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class InteractionType(Enum):
    NEW_KNOWLEDGE = "new_knowledge"
    CONTRADICTION = "contradiction"
    PRAISE = "praise"
    CRITICISM = "criticism"
    EXPLORATION = "exploration"
    ERROR_RECOVERY = "error_recovery"
    REPETITION = "repetition"


@dataclass
class ExperienceSignals:
    contradiction_detected: bool = False
    sentiment: str = "neutral"
    complexity: float = 0.5
    has_new_information: bool = False
    is_repetition: bool = False
    user_emotion: str = "neutral"
    truth_confidence: float = 0.0
    intent: str = ""
    strategy: str = "simple"


@dataclass
class ExperienceDeltas:
    impulse: dict = field(default_factory=dict)
    emotion: dict = field(default_factory=dict)
    persona: dict = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class ExperienceRecord:
    dialog_id: str
    user_message: str
    ai_response: str

    interaction_type: InteractionType
    signals: ExperienceSignals
    significance: float

    expectation: str
    reality: str
    delta: str

    lessons: list = field(default_factory=list)
    strategy_success: float = 0.0

    impulse_before: dict = field(default_factory=dict)
    emotion_before: dict = field(default_factory=dict)
    persona_before: dict = field(default_factory=dict)

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "dialog_id": self.dialog_id,
            "user_message": self.user_message[:200],
            "ai_response": self.ai_response[:200],
            "interaction_type": self.interaction_type.value,
            "signals": {
                "contradiction_detected": self.signals.contradiction_detected,
                "sentiment": self.signals.sentiment,
                "complexity": self.signals.complexity,
                "has_new_information": self.signals.has_new_information,
                "is_repetition": self.signals.is_repetition,
                "user_emotion": self.signals.user_emotion,
                "truth_confidence": self.signals.truth_confidence,
                "intent": self.signals.intent,
                "strategy": self.signals.strategy,
            },
            "significance": round(self.significance, 3),
            "expectation": self.expectation,
            "reality": self.reality,
            "delta": self.delta,
            "lessons": self.lessons,
            "strategy_success": self.strategy_success,
            "impulse_before": self.impulse_before,
            "emotion_before": self.emotion_before,
            "persona_before": self.persona_before,
            "timestamp": self.timestamp,
        }
