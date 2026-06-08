"""
Session Provider Manager — Управление ключами пользователей через LLM провайдеров

Пользователь вводит ключи → ключи шифруются → сохраняются в БД → используются для чата
"""

from typing import Optional, Dict
from core.supabase_client import get_supabase
from core.encryption import get_encryptor
import logging

logger = logging.getLogger("padplus.session_provider")


class SessionProviderManager:
    """
    Менеджер провайдеров для сессии пользователя
    
    Создаёт UserManager для каждого пользователя, который управляет его API ключами.
    Ключи передаются в LLMService.generate() напрямую, а не хранятся в сервисе.
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
            UserManager с загруженными ключами из БД
        """
        user_manager = UserManager(session_id, self.supabase, self.encryptor)
        user_manager.load_keys()
        return user_manager


class UserManager:
    """
    Персональный менеджер пользователя
    
    Хранит активные API ключи (ключи передаются в generate() напрямую)
    
    Методы:
    - load_keys(): Загрузить ключи из БД
    - get_default_key_data(): Получить расшифрованный ключ по умолчанию
    - get_provider_keys(provider): Получить расшифрованный ключ провайдера
    """
    
    def __init__(self, user_id: str, supabase, encryptor):
        self.user_id = user_id
        self.supabase = supabase
        self.encryptor = encryptor
        self.keys: Dict[str, Dict] = {}
    
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
        
        # Сохраняем все ключи
        for key_data in result.data:
            self.keys[key_data["provider"]] = key_data
        
        logger.info(f"✅ Загружено {len(self.keys)} ключей для пользователя {self.user_id}")
    
    def has_active_providers(self) -> bool:
        """Проверяет есть ли активные ключи"""
        return len(self.keys) > 0
    
    def get_default_key(self) -> Optional[Dict]:
        """Получает ключ по умолчанию"""
        for key_data in self.keys.values():
            if key_data.get("is_default"):
                return key_data
        # Если нет default, возвращаем первый
        return next(iter(self.keys.values()), None)
    
    def get_provider_keys(self, provider: str) -> Optional[Dict]:
        """Получает ключ конкретного провайдера (с расшифровкой)"""
        key_data = self.keys.get(provider)
        if not key_data:
            return None
        
        # Расшифровываем ключ
        try:
            api_key = self.encryptor.decrypt(key_data["api_key_encrypted"])
            return {
                "provider": key_data["provider"],
                "api_key": api_key,
                "model_preference": key_data.get("model_preference"),
                "is_default": key_data.get("is_default", False)
            }
        except Exception as e:
            logger.error(f"Ошибка расшифровки ключа: {e}")
            return None
    
    def get_default_key_data(self) -> Optional[Dict]:
        """Получает данные ключа по умолчанию (с расшифровкой)"""
        default_key = self.get_default_key()
        if not default_key:
            return None
        
        try:
            api_key = self.encryptor.decrypt(default_key["api_key_encrypted"])
            return {
                "provider": default_key["provider"],
                "api_key": api_key,
                "model_preference": default_key.get("model_preference"),
                "is_default": default_key.get("is_default", False)
            }
        except Exception as e:
            logger.error(f"Ошибка расшифровки default ключа: {e}")
            return None


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
