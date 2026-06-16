"""
⚡ RateLimiter — Защита от перегрузки

- Ограничение запросов по IP/пользователю
- Скользящее окно (sliding window)
- Настраиваемые лимиты
- Блокировка при превышении
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from enum import Enum
import json
import os
import logging

logger = logging.getLogger("PAD+.ratelimit")


class LimitType(Enum):
    """Типы лимитов"""
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"


@dataclass
class RateLimitConfig:
    """Конфигурация лимита"""
    max_requests: int = 60          # Максимум запросов
    window_seconds: int = 60        # Окно в секундах
    block_duration_seconds: int = 60  # Длительность блокировки
    
    @classmethod
    def per_minute(cls, max_requests: int = 60) -> 'RateLimitConfig':
        return cls(max_requests=max_requests, window_seconds=60)
    
    @classmethod
    def per_hour(cls, max_requests: int = 1000) -> 'RateLimitConfig':
        return cls(max_requests=max_requests, window_seconds=3600)
    
    @classmethod
    def per_day(cls, max_requests: int = 10000) -> 'RateLimitConfig':
        return cls(max_requests=max_requests, window_seconds=86400)


@dataclass
class ClientState:
    """Состояние клиента"""
    client_id: str
    requests: List[datetime] = field(default_factory=list)
    blocked_until: Optional[datetime] = None
    total_requests: int = 0
    total_blocked: int = 0
    
    def is_blocked(self) -> bool:
        if self.blocked_until is None:
            return False
        if datetime.now() > self.blocked_until:
            self.blocked_until = None
            return False
        return True
    
    def cleanup_old_requests(self, window_seconds: int):
        """Удаляет старые запросы за пределами окна"""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        self.requests = [r for r in self.requests if r > cutoff]


class RateLimiter:
    """
    ⚡ Rate Limiter с скользящим окном
    
    Features:
    - Ограничение запросов по клиенту
    - Скользящее окно (более точное чем фиксированное)
    - Настраиваемые лимиты для разных endpoint
    - Автоматическая разблокировка
    """
    
    # Конфигурации по умолчанию для разных endpoint
    DEFAULT_CONFIGS = {
        "default": RateLimitConfig.per_minute(60),
        "chat": RateLimitConfig.per_minute(30),
        "stream": RateLimitConfig.per_minute(10),
        "search": RateLimitConfig.per_minute(100),
        "export": RateLimitConfig.per_hour(10),
    }
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "rate_limits.json"
            )
        self.data_path = data_path
        
        # Состояние клиентов: client_id -> ClientState
        self._clients: Dict[str, ClientState] = {}
        
        # Конфигурации лимитов
        self._configs: Dict[str, RateLimitConfig] = self.DEFAULT_CONFIGS.copy()
        
        # Статистика
        self._stats = {
            "total_requests": 0,
            "total_allowed": 0,
            "total_blocked": 0,
            "unique_clients": 0
        }
        
        self._load()
    
    def _load(self):
        """Загружает состояние из файла"""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    self._stats = data.get('stats', self._stats)
                    
                    for client_id, client_data in data.get('clients', {}).items():
                        self._clients[client_id] = ClientState(
                            client_id=client_id,
                            requests=[datetime.fromisoformat(r) 
                                     for r in client_data.get('requests', [])],
                            blocked_until=datetime.fromisoformat(
                                client_data['blocked_until']
                            ) if client_data.get('blocked_until') else None,
                            total_requests=client_data.get('total_requests', 0),
                            total_blocked=client_data.get('total_blocked', 0)
                        )
                        
            except Exception as e:
                logger.warning(f"Ошибка загрузки rate limits: {e}")
    
    def _save(self):
        """Сохраняет состояние в файл"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        data = {
            "updated": datetime.now().isoformat(),
            "stats": self._stats,
            "clients": {
                client_id: {
                    "requests": [r.isoformat() for r in client.requests[-100:]],
                    "blocked_until": client.blocked_until.isoformat() 
                        if client.blocked_until else None,
                    "total_requests": client.total_requests,
                    "total_blocked": client.total_blocked
                }
                for client_id, client in self._clients.items()
            }
        }
        
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def configure(self, endpoint: str, config: RateLimitConfig):
        """Настраивает лимит для endpoint"""
        self._configs[endpoint] = config
    
    def check(self, client_id: str, endpoint: str = "default") -> Dict[str, Any]:
        """
        Проверяет, разрешён ли запрос
        
        Returns:
            Dict с ключами:
            - allowed: bool
            - remaining: int (оставшиеся запросы)
            - reset_at: datetime (когда сбросится лимит)
            - retry_after: int (секунд до разблокировки, если заблокирован)
        """
        self._stats["total_requests"] += 1
        
        # Получаем конфигурацию
        config = self._configs.get(endpoint, self._configs["default"])
        
        # Получаем или создаём состояние клиента
        if client_id not in self._clients:
            self._clients[client_id] = ClientState(client_id=client_id)
            self._stats["unique_clients"] += 1
        
        client = self._clients[client_id]
        
        # Проверяем блокировку
        if client.is_blocked():
            self._stats["total_blocked"] += 1
            client.total_blocked += 1
            self._save()
            
            retry_after = int((client.blocked_until - datetime.now()).total_seconds())
            return {
                "allowed": False,
                "remaining": 0,
                "reset_at": client.blocked_until.isoformat(),
                "retry_after": max(1, retry_after),
                "reason": "rate_limited"
            }
        
        # Очищаем старые запросы
        client.cleanup_old_requests(config.window_seconds)
        
        # Проверяем лимит
        if len(client.requests) >= config.max_requests:
            # Блокируем клиента
            client.blocked_until = datetime.now() + timedelta(
                seconds=config.block_duration_seconds
            )
            self._stats["total_blocked"] += 1
            client.total_blocked += 1
            self._save()
            
            return {
                "allowed": False,
                "remaining": 0,
                "reset_at": client.blocked_until.isoformat(),
                "retry_after": config.block_duration_seconds,
                "reason": "limit_exceeded"
            }
        
        # Разрешаем запрос
        client.requests.append(datetime.now())
        client.total_requests += 1
        self._stats["total_allowed"] += 1
        
        remaining = config.max_requests - len(client.requests)
        reset_at = datetime.now() + timedelta(seconds=config.window_seconds)
        
        # Периодически сохраняем
        if len(client.requests) % 10 == 0:
            self._save()
        
        return {
            "allowed": True,
            "remaining": remaining,
            "reset_at": reset_at.isoformat(),
            "retry_after": 0
        }
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Возвращает статистику клиента"""
        if client_id not in self._clients:
            return {"error": "client not found"}
        
        client = self._clients[client_id]
        config = self._configs["default"]
        client.cleanup_old_requests(config.window_seconds)
        
        return {
            "client_id": client_id,
            "requests_in_window": len(client.requests),
            "max_requests": config.max_requests,
            "is_blocked": client.is_blocked(),
            "blocked_until": client.blocked_until.isoformat() 
                if client.blocked_until else None,
            "total_requests": client.total_requests,
            "total_blocked": client.total_blocked
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает общую статистику"""
        blocked_clients = sum(
            1 for c in self._clients.values() if c.is_blocked()
        )
        
        return {
            "total_requests": self._stats["total_requests"],
            "total_allowed": self._stats["total_allowed"],
            "total_blocked": self._stats["total_blocked"],
            "unique_clients": self._stats["unique_clients"],
            "currently_blocked": blocked_clients,
            "configs": {
                name: {
                    "max_requests": cfg.max_requests,
                    "window_seconds": cfg.window_seconds
                }
                for name, cfg in self._configs.items()
            }
        }
    
    def reset_client(self, client_id: str):
        """Сбрасывает лимиты для клиента"""
        if client_id in self._clients:
            self._clients[client_id].requests.clear()
            self._clients[client_id].blocked_until = None
            self._save()
    
    def reset_all(self):
        """Сбрасывает все лимиты"""
        self._clients.clear()
        self._stats = {
            "total_requests": 0,
            "total_allowed": 0,
            "total_blocked": 0,
            "unique_clients": 0
        }
        self._save()
    
    def cleanup_inactive(self, max_age_hours: int = 24):
        """Удаляет неактивных клиентов"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for client_id, client in self._clients.items():
            if client.requests:
                last_request = max(client.requests)
                if last_request < cutoff and not client.is_blocked():
                    to_remove.append(client_id)
            elif not client.is_blocked():
                to_remove.append(client_id)
        
        for client_id in to_remove:
            del self._clients[client_id]
        
        if to_remove:
            self._save()
            logger.info(f"Cleaned up {len(to_remove)} inactive clients")


# Глобальный экземпляр
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Возвращает глобальный Rate Limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter