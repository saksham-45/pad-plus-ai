"""
🔐 SessionManager — Управление сессиями пользователей

- Создание и хранение сессий
- Контекст диалога
- Настройки пользователя
- Автоматическая очистка неактивных
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json
import os
import uuid
import logging

logger = logging.getLogger("PAD+.session")


@dataclass
class SessionContext:
    """Контекст сессии"""
    topics_discussed: List[str] = field(default_factory=list)
    last_intent: str = ""
    emotion_history: List[str] = field(default_factory=list)
    entities_mentioned: Dict[str, int] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    def add_topic(self, topic: str):
        if topic and topic not in self.topics_discussed:
            self.topics_discussed.append(topic)
            if len(self.topics_discussed) > 50:
                self.topics_discussed.pop(0)
    
    def add_entity(self, entity: str):
        self.entities_mentioned[entity] = \
            self.entities_mentioned.get(entity, 0) + 1
    
    def add_emotion(self, emotion: str):
        self.emotion_history.append(emotion)
        if len(self.emotion_history) > 20:
            self.emotion_history.pop(0)
    
    def to_dict(self) -> dict:
        return {
            "topics_discussed": self.topics_discussed,
            "last_intent": self.last_intent,
            "emotion_history": self.emotion_history,
            "entities_mentioned": self.entities_mentioned,
            "preferences": self.preferences
        }


@dataclass
class Session:
    """Сессия пользователя"""
    session_id: str
    created_at: datetime
    last_active: datetime
    ip_address: str = ""
    user_agent: str = ""
    context: SessionContext = field(default_factory=SessionContext)
    settings: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, max_age_hours: int = 24) -> bool:
        age = datetime.now() - self.last_active
        return age > timedelta(hours=max_age_hours)
    
    def touch(self):
        """Обновляет время последней активности"""
        self.last_active = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "ip_address": self.ip_address,
            "message_count": self.message_count,
            "context": self.context.to_dict(),
            "settings": self.settings,
            "metadata": self.metadata
        }


class SessionManager:
    """
    🔐 Менеджер сессий
    
    Features:
    - Создание и хранение сессий
    - Контекст диалога для персонализации
    - Настройки пользователя
    - Автоматическая очистка неактивных
    """
    
    DEFAULT_SETTINGS = {
        "language": "ru",
        "response_length": "medium",  # short, medium, long
        "formality": "neutral",       # casual, neutral, formal
        "detail_level": "normal",     # brief, normal, detailed
        "emotion_display": True,
        "show_confidence": False
    }
    
    def __init__(self, data_path: str = None, max_age_hours: int = 24):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "sessions.json"
            )
        self.data_path = data_path
        self.max_age_hours = max_age_hours
        
        # Активные сессии: session_id -> Session
        self._sessions: Dict[str, Session] = {}
        
        # Индекс по IP: ip_address -> set of session_ids
        self._ip_index: Dict[str, set] = {}
        
        self._stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_messages": 0
        }
        
        self._load()
    
    def _load(self):
        """Загружает сессии из файла"""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    self._stats = data.get('stats', self._stats)
                    
                    for session_data in data.get('sessions', []):
                        session = Session(
                            session_id=session_data['session_id'],
                            created_at=datetime.fromisoformat(
                                session_data['created_at']
                            ),
                            last_active=datetime.fromisoformat(
                                session_data['last_active']
                            ),
                            ip_address=session_data.get('ip_address', ''),
                            user_agent=session_data.get('user_agent', ''),
                            message_count=session_data.get('message_count', 0),
                            settings=session_data.get('settings', {}),
                            metadata=session_data.get('metadata', {})
                        )
                        
                        # Восстанавливаем контекст
                        ctx_data = session_data.get('context', {})
                        session.context = SessionContext(
                            topics_discussed=ctx_data.get('topics_discussed', []),
                            last_intent=ctx_data.get('last_intent', ''),
                            emotion_history=ctx_data.get('emotion_history', []),
                            entities_mentioned=ctx_data.get('entities_mentioned', {}),
                            preferences=ctx_data.get('preferences', {})
                        )
                        
                        # Не загружаем истёкшие
                        if not session.is_expired(self.max_age_hours):
                            self._sessions[session.session_id] = session
                            
                            if session.ip_address:
                                if session.ip_address not in self._ip_index:
                                    self._ip_index[session.ip_address] = set()
                                self._ip_index[session.ip_address].add(
                                    session.session_id
                                )
                        
            except Exception as e:
                logger.warning(f"Ошибка загрузки сессий: {e}")
    
    def _save(self):
        """Сохраняет сессии в файл"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        data = {
            "updated": datetime.now().isoformat(),
            "stats": self._stats,
            "sessions": [s.to_dict() for s in self._sessions.values()]
        }
        
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_session(
        self,
        ip_address: str = "",
        user_agent: str = "",
        settings: Dict = None
    ) -> Session:
        """Создаёт новую сессию"""
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        session = Session(
            session_id=session_id,
            created_at=datetime.now(),
            last_active=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            settings={**self.DEFAULT_SETTINGS, **(settings or {})}
        )
        
        self._sessions[session_id] = session
        self._stats["total_sessions"] += 1
        
        if ip_address:
            if ip_address not in self._ip_index:
                self._ip_index[ip_address] = set()
            self._ip_index[ip_address].add(session_id)
        
        self._save()
        
        logger.info(f"🔐 Session created: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Получает сессию по ID"""
        if session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id]
        
        if session.is_expired(self.max_age_hours):
            self.end_session(session_id)
            return None
        
        session.touch()
        return session
    
    def get_or_create(
        self,
        session_id: str = None,
        ip_address: str = ""
    ) -> Session:
        """Получает существующую или создаёт новую сессию"""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        
        return self.create_session(ip_address=ip_address)
    
    def end_session(self, session_id: str):
        """Завершает сессию"""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            
            if session.ip_address and session.ip_address in self._ip_index:
                self._ip_index[session.ip_address].discard(session_id)
            
            del self._sessions[session_id]
            self._save()
            
            logger.info(f"🔐 Session ended: {session_id}")
    
    def record_message(
        self,
        session_id: str,
        intent: str = None,
        topic: str = None,
        entity: str = None,
        emotion: str = None
    ):
        """Записывает сообщение в контекст сессии"""
        session = self.get_session(session_id)
        if not session:
            return
        
        session.message_count += 1
        self._stats["total_messages"] += 1
        
        if intent:
            session.context.last_intent = intent
        
        if topic:
            session.context.add_topic(topic)
        
        if entity:
            session.context.add_entity(entity)
        
        if emotion:
            session.context.add_emotion(emotion)
        
        self._save()
    
    def update_settings(
        self,
        session_id: str,
        settings: Dict[str, Any]
    ):
        """Обновляет настройки сессии"""
        session = self.get_session(session_id)
        if not session:
            return
        
        session.settings.update(settings)
        self._save()
    
    def get_context_for_prompt(self, session_id: str) -> str:
        """Генерирует контекст для промпта"""
        session = self.get_session(session_id)
        if not session:
            return ""
        
        lines = []
        
        if session.context.topics_discussed:
            recent_topics = session.context.topics_discussed[-5:]
            lines.append(f"Недавние темы: {', '.join(recent_topics)}")
        
        if session.context.entities_mentioned:
            top_entities = sorted(
                session.context.entities_mentioned.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            entities_str = ', '.join(e[0] for e in top_entities)
            lines.append(f"Упоминаемые сущности: {entities_str}")
        
        if session.context.emotion_history:
            recent_emotions = session.context.emotion_history[-3:]
            lines.append(f"Последние эмоции: {', '.join(recent_emotions)}")
        
        if session.settings.get('formality') != 'neutral':
            lines.append(f"Стиль общения: {session.settings['formality']}")
        
        return "\n".join(lines) if lines else ""
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику сессий"""
        self.cleanup_expired()
        
        return {
            "total_sessions": self._stats["total_sessions"],
            "active_sessions": len(self._sessions),
            "total_messages": self._stats["total_messages"],
            "unique_ips": len(self._ip_index),
            "avg_messages_per_session": (
                self._stats["total_messages"] / max(1, len(self._sessions))
            )
        }
    
    def cleanup_expired(self):
        """Удаляет истёкшие сессии"""
        to_remove = [
            sid for sid, session in self._sessions.items()
            if session.is_expired(self.max_age_hours)
        ]
        
        for sid in to_remove:
            self.end_session(sid)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} expired sessions")
    
    def get_sessions_by_ip(self, ip_address: str) -> List[Session]:
        """Возвращает сессии по IP"""
        if ip_address not in self._ip_index:
            return []
        
        return [
            self._sessions[sid]
            for sid in self._ip_index[ip_address]
            if sid in self._sessions
        ]


# Глобальный экземпляр
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Возвращает глобальный менеджер сессий"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager