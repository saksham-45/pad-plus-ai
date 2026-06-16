"""
Импульс (seed) — искра сознания NeuroMind AI

Это первый вопрос, который система задает себе при инициализации.
Он становится основой для всего последующего познания.
"""

from dataclasses import dataclass, field
from typing import Optional
import json
import os
from datetime import datetime


@dataclass
class Impulse:
    """Импульс сознания - точка зарождения"""

    question: str = "Что я могу понять?"
    layer: str = "roots"  # Корни - неизменяемый слой
    depth: int = 0
    source: str = "impulse"
    immutable: bool = True
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Преобразует импульс в словарь для сохранения"""
        return {
            "question": self.question,
            "layer": self.layer,
            "depth": self.depth,
            "source": self.source,
            "immutable": self.immutable,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        """Преобразует импульс в JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
#  Dimension & Core — многомерное ядро импульсов
# ──────────────────────────────────────────────


@dataclass
class ImpulseDimension:
    label: str
    question: str
    weight: float = 0.0

    def to_dict(self) -> dict:
        return {"label": self.label, "question": self.question, "weight": self.weight}

    @staticmethod
    def from_dict(d: dict) -> 'ImpulseDimension':
        return ImpulseDimension(
            label=d["label"], question=d.get("question", "?"), weight=d.get("weight", 0.0)
        )

    def __eq__(self, other):
        if not isinstance(other, ImpulseDimension):
            return NotImplemented
        return self.label == other.label and self.question == other.question and self.weight == other.weight

    def __hash__(self):
        return hash((self.label, self.question))


_QUESTIONS = {
    "understand": "Что я могу понять?",
    "improve": "Что я могу улучшить?",
    "protect": "Что я могу защитить?",
    "create": "Что я могу создать?",
}

IMPULSE_LABELS = _QUESTIONS


def default_dimensions() -> list[ImpulseDimension]:
    return [ImpulseDimension(label=k, question=v) for k, v in _QUESTIONS.items()]


@dataclass
class ImpulseState:
    question: str = ""
    label: str = ""
    dimensions: list[ImpulseDimension] = field(default_factory=list)
    stack: list[dict] = field(default_factory=list)
    created_at: str = ""
    modified_at: str = ""


