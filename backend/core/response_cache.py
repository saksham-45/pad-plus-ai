"""
💾 ResponseCache — Умное кэширование ответов

- Семантическое кэширование (похожие запросы)
- TTL для устаревания
- Статистика попаданий
- Экономия LLM запросов
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import json
import os
import hashlib


@dataclass
class CacheEntry:
    """Запись в кэше"""
    query_hash: str
    query_text: str
    response: str
    intent: str
    confidence: float
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "query_hash": self.query_hash,
            "query_text": self.query_text[:100],
            "response": self.response[:200] + "..." if len(self.response) > 200 else self.response,
            "intent": self.intent,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "hit_count": self.hit_count,
            "metadata": self.metadata
        }


class ResponseCache:
    """
    💾 Умное кэширование ответов
    
    Features:
    - Семантическое сходство (похожие запросы)
    - Настраиваемый TTL
    - Автоматическая очистка устаревших
    - Статистика эффективности
    """
    
    # Настройки по умолчанию
    DEFAULT_TTL_HOURS = 24
    MAX_CACHE_SIZE = 1000
    SIMILARITY_THRESHOLD = 0.85  # Для семантического поиска
    
    def __init__(self, data_path: str = None, ttl_hours: int = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "response_cache.json"
            )
        self.data_path = data_path
        self.ttl_hours = ttl_hours or self.DEFAULT_TTL_HOURS
        
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "total_hits": 0,
            "total_misses": 0,
            "total_requests": 0,
            "evicted_entries": 0
        }
        
        self._load()
    
    def _load(self):
        """Загружает кэш из файла"""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for item in data.get('cache', []):
                        entry = CacheEntry(
                            query_hash=item['query_hash'],
                            query_text=item['query_text'],
                            response=item['response'],
                            intent=item.get('intent', 'unknown'),
                            confidence=item.get('confidence', 0.5),
                            created_at=datetime.fromisoformat(item['created_at']),
                            expires_at=datetime.fromisoformat(item['expires_at']),
                            hit_count=item.get('hit_count', 0),
                            metadata=item.get('metadata', {})
                        )
                        
                        # Не загружаем устаревшие
                        if not entry.is_expired():
                            self._cache[entry.query_hash] = entry
                    
                    self._stats = data.get('stats', self._stats)
                    
            except Exception as e:
                print(f"Ошибка загрузки кэша: {e}")
    
    def _save(self):
        """Сохраняет кэш в файл"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        # Очищаем устаревшие перед сохранением
        self._cleanup()
        
        data = {
            "updated": datetime.now().isoformat(),
            "cache": [e.to_dict() for e in self._cache.values()],
            "stats": self._stats
        }
        
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _cleanup(self):
        """Удаляет устаревшие записи"""
        expired = [h for h, e in self._cache.items() if e.is_expired()]
        for h in expired:
            del self._cache[h]
            self._stats["evicted_entries"] += 1
    
    def _hash_query(self, query: str, context: Dict = None) -> str:
        """Создаёт хеш запроса"""
        # Нормализуем запрос
        normalized = query.lower().strip()
        
        # Добавляем важный контекст
        if context:
            important_keys = ["intent", "emotion"]
            for key in important_keys:
                if key in context:
                    normalized += f"|{key}:{context[key]}"
        
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Вычисляет семантическое сходство между текстами
        Простой алгоритм (можно улучшить с эмбеддингами)
        """
        # Токенизация
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def get(self, query: str, context: Dict = None) -> Optional[Tuple[str, float]]:
        """
        Получает ответ из кэша
        
        Returns:
            Tuple (response, confidence) или None
        """
        self._stats["total_requests"] += 1
        
        query_hash = self._hash_query(query, context)
        
        # Прямое попадание
        if query_hash in self._cache:
            entry = self._cache[query_hash]
            
            if not entry.is_expired():
                entry.hit_count += 1
                self._stats["total_hits"] += 1
                self._save()
                return entry.response, entry.confidence
        
        # Семантический поиск похожих
        best_match = None
        best_similarity = 0.0
        
        for entry in self._cache.values():
            if entry.is_expired():
                continue
            
            similarity = self._compute_similarity(query, entry.query_text)
            if similarity > best_similarity and similarity >= self.SIMILARITY_THRESHOLD:
                best_similarity = similarity
                best_match = entry
        
        if best_match:
            best_match.hit_count += 1
            self._stats["total_hits"] += 1
            self._save()
            return best_match.response, best_match.confidence * best_similarity
        
        self._stats["total_misses"] += 1
        return None
    
    def set(
        self,
        query: str,
        response: str,
        intent: str = "unknown",
        confidence: float = 0.5,
        context: Dict = None,
        metadata: Dict = None,
        ttl_hours: int = None
    ):
        """Сохраняет ответ в кэш"""
        # Проверяем размер
        if len(self._cache) >= self.MAX_CACHE_SIZE:
            # Удаляем старые записи
            self._evict_oldest()
        
        query_hash = self._hash_query(query, context)
        ttl = ttl_hours or self.ttl_hours
        
        entry = CacheEntry(
            query_hash=query_hash,
            query_text=query,
            response=response,
            intent=intent,
            confidence=confidence,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=ttl),
            metadata=metadata or {}
        )
        
        self._cache[query_hash] = entry
        self._save()
    
    def _evict_oldest(self, count: int = 10):
        """Удаляет старые записи"""
        # Сортируем по hit_count и created_at
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: (x[1].hit_count, x[1].created_at)
        )
        
        for i in range(min(count, len(sorted_entries))):
            del self._cache[sorted_entries[i][0]]
            self._stats["evicted_entries"] += 1
    
    def invalidate(self, query: str = None, all: bool = False):
        """Инвалидирует кэш"""
        if all:
            self._cache.clear()
            self._save()
            return
        
        if query:
            query_hash = self._hash_query(query)
            if query_hash in self._cache:
                del self._cache[query_hash]
                self._save()
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        total = self._stats["total_requests"]
        hits = self._stats["total_hits"]
        
        hit_rate = hits / total if total > 0 else 0.0
        
        return {
            "total_entries": len(self._cache),
            "total_requests": total,
            "total_hits": hits,
            "total_misses": self._stats["total_misses"],
            "hit_rate": round(hit_rate, 3),
            "evicted_entries": self._stats["evicted_entries"],
            "estimated_savings": hits * 0.01  # Примерная экономия в рублях
        }
    
    def get_top_queries(self, limit: int = 10) -> List[Dict]:
        """Возвращает топ запросов по попаданиям"""
        sorted_entries = sorted(
            self._cache.values(),
            key=lambda x: x.hit_count,
            reverse=True
        )
        
        return [
            {
                "query": e.query_text[:50],
                "hits": e.hit_count,
                "intent": e.intent
            }
            for e in sorted_entries[:limit]
        ]


# Глобальный экземпляр
_response_cache: Optional[ResponseCache] = None


def get_response_cache() -> ResponseCache:
    """Возвращает глобальный кэш"""
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache()
    return _response_cache