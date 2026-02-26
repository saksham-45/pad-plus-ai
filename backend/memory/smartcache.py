"""
Трёхслойная память NeuroMind AI

🐚 Шелуха (SmartCache) — кратковременная память (TTL=1 час)
🌱 Почва (VectorMemory) — долговременная память (TTL=30 дней)
🌳 Корни (KnowledgeBase) — неизменяемое ядро (бессрочно)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json
import uuid
import threading
import time


@dataclass
class MemoryRecord:
    """Запись в памяти"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    source: str = "user"  # user, fallback, impulse, reflection
    layer: str = "husk"  # husk, soil, roots
    confidence: float = 0.5
    depth: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    ttl: int = 3600  # секунд (1 час для шелухи)
    immutable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Проверяет, истёк ли TTL"""
        if self.immutable:
            return False
        expires_at = self.created_at + timedelta(seconds=self.ttl)
        return datetime.now() > expires_at
    
    def to_dict(self) -> dict:
        """Преобразует запись в словарь"""
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "layer": self.layer,
            "confidence": self.confidence,
            "depth": self.depth,
            "created_at": self.created_at.isoformat(),
            "ttl": self.ttl,
            "immutable": self.immutable,
            "metadata": self.metadata
        }


class SmartCache:
    """
    🐚 Шелуха — кратковременная память
    
    - RAM LRU кэш
    - TTL = 1 час
    - Частые вопросы, случайные связи
    - Negative cache (отрицательные результаты)
    """
    
    DEFAULT_TTL = 3600  # 1 час
    MAX_SIZE = 1000
    
    def __init__(self, max_size: int = None):
        self.max_size = max_size or self.MAX_SIZE
        self._cache: Dict[str, MemoryRecord] = {}
        self._negative_cache: Dict[str, datetime] = {}
        self._lock = threading.RLock()
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Запускает фоновую очистку устаревших записей"""
        def cleanup():
            while True:
                time.sleep(60)  # Каждую минуту
                self._cleanup_expired()
        
        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()
    
    def _cleanup_expired(self):
        """Удаляет устаревшие записи"""
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired:
                del self._cache[key]
    
    def store(self, text: str, source: str = "user", 
              confidence: float = 0.5, ttl: int = None) -> MemoryRecord:
        """Сохраняет запись в кэш"""
        with self._lock:
            # Если кэш полон, удаляем самые старые
            if len(self._cache) >= self.max_size:
                oldest = min(self._cache.items(), 
                           key=lambda x: x[1].created_at)
                del self._cache[oldest[0]]
            
            record = MemoryRecord(
                text=text,
                source=source,
                layer="husk",
                confidence=confidence,
                ttl=ttl or self.DEFAULT_TTL
            )
            self._cache[record.id] = record
            return record
    
    def get(self, record_id: str) -> Optional[MemoryRecord]:
        """Получает запись по ID"""
        with self._lock:
            record = self._cache.get(record_id)
            if record and not record.is_expired():
                return record
            return None
    
    def search(self, query: str, limit: int = 10) -> List[MemoryRecord]:
        """Простой поиск по тексту"""
        with self._lock:
            results = []
            query_lower = query.lower()
            for record in self._cache.values():
                if record.is_expired():
                    continue
                if query_lower in record.text.lower():
                    results.append(record)
                    if len(results) >= limit:
                        break
            return results
    
    def get_all(self) -> List[MemoryRecord]:
        """Возвращает все неистёкшие записи"""
        with self._lock:
            return [r for r in self._cache.values() if not r.is_expired()]
    
    def clear(self) -> int:
        """Очищает кэш"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def add_negative(self, query: str):
        """Добавляет в negative cache"""
        self._negative_cache[query] = datetime.now()
    
    def is_negative(self, query: str) -> bool:
        """Проверяет, есть ли в negative cache"""
        if query in self._negative_cache:
            # Удаляем если старше 1 часа
            age = datetime.now() - self._negative_cache[query]
            if age > timedelta(hours=1):
                del self._negative_cache[query]
                return False
            return True
        return False


# Глобальный экземпляр
_husk_cache: Optional[SmartCache] = None


def get_husk_cache() -> SmartCache:
    """Возвращает глобальный кэш шелухи"""
    global _husk_cache
    if _husk_cache is None:
        _husk_cache = SmartCache()
    return _husk_cache