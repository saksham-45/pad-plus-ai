"""
🐚 SmartCacheChroma — кратковременная память на ChromaDB

- ChromaDB хранилище
- Семантический поиск (по смыслу)
- TTL = 1 час
- Частые вопросы, случайные связи
- Negative cache (отрицательные результаты)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json
import uuid
import os
from pathlib import Path
from datetime import datetime as dt

try:
    import chromadb
except Exception:
    chromadb = None

from .base import MemoryRecord


class SmartCacheChroma:
    """
    🐚 Шелуха на ChromaDB — кратковременная память с семантическим поиском

    - ChromaDB хранилище
    - Семантический поиск
    - TTL = 1 час (3600 секунд)
    - Частые вопросы, случайные связи
    - Negative cache
    """

    DEFAULT_TTL = 3600  # 1 час
    MAX_SIZE = 1000
    DEFAULT_COLLECTION = "smartcache"

    def __init__(self, collection_name: str = None, db_path: str = None):
        """
        Инициализирует SmartCacheChroma
        
        Args:
            collection_name: Имя коллекции ChromaDB
            db_path: Путь к хранилищу ChromaDB
        """
        if db_path is None:
            db_path = "data/chroma"
        
        self.db_path = db_path
        self.collection_name = collection_name or self.DEFAULT_COLLECTION

        # Инициализируем кэши всегда
        self._cache: Dict[str, MemoryRecord] = {}
        self._negative_cache: Dict[str, datetime] = {}

        # Инициализация ChromaDB или SQLite fallback
        if chromadb:
            try:
                self.client = chromadb.PersistentClient(path=db_path)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                self.chroma_available = True
                print(f"✅ SmartCacheChroma инициализирована: {self.collection_name}")
            except Exception:
                self.chroma_available = False
                self._init_sqlite(db_path)
        else:
            self.chroma_available = False
            self._init_sqlite(db_path)

    def _init_sqlite(self, db_path):
        import sqlite3, os
        os.makedirs(db_path, exist_ok=True)
        self.sqlite_path = os.path.join(db_path, "smartcache_fallback.db")
        self.sqlite_conn = sqlite3.connect(self.sqlite_path)
        self.sqlite_conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                id TEXT PRIMARY KEY, text TEXT, source TEXT,
                confidence REAL, depth INTEGER, metadata TEXT, timestamp REAL
            )
        """)
        self.sqlite_conn.commit()
        print(f"✅ SmartCacheChroma SQLite fallback инициализирован")

    def store(self, text: str, source: str = "user",
              confidence: float = 0.5, ttl: int = None) -> MemoryRecord:
        """
        Сохраняет запись в кэш
        
        Args:
            text: Текст записи
            source: Источник (user, fallback, impulse, reflection)
            confidence: Уверенность (0.0-1.0)
            ttl: Время жизни в секундах
        
        Returns:
            MemoryRecord сохранённой записи
        """
        # Генерируем ID
        record_id = f"cache_{uuid.uuid4().hex[:8]}"
        
        # Создаём запись с тем же ID
        record = MemoryRecord(
            id=record_id,
            text=text,
            metadata={
                "source": source,
                "layer": "husk",
                "confidence": confidence,
                "ttl": ttl or self.DEFAULT_TTL,
            }
        )
        
        # Метаданные для ChromaDB
        # created_at уже строка в isoformat (из base.py)
        chroma_metadata = {
            "text": text,
            "source": source,
            "layer": "husk",
            "confidence": confidence,
            "ttl": ttl or self.DEFAULT_TTL,
            "created_at": record.created_at or dt.now().isoformat(),
        }
        
        # Сохраняем в ChromaDB
        self.collection.add(
            ids=[record_id],
            documents=[text],
            metadatas=[chroma_metadata]
        )
        
        # Кэшируем
        self._cache[record_id] = record
        
        return record

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        """
        Получает запись по ID
        
        Args:
            record_id: ID записи
        
        Returns:
            MemoryRecord или None
        """
        # Проверяем кэш
        if record_id in self._cache:
            record = self._cache[record_id]
            # Проверяем TTL через metadata
            ttl = record.metadata.get('ttl', self.DEFAULT_TTL)
            created_at_str = record.created_at
            if created_at_str:
                try:
                    created_at = dt.fromisoformat(created_at_str)
                    expires_at = created_at + timedelta(seconds=ttl)
                    if datetime.now() <= expires_at:
                        return record
                except (ValueError, TypeError):
                    pass
            # Если записи нет в кэше или истекла
            del self._cache[record_id]
        
        # Ищем в ChromaDB
        results = self.collection.get(ids=[record_id], include=["metadatas", "documents"])
        
        if not results['ids'] or not results['ids'][0]:
            return None
        
        metadata = results['metadatas'][0]
        
        # Получаем text
        text = metadata.get('text', '')
        if not text and results['documents'] and results['documents'][0]:
            text = results['documents'][0]
        
        # Проверяем TTL (обрабатываем пустые/None значения)
        created_at_str = metadata.get('created_at', '')
        if not created_at_str:
            created_at_str = dt.now().isoformat()
        created_at = dt.fromisoformat(created_at_str)
        ttl = metadata.get('ttl', self.DEFAULT_TTL)
        expires_at = created_at + timedelta(seconds=ttl)
        
        if datetime.now() > expires_at:
            # Истёк TTL, удаляем
            self.collection.delete(ids=[record_id])
            return None
        
        # Восстанавливаем MemoryRecord (используем только допустимые поля)
        record = MemoryRecord(
            id=record_id,
            text=text,
            metadata={
                "source": metadata.get('source', 'user'),
                "layer": "husk",
                "confidence": metadata.get('confidence', 0.5),
                "ttl": ttl,
            },
            created_at=created_at_str
        )
        
        # Кэшируем
        self._cache[record_id] = record
        
        return record

    def search(self, query: str, limit: int = 10,
               min_confidence: float = 0.0) -> List[MemoryRecord]:
        """
        Семантический поиск по кэшу
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            min_confidence: Минимальная уверенность
        
        Returns:
            Список найденных MemoryRecord
        """
        # Фильтр по confidence
        where_filter = {"confidence": {"$gte": min_confidence}}
        
        # Поиск в ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Форматируем результаты
        records = []
        if results['ids'] and results['ids'][0]:
            for i, record_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                
                # Проверяем TTL (обрабатываем пустые/None значения)
                created_at_str = metadata.get('created_at', '')
                if not created_at_str:
                    created_at_str = dt.now().isoformat()
                created_at = dt.fromisoformat(created_at_str)
                ttl = metadata.get('ttl', self.DEFAULT_TTL)
                expires_at = created_at + timedelta(seconds=ttl)
                
                if datetime.now() > expires_at:
                    # Истёк TTL, пропускаем
                    continue
                
                # Получаем text
                text = metadata.get('text', '')
                if not text and results['documents'] and results['documents'][0]:
                    text = results['documents'][0]
                
                record = MemoryRecord(
                    id=record_id,
                    text=text,
                    metadata={
                        "source": metadata.get('source', 'user'),
                        "layer": "husk",
                        "confidence": metadata.get('confidence', 0.5),
                        "ttl": ttl,
                    },
                    created_at=created_at_str
                )
                records.append(record)
        
        return records

    def add_negative(self, query: str, ttl: int = 300) -> None:
        """
        Добавляет отрицательный результат (кэш "нет такого")
        
        Args:
            query: Поисковый запрос
            ttl: Время жизни в секундах (по умолчанию 5 минут)
        """
        self._negative_cache[query] = datetime.now() + timedelta(seconds=ttl)

    def is_negative(self, query: str) -> bool:
        """
        Проверяет, есть ли отрицательный результат для запроса
        
        Args:
            query: Поисковый запрос
        
        Returns:
            True если есть отрицательный результат
        """
        if query in self._negative_cache:
            if datetime.now() < self._negative_cache[query]:
                return True
            else:
                del self._negative_cache[query]
        return False

    def delete(self, record_id: str) -> bool:
        """
        Удаляет запись по ID
        
        Args:
            record_id: ID записи
        
        Returns:
            True если удалено
        """
        self.collection.delete(ids=[record_id])
        
        # Удаляем из кэша
        if record_id in self._cache:
            del self._cache[record_id]
        
        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Статистика кэша
        
        Returns:
            Словарь со статистикой
        """
        total = self.collection.count()
        
        # Получаем все записи для статистики
        all_records = []
        if total > 0:
            results = self.collection.get(include=["metadatas"])
            if results['metadatas']:
                all_records = results['metadatas']
        
        # Статистика по источникам
        source_dist = {}
        for meta in all_records:
            source = meta.get('source', 'unknown')
            source_dist[source] = source_dist.get(source, 0) + 1
        
        # Средняя confidence
        avg_conf = sum(m.get('confidence', 0.5) for m in all_records) / len(all_records) if all_records else 0
        
        # Negative cache размер
        negative_size = len(self._negative_cache)
        
        return {
            "total_records": total,
            "source_distribution": source_dist,
            "average_confidence": round(avg_conf, 3),
            "negative_cache_size": negative_size,
            "collection": self.collection_name
        }

    def clear(self):
        """Очищает кэш"""
        # ChromaDB не поддерживает delete(where={}), используем get + delete по ID
        results = self.collection.get(include=[])
        if results and results['ids']:
            self.collection.delete(ids=results['ids'])
        
        self._cache.clear()
        self._negative_cache.clear()
        
        print("🗑️ SmartCacheChroma очищена")


# Глобальный экземпляр
_smartcache_chroma: Optional[SmartCacheChroma] = None


def get_smartcache_chroma() -> SmartCacheChroma:
    """
    Возвращает глобальный SmartCacheChroma
    
    Returns:
        SmartCacheChroma
    """
    global _smartcache_chroma
    if _smartcache_chroma is None:
        _smartcache_chroma = SmartCacheChroma()
    return _smartcache_chroma
