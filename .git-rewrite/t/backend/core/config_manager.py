"""
⚙️ ConfigManager — Централизованное управление настройками

- Загрузка из .env и config файлов
- Валидация настроек
- Hot reload при изменениях
- Профили конфигурации
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
import json
import os
import sqlite3
# Попробуем импортировать psycopg2, но не будем падать если его нет
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
import logging

logger = logging.getLogger("PAD+.config")


class ConfigSource(Enum):
    """Источники конфигурации"""
    ENV = "env"
    FILE = "file"
    DEFAULT = "default"
    RUNTIME = "runtime"


@dataclass
class ConfigValue:
    """Значение конфигурации"""
    key: str
    value: Any
    source: ConfigSource
    type: str
    description: str = ""
    editable: bool = True
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": str(self.value),
            "source": self.source.value,
            "type": self.type,
            "description": self.description,
            "editable": self.editable
        }


# Конфигурация по умолчанию
DEFAULT_CONFIG = {
    # LLM
    "llm.provider": {
        "value": "gigachat",
        "type": "string",
        "description": "Основной LLM провайдер"
    },
    "llm.model": {
        "value": "GigaChat",
        "type": "string",
        "description": "Модель LLM"
    },
    "llm.temperature": {
        "value": 0.7,
        "type": "float",
        "description": "Температура генерации"
    },
    "llm.max_tokens": {
        "value": 2000,
        "type": "int",
        "description": "Максимум токенов"
    },
    "llm.timeout": {
        "value": 30,
        "type": "int",
        "description": "Таймаут запроса (секунды)"
    },
    
    # Memory
    "memory.rag.max_items": {
        "value": 10000,
        "type": "int",
        "description": "Максимум записей в RAG"
    },
    "memory.rag.similarity_threshold": {
        "value": 0.7,
        "type": "float",
        "description": "Порог схожести для RAG"
    },
    "memory.hygiene.enabled": {
        "value": True,
        "type": "bool",
        "description": "Автоматическая очистка памяти"
    },
    "memory.hygiene.similarity_threshold": {
        "value": 0.85,
        "type": "float",
        "description": "Порог для удаления дубликатов"
    },
    "memory.hygiene.obsolete_days": {
        "value": 90,
        "type": "int",
        "description": "Дни до устаревания"
    },
    
    # Safety
    "safety.strict_mode": {
        "value": False,
        "type": "bool",
        "description": "Строгий режим безопасности"
    },
    "safety.max_requests_per_minute": {
        "value": 60,
        "type": "int",
        "description": "Максимум запросов в минуту"
    },
    "safety.block_duration": {
        "value": 60,
        "type": "int",
        "description": "Длительность блокировки (секунды)"
    },
    
    # Autonomy
    "autonomy.enabled": {
        "value": True,
        "type": "bool",
        "description": "Автономные процессы"
    },
    "autonomy.reflection_interval": {
        "value": 10,
        "type": "int",
        "description": "Интервал рефлексии (сообщения)"
    },
    "autonomy.learning_enabled": {
        "value": True,
        "type": "bool",
        "description": "Автоматическое обучение"
    },
    
    # Cache
    "cache.enabled": {
        "value": True,
        "type": "bool",
        "description": "Кэширование ответов"
    },
    "cache.ttl_hours": {
        "value": 24,
        "type": "int",
        "description": "Время жизни кэша (часы)"
    },
    "cache.max_size": {
        "value": 1000,
        "type": "int",
        "description": "Максимум записей в кэше"
    },
    
    # Session
    "session.max_age_hours": {
        "value": 24,
        "type": "int",
        "description": "Время жизни сессии (часы)"
    },
    
    # System
    "system.log_level": {
        "value": "INFO",
        "type": "string",
        "description": "Уровень логирования"
    },
    "system.debug_mode": {
        "value": False,
        "type": "bool",
        "description": "Режим отладки"
    }
}


class ConfigManager:
    """
    ⚙️ Менеджер конфигурации
    
    Features:
    - Загрузка из .env, config файлов
    - Валидация типов
    - Hot reload
    - Профили (dev, prod, test)
    """
    
    def __init__(self, config_path: str = None, env_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "config.json"
            )
        if env_path is None:
            env_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                ".env"
            )
        
        self.config_path = config_path
        self.env_path = env_path
        
        # Конфигурация: key -> ConfigValue
        self._config: Dict[str, ConfigValue] = {}
        
        # Callback'и при изменении
        self._callbacks: Dict[str, List[Callable]] = {}
        
        # Текущий профиль
        self._profile = "default"
        
        self._load_defaults()
        self._load_from_env()
        self._load_from_file()
    
    def _load_defaults(self):
        """Загружает конфигурацию по умолчанию"""
        for key, cfg in DEFAULT_CONFIG.items():
            self._config[key] = ConfigValue(
                key=key,
                value=cfg["value"],
                source=ConfigSource.DEFAULT,
                type=cfg["type"],
                description=cfg.get("description", ""),
                editable=cfg.get("editable", True)
            )
    
    def _load_from_env(self):
        """Загружает конфигурацию из .env"""
        if not os.path.exists(self.env_path):
            return
        
        try:
            with open(self.env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' not in line:
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    # Конвертируем ключ в наш формат
                    config_key = self._env_to_config_key(key)
                    
                    if config_key in self._config:
                        parsed = self._parse_value(
                            value, 
                            self._config[config_key].type
                        )
                        self._config[config_key].value = parsed
                        self._config[config_key].source = ConfigSource.ENV
                        
        except Exception as e:
            logger.warning(f"Ошибка загрузки .env: {e}")
    
    def _env_to_config_key(self, env_key: str) -> str:
        """Конвертирует ключ .env в ключ конфигурации"""
        # GIGACHAT_API_KEY -> llm.api_key
        # SAFETY_STRICT_MODE -> safety.strict_mode
        mapping = {
            "GIGACHAT_API_KEY": "llm.api_key",
            "GIGACHAT_ENABLED": "llm.enabled",
            "SAFETY_STRICT_MODE": "safety.strict_mode",
            "MAX_REQUESTS_PER_MINUTE": "safety.max_requests_per_minute",
            "RAG_MAX_ITEMS": "memory.rag.max_items",
            "HYGIENE_SIMILARITY_THRESHOLD": "memory.hygiene.similarity_threshold"
        }
        return mapping.get(env_key, env_key.lower().replace('_', '.'))
    
    def _parse_value(self, value: str, type_name: str) -> Any:
        """Парсит значение по типу"""
        if type_name == "int":
            return int(value)
        elif type_name == "float":
            return float(value)
        elif type_name == "bool":
            return value.lower() in ('true', '1', 'yes', 'on')
        else:
            return value
    
    def _load_from_file(self):
        """Загружает конфигурацию из файла"""
        if not os.path.exists(self.config_path):
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                profile = data.get('profile', 'default')
                self._profile = profile
                
                for key, value in data.get('config', {}).items():
                    if key in self._config:
                        self._config[key].value = value
                        self._config[key].source = ConfigSource.FILE
                    else:
                        self._config[key] = ConfigValue(
                            key=key,
                            value=value,
                            source=ConfigSource.FILE,
                            type="string"
                        )
                        
        except Exception as e:
            logger.warning(f"Ошибка загрузки config: {e}")
    
    def _save(self):
        """Сохраняет конфигурацию в файл"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        data = {
            "updated": datetime.now().isoformat(),
            "profile": self._profile,
            "config": {
                k: v.value for k, v in self._config.items()
                if v.source in [ConfigSource.FILE, ConfigSource.RUNTIME]
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получает значение конфигурации"""
        if key in self._config:
            return self._config[key].value
        return default
    
    def set(
        self, 
        key: str, 
        value: Any,
        description: str = None
    ):
        """Устанавливает значение конфигурации"""
        if key in self._config:
            self._config[key].value = value
            self._config[key].source = ConfigSource.RUNTIME
            self._config[key].updated_at = datetime.now()
            
            if description:
                self._config[key].description = description
        else:
            self._config[key] = ConfigValue(
                key=key,
                value=value,
                source=ConfigSource.RUNTIME,
                type=type(value).__name__
            )
        
        self._save()
        
        # Вызываем callback'и
        self._emit_change(key, value)
    
    def _emit_change(self, key: str, value: Any):
        """Вызывает callback'и при изменении"""
        if key in self._callbacks:
            for callback in self._callbacks[key]:
                try:
                    callback(key, value)
                except Exception as e:
                    logger.warning(f"Callback error for {key}: {e}")
    
    def on_change(self, key: str, callback: Callable):
        """Регистрирует callback при изменении"""
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)
    
    def get_all(self) -> Dict[str, Any]:
        """Возвращает всю конфигурацию"""
        return {k: v.to_dict() for k, v in self._config.items()}
    
    def get_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """Возвращает конфигурацию по префиксу"""
        return {
            k: v.value for k, v in self._config.items()
            if k.startswith(prefix)
        }
    
    def get_profile(self) -> str:
        """Возвращает текущий профиль"""
        return self._profile
    
    def set_profile(self, profile: str):
        """Устанавливает профиль"""
        self._profile = profile
        self._save()
    
    def export_env(self) -> str:
        """Экспортирует в формат .env"""
        lines = []
        for key, cfg in self._config.items():
            env_key = key.upper().replace('.', '_')
            lines.append(f"{env_key}={cfg.value}")
        return '\n'.join(lines)
    
    def reset(self, key: str = None):
        """Сбрасывает к значениям по умолчанию"""
        if key:
            if key in DEFAULT_CONFIG:
                self._config[key].value = DEFAULT_CONFIG[key]["value"]
                self._config[key].source = ConfigSource.DEFAULT
        else:
            self._load_defaults()
        
        self._save()
    
    def validate(self) -> List[str]:
        """Валидирует конфигурацию"""
        errors = []
        
        # Проверка типов
        for key, cfg in self._config.items():
            expected_type = cfg.type
            actual_type = type(cfg.value).__name__
            
            if expected_type == "int" and not isinstance(cfg.value, int):
                errors.append(f"{key}: expected int, got {actual_type}")
            elif expected_type == "float" and not isinstance(
                cfg.value, (int, float)
            ):
                errors.append(f"{key}: expected float, got {actual_type}")
            elif expected_type == "bool" and not isinstance(cfg.value, bool):
                errors.append(f"{key}: expected bool, got {actual_type}")
        
        # Проверка диапазонов
        temp = self.get("llm.temperature", 0.7)
        if not 0 <= temp <= 2:
            errors.append(f"llm.temperature: {temp} out of range [0, 2]")
        
        return errors


# Глобальный экземпляр
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Возвращает глобальный менеджер конфигурации"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_database_url() -> str:
    """Получить URL базы данных из переменных окружения"""
    return os.getenv('DATABASE_URL', 'sqlite:///./data/memory.db')


def get_database_connection():
    """Получить подключение к базе данных"""
    db_url = get_database_url()
    
    if db_url.startswith('postgresql'):
        # PostgreSQL (Supabase)
        return psycopg2.connect(db_url)
    else:
        # SQLite (локальная разработка)
        # Заменяем sqlite:/// на путь к файлу
        db_path = db_url.replace('sqlite:///', '')
        return sqlite3.connect(db_path)


def test_database_connection():
    """Тест подключения к базе данных"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        db_url = get_database_url()
        if db_url.startswith('postgresql'):
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Подключено к PostgreSQL: {version[0]}")
        else:
            cursor.execute("SELECT sqlite_version();")
            version = cursor.fetchone()
            print(f"✅ Подключено к SQLite: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False