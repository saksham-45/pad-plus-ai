"""
👤 UserPersona — Персональная личность пользователя

Хранит предпочтения, стиль общения и эволюцию личности
для каждого отдельного пользователя.

В отличие от PersonaMemory (общая личность системы),
UserPersona индивидуальна для каждого пользователя.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger("PAD+.user_persona")


@dataclass
class UserPersona:
    """
    Персональная личность пользователя
    
    Хранит:
    - Предпочтения в стиле общения
    - Темы, которые интересны пользователю
    - Историю взаимодействий
    - Эволюцию предпочтений
    """
    
    # Идентификация
    user_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Предпочтения стиля общения
    style_preferences: Dict[str, Any] = field(default_factory=lambda: {
        "verbosity": 0.5,  # 0 = кратко, 1 = подробно
        "formality": 0.5,  # 0 = неформально, 1 = формально
        "technical_level": 0.5,  # 0 = просто, 1 = технически сложно
        "humor_level": 0.3,  # 0 = серьёзно, 1 = с юмором
        "use_examples": True,
        "use_analogies": True
    })
    
    # Интересы пользователя
    interests: List[str] = field(default_factory=list)
    
    # Часто обсуждаемые темы
    frequent_topics: Dict[str, int] = field(default_factory=dict)
    
    # История взаимодействий
    total_interactions: int = 0
    last_interaction: Optional[str] = None
    
    # Предпочтения по провайдерам/моделям
    preferred_providers: List[str] = field(default_factory=list)
    preferred_models: Dict[str, int] = field(default_factory=dict)
    
    # Эволюция (история изменений предпочтений)
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "style_preferences": self.style_preferences,
            "interests": self.interests,
            "frequent_topics": self.frequent_topics,
            "total_interactions": self.total_interactions,
            "last_interaction": self.last_interaction,
            "preferred_providers": self.preferred_providers,
            "preferred_models": self.preferred_models,
            "evolution_history": self.evolution_history[-10:]  # Последние 10 записей
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserPersona':
        """Создаёт из словаря"""
        return cls(
            user_id=data["user_id"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            style_preferences=data.get("style_preferences", {}),
            interests=data.get("interests", []),
            frequent_topics=data.get("frequent_topics", {}),
            total_interactions=data.get("total_interactions", 0),
            last_interaction=data.get("last_interaction"),
            preferred_providers=data.get("preferred_providers", []),
            preferred_models=data.get("preferred_models", {}),
            evolution_history=data.get("evolution_history", [])
        )
    
    def get_context_for_prompt(self) -> str:
        """
        Формирует контекст для промпта
        
        Используется в Pipeline для персонализации ответов
        """
        parts = []
        
        # Стиль общения
        style = self.style_preferences
        if style["verbosity"] > 0.7:
            parts.append("Пользователь предпочитает подробные ответы.")
        elif style["verbosity"] < 0.3:
            parts.append("Пользователь предпочитает краткие ответы.")
        
        if style["technical_level"] > 0.7:
            parts.append("Используй технические термины.")
        elif style["technical_level"] < 0.3:
            parts.append("Объясняй простыми словами.")
        
        if style["humor_level"] > 0.5:
            parts.append("Допустим лёгкий юмор.")
        
        # Интересы
        if self.interests:
            interests_str = ", ".join(self.interests[:5])
            parts.append(f"Интересы пользователя: {interests_str}.")
        
        # Частые темы
        if self.frequent_topics:
            top_topics = sorted(
                self.frequent_topics.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            topics_str = ", ".join(t[0] for t in top_topics)
            parts.append(f"Часто обсуждаемые темы: {topics_str}.")
        
        return "\n".join(parts) if parts else None
    
    def record_interaction(
        self,
        topic: str = None,
        provider: str = None,
        model: str = None
    ) -> None:
        """
        Записывает взаимодействие
        
        Автоматически обновляет статистику и предпочтения
        """
        self.total_interactions += 1
        self.last_interaction = datetime.now().isoformat()
        self.updated_at = self.last_interaction
        
        # Обновляем темы
        if topic:
            self.frequent_topics[topic] = self.frequent_topics.get(topic, 0) + 1
            
            # Добавляем в интересы если тема новая
            if topic not in self.interests and len(self.interests) < 10:
                self.interests.append(topic)
        
        # Обновляем предпочтения по моделям
        if model:
            self.preferred_models[model] = self.preferred_models.get(model, 0) + 1
        
        # Обновляем предпочтения по провайдерам
        if provider and provider not in self.preferred_providers:
            self.preferred_providers.append(provider)
    
    def adjust_style(
        self,
        trait: str,
        delta: float,
        reason: str = None
    ) -> None:
        """
        Корректирует стиль общения
        
        Args:
            trait: Название черты (verbosity, formality, etc.)
            delta: Изменение (-0.1 до +0.1)
            reason: Причина изменения
        """
        if trait not in self.style_preferences:
            return
        
        # Ограничиваем изменение
        delta = max(-0.1, min(0.1, delta))
        
        old_value = self.style_preferences[trait]
        new_value = max(0.0, min(1.0, old_value + delta))
        
        self.style_preferences[trait] = new_value
        
        # Записываем в историю эволюции
        if reason:
            self.evolution_history.append({
                "timestamp": datetime.now().isoformat(),
                "trait": trait,
                "old_value": round(old_value, 2),
                "new_value": round(new_value, 2),
                "reason": reason
            })
        
        logger.debug(f"🎭 UserPersona {self.user_id[:8]}...: {trait} {old_value:.2f} → {new_value:.2f} ({reason})")


class UserPersonaManager:
    """
    👤 Менеджер персональных личностей
    
    Управляет коллекцией UserPersona для разных пользователей.
    """
    
    def __init__(self, storage_path: str = "data/user_personas.json"):
        from pathlib import Path
        
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Кэш персонажей
        self._personas: Dict[str, UserPersona] = {}
        
        # Загружаем из файла
        self._load()
        
        logger.info(f"✅ UserPersonaManager инициализирован: {len(self._personas)} пользователей")
    
    def get_persona(self, user_id: str) -> UserPersona:
        """
        Получает или создаёт персону для пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            UserPersona для данного пользователя
        """
        if user_id not in self._personas:
            # Создаём новую персону
            self._personas[user_id] = UserPersona(user_id=user_id)
            logger.info(f"🎭 Создана новая UserPersona для {user_id[:8]}...")
        
        return self._personas[user_id]
    
    def save_persona(self, persona: UserPersona) -> None:
        """
        Сохраняет персону
        
        Args:
            persona: UserPersona для сохранения
        """
        self._personas[persona.user_id] = persona
        self._save()
    
    def _load(self) -> None:
        """Загружает персоны из файла"""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for user_data in data.get("users", []):
                persona = UserPersona.from_dict(user_data)
                self._personas[persona.user_id] = persona
            
            logger.info(f"📥 Загружено {len(self._personas)} UserPersona")
        except Exception as e:
            logger.warning(f"Ошибка загрузки UserPersona: {e}")
    
    def _save(self) -> None:
        """Сохраняет персоны в файл"""
        data = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "users": [p.to_dict() for p in self._personas.values()]
        }
        
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"📤 Сохранено {len(self._personas)} UserPersona")
        except Exception as e:
            logger.error(f"Ошибка сохранения UserPersona: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика менеджера"""
        if not self._personas:
            return {"total_users": 0}
        
        total_interactions = sum(p.total_interactions for p in self._personas.values())
        
        return {
            "total_users": len(self._personas),
            "total_interactions": total_interactions,
            "avg_interactions_per_user": round(total_interactions / len(self._personas), 1),
            "storage_path": str(self.storage_path)
        }


# Глобальный экземпляр
_persona_manager: Optional[UserPersonaManager] = None


def get_user_persona_manager() -> UserPersonaManager:
    """
    Возвращает глобальный менеджер персонажей
    
    Returns:
        UserPersonaManager
    """
    global _persona_manager
    if _persona_manager is None:
        _persona_manager = UserPersonaManager()
    return _persona_manager