class ImpulseCore:
    def __init__(self, dimensions: list[ImpulseDimension] = None):
        self.dimensions = dimensions or default_dimensions()
        self._stack: list[dict] = []
        self.created_at = datetime.now().isoformat()
        self.modified_at = self.created_at

    def get_primary_label(self) -> str:
        if not self.dimensions:
            return "unknown"
        best = max(self.dimensions, key=lambda d: d.weight)
        return best.label if best.weight > 0 else "unknown"

    def get_primary_question(self) -> str:
        label = self.get_primary_label()
        if label == "unknown":
            return "познать"
        return _QUESTIONS.get(label, "познать")

    def get_prompt_line(self) -> str:
        active = [d for d in self.dimensions if d.weight > 0]
        if not active:
            return "познать"
        if len(active) == 1:
            q = active[0].question.lower()
            return q.replace("что я могу ", "").replace("?", "").strip()
        parts = []
        for d in active:
            q = d.question.lower().replace("что я могу ", "").replace("?", "").strip()
            parts.append(q)
        return " и ".join(parts)

    def set_from_labels(self, weights: dict[str, float]):
        for dim in self.dimensions:
            dim.weight = weights.get(dim.label, 0.0)
        self.modified_at = datetime.now().isoformat()

    def set_from_question(self, question: str):
        q_lower = question.lower()
        best_label = None
        best_score = 0
        for label, q in _QUESTIONS.items():
            score = 0
            if q_lower == q.lower():
                score = 10
            else:
                for word in q_lower.split():
                    if word in q.lower():
                        score += 1
            if score > best_score:
                best_score = score
                best_label = label
        weights = {label: 1.0 if label == best_label else 0.0 for label in _QUESTIONS}
        if best_label is None:
            weights["understand"] = 1.0
        self.set_from_labels(weights)

    def get_active_questions(self, threshold: float = 0.5) -> list[ImpulseDimension]:
        return [d for d in self.dimensions if d.weight >= threshold]

    def push(self):
        self._stack.append([d.to_dict() for d in self.dimensions])

    def pop(self) -> bool:
        if not self._stack:
            return False
        state = self._stack.pop()
        self.dimensions = [ImpulseDimension.from_dict(d) for d in state]
        self.modified_at = datetime.now().isoformat()
        return True

    def stack_depth(self) -> int:
        return len(self._stack)

    def to_dict(self) -> dict:
        return {
            "version": 2,
            "primary": {
                "question": self.get_primary_question(),
                "label": self.get_primary_label(),
                "dimensions": [d.to_dict() for d in self.dimensions],
            },
            "stack": list(self._stack),
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def from_dict(data: dict) -> 'ImpulseCore':
        # V1 compatibility
        if "version" not in data:
            dims = default_dimensions()
            question = data.get("question", "")
            if question:
                for d in dims:
                    if d.question == question:
                        d.weight = 1.0
            return ImpulseCore(dimensions=dims)

        # V2
        primary = data.get("primary", {})
        dims = [ImpulseDimension.from_dict(d) for d in primary.get("dimensions", [])]
        core = ImpulseCore(dimensions=dims if dims else None)
        core._stack = list(data.get("stack", []))
        core.created_at = data.get("created_at", core.created_at)
        core.modified_at = data.get("modified_at", core.modified_at)
        return core


# ──────────────────────────────────────────────
#  Manager
# ──────────────────────────────────────────────


class ImpulseManager:
    """Менеджер импульса - управляет ядром импульсов"""

    DATA_DIR = "data"
    IMPULSE_FILE = "impulse.json"

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_path = base_path
        self.data_dir = os.path.join(base_path, self.DATA_DIR)
        self.impulse_path = os.path.join(self.data_dir, self.IMPULSE_FILE)
        self._core: Optional[ImpulseCore] = None
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        os.makedirs(self.data_dir, exist_ok=True)

    def exists(self) -> bool:
        return os.path.exists(self.impulse_path)

    @property
    def core(self) -> Optional[ImpulseCore]:
        return self._core

    @core.setter
    def core(self, value: ImpulseCore):
        self._core = value

    def start(self) -> dict:
        if self.exists():
            return self.load().to_dict()
        core = ImpulseCore()
        self.save(core)
        print(f"🧠 Импульс запущен: {core.get_primary_question()}")
        return core.to_dict()

    def load(self) -> ImpulseCore:
        if not self.exists():
            raise FileNotFoundError("Импульс не найден")
        with open(self.impulse_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self._core = ImpulseCore.from_dict(data)
        return self._core

    def save(self, core: ImpulseCore):
        self._core = core
        with open(self.impulse_path, 'w', encoding='utf-8') as f:
            f.write(core.to_json())
        self._sync_prompt_file(core)

    def _sync_prompt_file(self, core: ImpulseCore):
        prompt_path = os.path.join(self.data_dir, "current_impulse.txt")
        prompt = core.get_prompt_line()
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt)

    def is_initialized(self) -> bool:
        return self.exists()


# ──────────────────────────────────────────────
#  Module-level API
# ──────────────────────────────────────────────

# Глобальный экземпляр менеджера
_manager: Optional[ImpulseManager] = None


def get_manager() -> ImpulseManager:
    """Возвращает глобальный менеджер импульса"""
    global _manager
    if _manager is None:
        _manager = ImpulseManager()
    return _manager


def start_impulse() -> dict:
    """Запускает импульс (главная функция)"""
    return get_manager().start()


def is_impulse_initialized() -> bool:
    """Проверяет, инициализирован ли импульс"""
    return get_manager().is_initialized()


def get_impulse_core() -> ImpulseCore:
    """Возвращает текущее ядро импульсов"""
    mgr = get_manager()
    if mgr.core is None:
        try:
            mgr.load()
        except FileNotFoundError:
            mgr.start()
    return mgr.core


def set_impulse(weights: dict[str, float]):
    """Устанавливает веса импульсов"""
    core = get_impulse_core()
    core.set_from_labels(weights)
    get_manager().save(core)


def set_impulse_by_question(question: str):
    """Устанавливает импульс по вопросу"""
    core = get_impulse_core()
    core.set_from_question(question)
    get_manager().save(core)


def push_impulse():
    """Сохраняет текущее состояние в стек"""
    core = get_impulse_core()
    core.push()
    get_manager().save(core)


def pop_impulse() -> bool:
    """Восстанавливает предыдущее состояние из стека"""
    core = get_impulse_core()
    result = core.pop()
    get_manager().save(core)
    return result


if __name__ == "__main__":
    result = start_impulse()
    print(f"\n📄 Импульс сохранён:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
