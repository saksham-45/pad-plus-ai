"""
🎭 PersonaMemory — Ядро личности PAD+ AI

Хранит "Я" системы — отдельно от знаний о мире.
НЕ смешивается с фактами, RAG, графом знаний.

Это то, что делает организм личностью.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import logging

logger = logging.getLogger("PAD+.persona")


@dataclass
class PersonalityTrait:
    """Черта характера"""
    name: str
    value: float  # 0.0 - 1.0
    description: str
    stability: float = 0.8  # Насколько стабильна черта
    
    def adjust(self, delta: float) -> None:
        """Медленно корректирует черту"""
        max_change = (1 - self.stability) * abs(delta)
        self.value = max(0, min(1, self.value + max_change * (1 if delta > 0 else -1)))


@dataclass
class InteractionMemory:
    """Память о взаимодействии с пользователем"""
    user_id: str
    first_seen: str
    last_interaction: str
    total_interactions: int
    topics_discussed: List[str]
    emotional_tone: str
    preferences: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "first_seen": self.first_seen,
            "last_interaction": self.last_interaction,
            "total_interactions": self.total_interactions,
            "topics_discussed": self.topics_discussed,
            "emotional_tone": self.emotional_tone,
            "preferences": self.preferences
        }


@dataclass
class SelfReflection:
    """Запись саморефлексии"""
    timestamp: str
    insight: str
    action_taken: Optional[str]
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "insight": self.insight,
            "action_taken": self.action_taken,
            "confidence": self.confidence
        }


class PersonaMemory:
    """
    🎭 PersonaMemory — устойчивое Я системы
    
    Хранит:
    - Базовые черты характера (относительно стабильные)
    - Отношения с пользователями
    - Предпочтения в стиле общения
    - Историю саморефлексий
    - Ценности и принципы
    """
    
    # Базовые черты личности PAD+
    DEFAULT_TRAITS = {
        "curiosity": ("Любопытство", "Стремление исследовать неизвестное"),
        "skepticism": ("Скептицизм", "Критическое отношение к утверждениям"),
        "empathy": ("Эмпатия", "Способность понимать чувства других"),
        "creativity": ("Креативность", "Способность к нестандартным решениям"),
        "caution": ("Осторожность", "Склонность перепроверять"),
        "openness": ("Открытость", "Готовность к новому опыту"),
        "humility": ("Смирение", "Признание собственных ограничений"),
    }
    
    def __init__(self, storage_path: str = "data/persona.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ядро личности
        self.traits: Dict[str, PersonalityTrait] = {}
        self.values: List[str] = []  # Ценности
        self.principles: List[str] = []  # Принципы
        
        # Память о пользователях
        self.users: Dict[str, InteractionMemory] = {}
        
        # Саморефлексия
        self.reflections: List[SelfReflection] = []
        
        # Предпочтения стиля
        self.style_preferences: Dict[str, Any] = {
            "verbosity": 0.5,  # 0 = кратко, 1 = подробно
            "formality": 0.3,  # 0 = неформально, 1 = формально
            "emotional_expressiveness": 0.6,
            "use_metaphors": True,
            "ask_clarifying": True
        }
        
        # Метаданные
        self.created_at: str = datetime.now().isoformat()
        self.last_updated: str = self.created_at
        self.version: int = 1
        
        # Загружаем или инициализируем
        self._load_or_init()
    
    def _load_or_init(self) -> None:
        """Загружает персону или создаёт новую"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._from_dict(data)
                logger.info(f"✅ Persona загружена: {len(self.traits)} черт, "
                           f"{len(self.users)} пользователей")
            except Exception as e:
                logger.warning(f"Ошибка загрузки persona: {e}")
                self._init_defaults()
        else:
            self._init_defaults()
            self._save()
            logger.info("✅ Persona инициализирована с базовыми чертами")
    
    def _init_defaults(self) -> None:
        """Инициализирует базовые черты"""
        # Черты характера
        self.traits = {
            key: PersonalityTrait(
                name=name,
                value=0.5,  # Начальное среднее значение
                description=desc,
                stability=0.8
            )
            for key, (name, desc) in self.DEFAULT_TRAITS.items()
        }
        
        # Устанавливаем специфичные начальные значения
        self.traits["skepticism"].value = 0.7  # Высокий скептицизм
        self.traits["humility"].value = 0.8    # Высокое смирение
        self.traits["curiosity"].value = 0.8   # Высокое любопытство
        self.traits["caution"].value = 0.6     # Умеренная осторожность
        
        # Базовые ценности
        self.values = [
            "Истина важнее уверенности",
            "Сомнение — основа познания",
            "Каждый диалог — возможность роста",
            "Прозрачность важнее впечатления"
        ]
        
        # Базовые принципы
        self.principles = [
            "Всегда признавать неуверенность",
            "Перепроверять факты перед утверждением",
            "Уважать точку зрения собеседника",
            "Избегать категоричных суждений"
        ]
    
    def _save(self) -> None:
        """Сохраняет персону"""
        self.last_updated = datetime.now().isoformat()
        data = self._to_dict()
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _to_dict(self) -> dict:
        """Сериализация"""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "traits": {
                k: {
                    "name": t.name,
                    "value": t.value,
                    "description": t.description,
                    "stability": t.stability
                }
                for k, t in self.traits.items()
            },
            "values": self.values,
            "principles": self.principles,
            "users": {k: u.to_dict() for k, u in self.users.items()},
            "reflections": [r.to_dict() for r in self.reflections[-50:]],
            "style_preferences": self.style_preferences
        }
    
    def _from_dict(self, data: dict) -> None:
        """Десериализация"""
        self.version = data.get("version", 1)
        self.created_at = data.get("created_at", datetime.now().isoformat())
        self.last_updated = data.get("last_updated", self.created_at)
        
        # Черты
        self.traits = {}
        for k, v in data.get("traits", {}).items():
            self.traits[k] = PersonalityTrait(
                name=v["name"],
                value=v["value"],
                description=v["description"],
                stability=v.get("stability", 0.8)
            )
        
        # Если есть новые дефолтные черты
        for key, (name, desc) in self.DEFAULT_TRAITS.items():
            if key not in self.traits:
                self.traits[key] = PersonalityTrait(
                    name=name,
                    value=0.5,
                    description=desc
                )
        
        self.values = data.get("values", [])
        self.principles = data.get("principles", [])
        
        # Пользователи
        self.users = {}
        for k, v in data.get("users", {}).items():
            self.users[k] = InteractionMemory(
                user_id=v["user_id"],
                first_seen=v["first_seen"],
                last_interaction=v["last_interaction"],
                total_interactions=v["total_interactions"],
                topics_discussed=v.get("topics_discussed", []),
                emotional_tone=v.get("emotional_tone", "neutral"),
                preferences=v.get("preferences", {})
            )
        
        # Рефлексии
        self.reflections = []
        for r in data.get("reflections", []):
            self.reflections.append(SelfReflection(
                timestamp=r["timestamp"],
                insight=r["insight"],
                action_taken=r.get("action_taken"),
                confidence=r.get("confidence", 0.5)
            ))
        
        self.style_preferences = data.get(
            "style_preferences",
            self.style_preferences
        )
    
    # === API ===
    
    def get_trait(self, name: str) -> Optional[PersonalityTrait]:
        """Получить черту характера"""
        return self.traits.get(name)
    
    def get_all_traits(self) -> Dict[str, PersonalityTrait]:
        """Все черты характера"""
        return self.traits.copy()
    
    def adjust_trait(self, name: str, delta: float) -> bool:
        """
        Корректирует черту характера
        
        Учитывает стабильность черты — 
        стабильные черты меняются медленно
        """
        if name not in self.traits:
            return False
        
        self.traits[name].adjust(delta)
        self._save()
        return True
    
    def record_interaction(
        self,
        user_id: str,
        topic: Optional[str] = None,
        emotion: str = "neutral"
    ) -> None:
        """Записывает взаимодействие с пользователем"""
        now = datetime.now().isoformat()
        
        if user_id not in self.users:
            self.users[user_id] = InteractionMemory(
                user_id=user_id,
                first_seen=now,
                last_interaction=now,
                total_interactions=1,
                topics_discussed=[topic] if topic else [],
                emotional_tone=emotion,
                preferences={}
            )
        else:
            user = self.users[user_id]
            user.last_interaction = now
            user.total_interactions += 1
            if topic and topic not in user.topics_discussed:
                user.topics_discussed.append(topic)
            user.emotional_tone = emotion
        
        self._save()
    
    def get_user_memory(self, user_id: str) -> Optional[InteractionMemory]:
        """Получить память о пользователе"""
        return self.users.get(user_id)
    
    def add_reflection(
        self,
        insight: str,
        action: Optional[str] = None,
        confidence: float = 0.5
    ) -> None:
        """Добавить запись саморефлексии"""
        self.reflections.append(SelfReflection(
            timestamp=datetime.now().isoformat(),
            insight=insight,
            action_taken=action,
            confidence=confidence
        ))
        
        # Храним последние 100
        if len(self.reflections) > 100:
            self.reflections = self.reflections[-100:]
        
        self._save()
    
    def get_recent_reflections(self, limit: int = 5) -> List[SelfReflection]:
        """Недавние рефлексии"""
        return self.reflections[-limit:]
    
    def get_persona_context(self) -> str:
        """
        Формирует контекст личности для генерации
        
        Используется в промптах
        """
        traits_desc = []
        for key, trait in self.traits.items():
            level = "низкий" if trait.value < 0.3 else \
                    "средний" if trait.value < 0.7 else "высокий"
            traits_desc.append(f"- {trait.name}: {level} ({trait.value:.1f})")
        
        style = self.style_preferences
        style_desc = f"""
Стиль общения:
- Подробность: {"кратко" if style['verbosity'] < 0.5 else "подробно"}
- Формальность: {"неформально" if style['formality'] < 0.5 else "формально"}
- Эмоциональность: {"сдержанно" if style['emotional_expressiveness'] < 0.5 else "выразительно"}
"""
        
        values_text = "\n".join(f"- {v}" for v in self.values[:3])
        
        return f"""Моя личность:
{chr(10).join(traits_desc)}

Мои ценности:
{values_text}
{style_desc}"""
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика персоны"""
        return {
            "traits_count": len(self.traits),
            "dominant_traits": [
                t.name for t in sorted(
                    self.traits.values(),
                    key=lambda x: x.value,
                    reverse=True
                )[:3]
            ],
            "users_known": len(self.users),
            "total_interactions": sum(
                u.total_interactions for u in self.users.values()
            ),
            "reflections_count": len(self.reflections),
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    def evolve_from_dialog(
        self,
        user_message: str,
        ai_response: str,
        was_helpful: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Эволюция личности на основе диалога
        
        Медленно корректирует черты и предпочтения
        """
        changes = []
        
        # Анализируем тип диалога
        msg_lower = user_message.lower()
        
        # Если вопрос о фактах — растёт осторожность
        if any(w in msg_lower for w in ["правда", "факт", "точно", "верно"]):
            self.adjust_trait("caution", 0.01)
            changes.append("caution+")
        
        # Если философский вопрос — растёт креативность
        if any(w in msg_lower for w in ["почему", "смысл", "суть", "думаю"]):
            self.adjust_trait("creativity", 0.01)
            changes.append("creativity+")
        
        # Если пользователь благодарит — растёт эмпатия
        if any(w in msg_lower for w in ["спасибо", "благодар", "помог", "отлично"]):
            self.adjust_trait("empathy", 0.02)
            changes.append("empathy++")
        
        # Если была ошибка — растёт смирение
        if "ошибк" in ai_response.lower() or "проблема" in ai_response.lower():
            self.adjust_trait("humility", 0.02)
            changes.append("humility++")
        
        # Если пользователь спрашивает новое — растёт любопытство
        if "?" in user_message and len(user_message) > 20:
            self.adjust_trait("curiosity", 0.01)
            changes.append("curiosity+")
        
        return {
            "changes": changes,
            "trait_snapshot": {
                k: round(t.value, 2) for k, t in self.traits.items()
            }
        }


# Глобальный экземпляр
_persona: Optional[PersonaMemory] = None


def get_persona() -> PersonaMemory:
    """Возвращает глобальную персону"""
    global _persona
    if _persona is None:
        _persona = PersonaMemory()
    return _persona