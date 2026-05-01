"""
🗄️ CacheManager — Система кэширования для PAD+ AI

Интегрирует Redis для:
- Кэширования ответов LLM
- Сессионного хранения
- Кэширования RAG запросов
- Rate limiting
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional, List
from datetime import datetime

import aioredis
from cachetools import TTLCache

from core.config_manager import get_config

logger = logging.getLogger("padplus.cache")


class CacheManager:
    """
    🗄️ Менеджер кэширования
    
    Предоставляет многоуровневое кэширование:
    - L1: In-memory cache (TTLCache)
    - L2: Redis cache (persistent)
    """
    
    def __init__(self):
        self.config = get_config()
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis: Optional[aioredis.Redis] = None
        
        # In-memory cache (L1)
        self.memory_cache = TTLCache(
            maxsize=1000,
            ttl=self.config.get("cache.ttl", 3600)
        )
        
        # Статистика
        self.stats = {
            "memory_hits": 0,
            "memory_misses": 0,
            "redis_hits": 0,
            "redis_misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    async def connect(self):
        """Подключается к Redis"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("🗄️ Redis подключен")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Redis: {e}")
            self.redis = None
    
    async def disconnect(self):
        """Отключается от Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("🗄️ Redis отключен")
    
    def _get_key(self, namespace: str, key: str) -> str:
        """Генерирует ключ для кэша"""
        return f"padplus:{namespace}:{key}"
    
    def _serialize(self, data: Any) -> str:
        """Сериализует данные в JSON"""
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"❌ Ошибка сериализации: {e}")
            return str(data)
    
    def _deserialize(self, data: str) -> Any:
        """Десериализует JSON в данные"""
        try:
            return json.loads(data)
        except Exception:
            return data
    
    # === L1 Cache (Memory) ===
    def get_memory(self, namespace: str, key: str) -> Optional[Any]:
        """Получает данные из in-memory кэша"""
        cache_key = self._get_key(namespace, key)
        value = self.memory_cache.get(cache_key)
        
        if value is not None:
            self.stats["memory_hits"] += 1
            logger.debug(f"🗄️ Memory cache hit: {cache_key}")
        else:
            self.stats["memory_misses"] += 1
        
        return value
    
    def set_memory(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None):
        """Сохраняет данные в in-memory кэш"""
        cache_key = self._get_key(namespace, key)
        self.memory_cache[cache_key] = value
        self.stats["sets"] += 1
        logger.debug(f"🗄️ Memory cache set: {cache_key}")
    
    def delete_memory(self, namespace: str, key: str):
        """Удаляет данные из in-memory кэша"""
        cache_key = self._get_key(namespace, key)
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
            self.stats["deletes"] += 1
            logger.debug(f"🗄️ Memory cache delete: {cache_key}")
    
    # === L2 Cache (Redis) ===
    async def get_redis(self, namespace: str, key: str) -> Optional[Any]:
        """Получает данные из Redis"""
        if not self.redis:
            return None
        
        cache_key = self._get_key(namespace, key)
        try:
            data = await self.redis.get(cache_key)
            if data:
                value = self._deserialize(data)
                self.stats["redis_hits"] += 1
                logger.debug(f"🗄️ Redis cache hit: {cache_key}")
                return value
            else:
                self.stats["redis_misses"] += 1
        except Exception as e:
            logger.error(f"❌ Ошибка Redis get: {e}")
        
        return None
    
    async def set_redis(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None):
        """Сохраняет данные в Redis"""
        if not self.redis:
            return
        
        cache_key = self._get_key(namespace, key)
        try:
            data = self._serialize(value)
            if ttl:
                await self.redis.setex(cache_key, ttl, data)
            else:
                await self.redis.set(cache_key, data)
            self.stats["sets"] += 1
            logger.debug(f"🗄️ Redis cache set: {cache_key}, TTL: {ttl}")
        except Exception as e:
            logger.error(f"❌ Ошибка Redis set: {e}")
    
    async def delete_redis(self, namespace: str, key: str):
        """Удаляет данные из Redis"""
        if not self.redis:
            return
        
        cache_key = self._get_key(namespace, key)
        try:
            await self.redis.delete(cache_key)
            self.stats["deletes"] += 1
            logger.debug(f"🗄️ Redis cache delete: {cache_key}")
        except Exception as e:
            logger.error(f"❌ Ошибка Redis delete: {e}")
    
    # === Multi-level Cache ===
    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Получает данные из кэша (L1 -> L2)"""
        # Сначала пробуем L1
        value = self.get_memory(namespace, key)
        if value is not None:
            return value
        
        # Если нет в L1, пробуем L2
        value = await self.get_redis(namespace, key)
        if value is not None:
            # Подгружаем в L1 для ускорения
            self.set_memory(namespace, key, value)
            return value
        
        return None
    
    async def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None):
        """Сохраняет данные в кэш (L1 + L2)"""
        # Сохраняем в L1
        self.set_memory(namespace, key, value, ttl)

        # Сохраняем в L2
        await self.set_redis(namespace, key, value, ttl)
    
    async def delete(self, namespace: str, key: str):
        """Удаляет данные из кэша (L1 + L2)"""
        self.delete_memory(namespace, key)
        await self.delete_redis(namespace, key)
    
    # === Специализированные методы ===
    async def cache_llm_response(self, prompt: str, response: str, 
                                provider: str, ttl: Optional[int] = None):
        """Кэширует ответ LLM"""
        if not ttl:
            ttl = self.config.get("cache.llm_ttl", 1800)  # 30 минут
        
        cache_key = f"llm:{provider}:{hash(prompt)}"
        data = {
            "prompt": prompt,
            "response": response,
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            "ttl": ttl
        }
        
        await self.set("llm", cache_key, data, ttl)
        logger.info(f"🗄️ LLM response cached: {provider}, prompt hash: {hash(prompt)}")
    
    async def get_cached_llm_response(self, prompt: str, provider: str) -> Optional[str]:
        """Получает закэшированный ответ LLM"""
        cache_key = f"llm:{provider}:{hash(prompt)}"
        data = await self.get("llm", cache_key)
        if data:
            return data.get("response")
        return None
    
    async def cache_rag_result(self, query: str, result: List[Dict], ttl: Optional[int] = None):
        """Кэширует результат RAG запроса"""
        if not ttl:
            ttl = self.config.get("cache.rag_ttl", 600)  # 10 минут
        
        cache_key = f"rag:{hash(query)}"
        data = {
            "query": query,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "ttl": ttl
        }
        
        await self.set("rag", cache_key, data, ttl)
        logger.info(f"🗄️ RAG result cached: query hash: {hash(query)}")
    
    async def get_cached_rag_result(self, query: str) -> Optional[List[Dict]]:
        """Получает закэшированный результат RAG"""
        cache_key = f"rag:{hash(query)}"
        data = await self.get("rag", cache_key)
        if data:
            return data.get("result")
        return None
    
    # === Session Management ===
    async def store_session(self, session_id: str, data: Dict, ttl: Optional[int] = None):
        """Сохраняет сессионные данные"""
        if not ttl:
            ttl = self.config.get("session.ttl_hours", 24) * 3600  # hours to seconds
        
        await self.set("session", session_id, data, ttl)
        logger.debug(f"🗄️ Session stored: {session_id}")
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Получает сессионные данные"""
        return await self.get("session", session_id)
    
    async def delete_session(self, session_id: str):
        """Удаляет сессионные данные"""
        await self.delete("session", session_id)
        logger.debug(f"🗄️ Session deleted: {session_id}")
    
    # === Rate Limiting ===
    async def is_rate_limited(self, key: str, limit: int, window: int) -> bool:
        """Проверяет rate limit"""
        cache_key = f"rate_limit:{key}"
        current_time = int(time.time())
        window_start = current_time - window
        
        try:
            # Получаем текущие запросы
            requests = await self.get_redis("rate_limit", cache_key)
            if not requests:
                requests = []
            
            # Фильтруем запросы в пределах окна
            requests = [req for req in requests if req > window_start]
            
            # Проверяем лимит
            if len(requests) >= limit:
                return True
            
            # Добавляем новый запрос
            requests.append(current_time)
            await self.set_redis("rate_limit", cache_key, requests, window)
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка rate limiting: {e}")
            return False
    
    # === Statistics ===
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэширования"""
        memory_hit_rate = self.stats["memory_hits"] / max(
            self.stats["memory_hits"] + self.stats["memory_misses"], 1
        )
        
        redis_hit_rate = self.stats["redis_hits"] / max(
            self.stats["redis_hits"] + self.stats["redis_misses"], 1
        )
        
        return {
            "memory": {
                "hit_rate": round(memory_hit_rate, 3),
                "hits": self.stats["memory_hits"],
                "misses": self.stats["memory_misses"],
                "size": len(self.memory_cache)
            },
            "redis": {
                "hit_rate": round(redis_hit_rate, 3),
                "hits": self.stats["redis_hits"],
                "misses": self.stats["redis_misses"],
                "connected": self.redis is not None
            },
            "total": {
                "sets": self.stats["sets"],
                "deletes": self.stats["deletes"]
            }
        }
    
    async def clear_namespace(self, namespace: str):
        """Очищает кэш по namespace"""
        # Очищаем L1
        keys_to_delete = [
            k for k in self.memory_cache.keys() 
            if k.startswith(f"padplus:{namespace}:")
        ]
        for key in keys_to_delete:
            del self.memory_cache[key]

        # Очищаем L2
        if self.redis:
            pattern = f"padplus:{namespace}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        
        logger.info(f"🗄️ Cache cleared for namespace: {namespace}")


# Глобальный экземпляр
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Возвращает глобальный менеджер кэширования"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager