import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger("padplus.meta_controller")


class CognitiveState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    LEARNING = "learning"
    REFLECTING = "reflecting"
    DREAMING = "dreaming"


@dataclass
class MetaSnapshot:
    state: CognitiveState = CognitiveState.IDLE
    emotion_summary: Dict[str, float] = field(default_factory=dict)
    impulse_primary: str = ""
    strategy_success_rate: float = 0.0
    dialogs_since_reflection: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "emotion_summary": self.emotion_summary,
            "impulse_primary": self.impulse_primary,
            "strategy_success_rate": round(self.strategy_success_rate, 3),
            "dialogs_since_reflection": self.dialogs_since_reflection,
            "timestamp": self.timestamp,
        }


class MetaController:
    def __init__(self):
        self._state = CognitiveState.IDLE
        self._snapshots: list[MetaSnapshot] = []
        self._max_snapshots = 50
        self._dialogs_since_reflection = 0
        self._reflection_threshold = int(os.getenv("META_REFLECTION_DIALOGS", "10"))
        self._low_success_threshold = float(os.getenv("META_LOW_SUCCESS", "0.4"))
        self._high_significance = float(os.getenv("META_HIGH_SIGNIFICANCE", "0.8"))

    def set_state(self, state: CognitiveState) -> None:
        old = self._state
        self._state = state
        if old != state:
            logger.info("MetaController: %s → %s", old.value, state.value)

    def get_state(self) -> CognitiveState:
        return self._state

    def adapt(self, signals: Dict[str, Any]) -> None:
        from core.events import get_events
        from core.xray.meta_learner import get_meta_learner

        strategy_success = signals.get("strategy_success", 0.5)
        interaction_type = signals.get("interaction_type", "new_knowledge")
        significance = signals.get("significance", 0.0)
        impulse_label = signals.get("impulse_primary", "")

        meta = get_meta_learner()
        all_stats = meta.get_all_stats()
        avg_success = 0.5
        if all_stats:
            rates = [s.get("success_rate", 0.5) for s in all_stats.values()]
            if rates:
                avg_success = sum(rates) / len(rates)

        snapshot = MetaSnapshot(
            state=self._state,
            emotion_summary=signals.get("emotion", {}),
            impulse_primary=impulse_label,
            strategy_success_rate=avg_success,
            dialogs_since_reflection=self._dialogs_since_reflection,
        )
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]

        self._dialogs_since_reflection += 1

        need_reflection = (
            self._dialogs_since_reflection >= self._reflection_threshold
            or avg_success < self._low_success_threshold
            or significance > self._high_significance
        )
        if need_reflection:
            self._state = CognitiveState.REFLECTING
            self._dialogs_since_reflection = 0
        elif self._state == CognitiveState.REFLECTING:
            self._state = CognitiveState.IDLE

    def get_snapshots(self, limit: int = 10) -> list[Dict[str, Any]]:
        return [s.to_dict() for s in self._snapshots[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "total_snapshots": len(self._snapshots),
            "dialogs_since_reflection": self._dialogs_since_reflection,
        }


_meta_controller: Optional[MetaController] = None


def get_meta_controller() -> MetaController:
    global _meta_controller
    if _meta_controller is None:
        _meta_controller = MetaController()
    return _meta_controller


def reset_meta_controller() -> None:
    global _meta_controller
    _meta_controller = None
