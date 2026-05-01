"""
Session Provider Manager — Управление провайдерами для отдельных пользователей

Обеспечивает изоляцию API ключей между пользователями через сессии.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass

from .provider_manager import ProviderManager, LLMResponse


@dataclass
class UserSession:
    """Сессия пользователя с провайдерами"""
    session_id: str
    user_providers: Dict[str, Dict[str, Any]]
    created_at: datetime
    last_accessed: datetime
    ttl_hours: int = 24
    
    def is_expired(self) -> bool:
        """Проверяет, истекла ли сессия"""
        return datetime.now() > (
            self.last_accessed + timedelta(hours=self.ttl_hours)
        )
    
    def touch(self):
        """Обновляет время последнего доступа"""
        self.last_accessed = datetime.now()


class SessionProviderManager:
    """Менеджер провайдеров с поддержкой пользовательских сессий"""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.system_manager = ProviderManager()
        self.system_manager.setup_from_env()  # Загружаем провайдеры из env
        self.default_ttl_hours = 24
    
    def create_session(self, session_id: str = None) -> str:
        """Создает новую сессию пользователя"""
        if session_id is None:
            session_id = hashlib.md5(
                f"{datetime.now().isoformat()}_{id(self)}".encode()
            ).hexdigest()[:16]
        
        if session_id not in self.sessions:
            self.sessions[session_id] = UserSession(
                session_id=session_id,
                user_providers={},
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Получает сессию пользователя"""
        session = self.sessions.get(session_id)
        if session and not session.is_expired():
            session.touch()
            return session
        elif session and session.is_expired():
            # Удаляем истекшую сессию
            del self.sessions[session_id]
            return None
        return None
    
    def set_user_provider(self, session_id: str, provider_name: str, config: Dict[str, Any]):
        """Устанавливает конфигурацию провайдера для пользователя"""
        session = self.get_session(session_id)
        if not session:
            session_id = self.create_session(session_id)
            session = self.sessions[session_id]
        
        session.user_providers[provider_name] = {
            **config,
            "updated_at": datetime.now().isoformat()
        }
    
    def get_user_providers(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        """Получает конфигурации провайдеров пользователя"""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return session.user_providers
    
    def create_user_manager(self, session_id: str) -> ProviderManager:
        """Создает менеджер провайдеров для конкретного пользователя"""
        user_manager = ProviderManager()
        user_manager.providers.clear()  # Очищаем системные провайдеры
        
        session = self.get_session(session_id)
        if not session:
            return self.system_manager  # Fallback на системные провайдеры
        
        # Создаем провайдеры из конфигурации пользователя
        from .provider_manager import GigaChatProvider, GeminiProvider, OpenRouterProvider
        
        # GigaChat
        gigachat_config = session.user_providers.get("gigachat", {})
        if gigachat_config.get("enabled") and gigachat_config.get("api_key"):
            user_manager.register(GigaChatProvider(
                gigachat_config["api_key"], 
                True
            ))
        
        # Gemini
        gemini_config = session.user_providers.get("gemini", {})
        if gemini_config.get("enabled") and gemini_config.get("api_key"):
            user_manager.register(GeminiProvider(
                gemini_config["api_key"], 
                True
            ))
        
        # OpenRouter
        openrouter_config = session.user_providers.get("openrouter", {})
        if openrouter_config.get("enabled") and openrouter_config.get("api_key"):
            user_manager.register(OpenRouterProvider(
                openrouter_config["api_key"], 
                True,
                openrouter_config.get("model", "google/gemma-7b-it")
            ))
        
        return user_manager
    
    async def generate(self, session_id: str, prompt: str, context: str = "") -> LLMResponse:
        """Генерирует ответ с использованием провайдеров пользователя или системных"""
        user_manager = self.create_user_manager(session_id)
        
        # Если у пользователя есть активные провайдеры, используем их
        if user_manager.has_active_providers():
            return await user_manager.generate(prompt, context)
        
        # Иначе используем системные провайдеры
        if self.system_manager.has_active_providers():
            return await self.system_manager.generate(prompt, context)
        
        # Fallback на SQLite fallback
        return await self.system_manager.fallback.generate(prompt, context)
    
    def get_providers_status(self, session_id: str) -> Dict[str, Any]:
        """Получает статус провайдеров для пользователя"""
        user_manager = self.create_user_manager(session_id)
        user_status = user_manager.get_providers_status()
        
        # Добавляем информацию о том, чьи это провайдеры
        result = {
            "user_providers": user_status,
            "has_user_providers": user_manager.has_active_providers(),
            "session_active": self.get_session(session_id) is not None
        }
        
        # Если у пользователя нет провайдеров, покажем системные
        if not user_manager.has_active_providers():
            result["system_providers"] = self.system_manager.get_providers_status()
            result["has_system_providers"] = self.system_manager.has_active_providers()
        
        return result
    
    async def test_user_provider(self, session_id: str, provider_name: str) -> Dict[str, Any]:
        """Тестирует провайдер пользователя"""
        try:
            user_manager = self.create_user_manager(session_id)
            result = await user_manager.test_provider(provider_name)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка тестирования провайдера {provider_name}: {str(e)}"
            }
    
    def cleanup_expired_sessions(self):
        """Очищает истекшие сессии"""
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        return len(expired_sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Получает статистику сессий"""
        active_sessions = len([s for s in self.sessions.values() if not s.is_expired()])
        total_sessions = len(self.sessions)
        
        return {
            "active_sessions": active_sessions,
            "total_sessions": total_sessions,
            "expired_sessions": total_sessions - active_sessions,
            "system_providers_active": self.system_manager.has_active_providers()
        }


# Глобальный экземпляр
_session_manager: Optional[SessionProviderManager] = None


def get_session_manager() -> SessionProviderManager:
    """Возвращает глобальный менеджер сессий"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionProviderManager()
    return _session_manager
