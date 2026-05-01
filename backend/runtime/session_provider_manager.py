"""
Session Provider Manager — Управление ключами пользователей через LiteLLM

Пользователь вводит ключи → ключи шифруются → сохраняются в БД → используются для чата
"""

from typing import Optional, Dict
from runtime.litellm_service import LiteLLMService
from core.supabase_client import get_supabase
from core.encryption import get_encryptor
import logging
import time
import os

logger = logging.getLogger("padplus.session_provider")


class SessionProviderManager:
    """
    Менеджер провайдеров для сессии пользователя
    
    Использует ТОЛЬКО LiteLLM для всех провайдеров
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        self.encryptor = get_encryptor()
    
    def create_user_manager(self, session_id: str):
        """
        Создаёт персональный менеджер для пользователя
        
        Args:
            session_id: ID сессии (user_id из Supabase Auth)
        
        Returns:
            UserManager с настроенным LiteLLM сервисом
        """
        user_manager = UserManager(session_id, self.supabase, self.encryptor)
        user_manager.load_keys()
        return user_manager


class UserManager:
    """
    Персональный менеджер пользователя
    
    Хранит активные API ключи и создаёт LiteLLM сервисы
    """
    
    def __init__(self, user_id: str, supabase, encryptor):
        self.user_id = user_id
        self.supabase = supabase
        self.encryptor = encryptor
        self.litellm_service: Optional[LiteLLMService] = None
        self.keys: Dict[str, Dict] = {}
        self.is_demo_mode = False
        self.demo_requests_used = 0
        self.demo_max_requests = 50
        self.demo_session_start = None
    
    def load_keys(self):
        """Загружает ключи пользователя из БД"""
        if not self.supabase:
            logger.warning("Supabase не подключен")
            return
        
        # Получаем активные ключи
        result = self.supabase.table("user_api_keys")\
            .select("*")\
            .eq("user_id", self.user_id)\
            .eq("is_active", True)\
            .execute()
        
        if not result.data:
            logger.info(f"У пользователя {self.user_id} нет ключей")
            return
        
        # Находим ключ по умолчанию
        default_key = None
        for key_data in result.data:
            self.keys[key_data["provider"]] = key_data
            if key_data.get("is_default"):
                default_key = key_data
        
        # Создаём LiteLLM сервис с ключом по умолчанию
        if default_key:
            api_key = self.encryptor.decrypt(default_key["api_key_encrypted"])
            model = default_key.get("model_preference")
            
            if api_key and model:
                self.litellm_service = LiteLLMService(
                    api_key=api_key,
                    model=model
                )
                logger.info(f"✅ LiteLLM настроен для {default_key['provider']}: {model}")
            else:
                logger.warning(f"⚠️ Ключ {default_key['provider']} не имеет API ключа или модели")
    
    def has_active_providers(self) -> bool:
        """Проверяет есть ли активные ключи"""
        return self.litellm_service is not None
    
    def get_provider_keys(self, provider: str) -> Optional[Dict]:
        """Получает ключ конкретного провайдера"""
        return self.keys.get(provider)
    
    def enable_demo_mode(self):
        """Включает демо режим с системным ключом"""
        demo_api_key = os.getenv("DEMO_API_KEY")
        demo_model = os.getenv("DEMO_MODEL", "gpt-3.5-turbo")
        
        if demo_api_key:
            self.litellm_service = LiteLLMService(
                api_key=demo_api_key,
                model=demo_model
            )
            self.is_demo_mode = True
            self.demo_session_start = time.time()
            logger.info(f"✅ Демо режим активирован для сессии {self.user_id}")
    
    def can_make_request(self) -> bool:
        """Проверяет может ли пользователь сделать еще запрос в демо режиме"""
        if not self.is_demo_mode:
            return True
        
        # Проверяем лимит запросов
        if self.demo_requests_used >= self.demo_max_requests:
            return False
        
        # Проверяем лимит по времени (15 минут)
        if self.demo_session_start:
            elapsed = time.time() - self.demo_session_start
            if elapsed > 15 * 60:  # 15 минут
                return False
        
        return True
    
    def count_request(self):
        """Увеличивает счетчик запросов в демо режиме"""
        if self.is_demo_mode:
            self.demo_requests_used += 1


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_session_manager = None


def get_session_manager() -> SessionProviderManager:
    """Возвращает глобальный менеджер сессий"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionProviderManager()
    return _session_manager
