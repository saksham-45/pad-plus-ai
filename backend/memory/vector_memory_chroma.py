"""
🌱 VectorMemoryChroma — долговременная память на ChromaDB

- ChromaDB хранилище
- Векторный поиск (семантический, по смыслу)
- TTL = 30 дней
- Факты, уроки, эпизоды
- Поддержка confidence и depth
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json
import uuid
import os
from pathlib import Path

try:
    import chromadb
except Exception:
    chromadb = None

from .base import MemoryRecord


class VectorMemoryChroma:
    """
    🌱 Почва на ChromaDB — долговременная память с векторным поиском

    - ChromaDB хранилище
    - Векторный поиск (семантический)
    - TTL = 30 дней (2592000 секунд)
    - Факты, уроки, эпизоды
    - Поддержка confidence и depth
    """

    DEFAULT_TTL = 2592000  # 30 дней
    DEFAULT_COLLECTION = "vector_memory"

    def __init__(self, collection_name: str = None, db_path: str = None):
        """
        Инициализирует VectorMemoryChroma
        
        Args:
            collection_name: Имя коллекции ChromaDB
            db_path: Путь к хранилищу ChromaDB
        """
        if db_path is None:
            db_path = "data/chroma"
        
        self.db_path = db_path
        self.collection_name = collection_name or self.DEFAULT_COLLECTION

        # Инициализируем кэш всегда
        self._cache: Dict[str, MemoryRecord] = {}

        # Инициализация ChromaDB или SQLite fallback
        if chromadb:
            try:
                self.client = chromadb.PersistentClient(path=db_path)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                self.chroma_available = True
                print(f"✅ VectorMemoryChroma инициализирована: {self.collection_name}")
            except Exception:
                self.chroma_available = False
                self._init_sqlite_fallback(db_path)
        else:
            self.chroma_available = False
            self._init_sqlite_fallback(db_path)

    def _init_sqlite_fallback(self, db_path):
        """Инициализирует SQLite fallback"""
        import sqlite3
        os.makedirs(db_path, exist_ok=True)
        self.sqlite_path = os.path.join(db_path, "vector_fallback.db")
        self.sqlite_conn = sqlite3.connect(self.sqlite_path)
        self.sqlite_conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                text TEXT,
                source TEXT,
                confidence REAL,
                depth INTEGER,
                metadata TEXT,
                timestamp REAL
            )
        """)
        self.sqlite_conn.commit()
        print(f"✅ VectorMemory SQLite fallback инициализирован")

    def store(self, text: str, source: str = "user",
              confidence: float = 0.5, depth: int = 0,
              ttl: int = None, metadata: dict = None) -> MemoryRecord:
        """
        Сохраняет запись в память
        
        Args:
            text: Текст записи
            source: Источник (user, fallback, impulse, reflection)
            confidence: Уверенность (0.0-1.0)
            depth: Глубина (0 = поверхностная, 10+ = глубокая)
            ttl: Время жизни в секундах
            metadata: Дополнительные метаданные
        
        Returns:
            MemoryRecord сохранённой записи
        """
        # Генерируем ID
        record_id = f"vec_{uuid.uuid4().hex[:8]}"
        
        # Создаём запись с тем же ID
        record = MemoryRecord(
            id=record_id,
            text=text,
            metadata={
                "source": source,
                "layer": "soil",
                "confidence": confidence,
                "depth": depth,
                "ttl": ttl or self.DEFAULT_TTL,
                **(metadata or {}),
            }
        )
        
        # Метаданные для ChromaDB (только простые типы)
        chroma_metadata = {
            "text": text,
            "source": source,
            "layer": "soil",
            "confidence": confidence,
            "depth": depth,
            "ttl": ttl or self.DEFAULT_TTL,
            "created_at": record.created_at or "",
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
            return self._cache[record_id]
        
        # Ищем в ChromaDB
        results = self.collection.get(ids=[record_id], include=["metadatas", "documents"])
        
        if not results['ids'] or not results['ids'][0]:
            return None
        
        metadata = results['metadatas'][0]
        
        # === ИСПРАВЛЕНИЕ: Получаем text из metadata или documents ===
        text = metadata.get('text', '')
        if not text and results['documents'] and results['documents'][0]:
            text = results['documents'][0]
        
        # Восстанавливаем MemoryRecord
        record = MemoryRecord(
            id=record_id,
            text=text,  # ← Исправлено
            source=metadata.get('source', 'user'),
            layer="soil",
            confidence=metadata.get('confidence', 0.5),
            depth=metadata.get('depth', 0),
            created_at=datetime.fromisoformat(metadata.get('created_at')),
            ttl=metadata.get('ttl', self.DEFAULT_TTL),
            immutable=metadata.get('immutable', 0) == 1
        )
        
        # Кэшируем
        self._cache[record_id] = record
        
        return record

    def search(self, query: str, limit: int = 10,
               min_confidence: float = 0.0) -> List[MemoryRecord]:
        """
        Семантический поиск по тексту
        
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
                distance = results['distances'][0][i] if results['distances'] else 0
                
                record = MemoryRecord(
                    id=record_id,
                    text=metadata.get('text', results['documents'][0][i]),
                    source=metadata.get('source', 'user'),
                    layer="soil",
                    confidence=metadata.get('confidence', 0.5),
                    depth=metadata.get('depth', 0),
                    created_at=datetime.fromisoformat(metadata.get('created_at')),
                    ttl=metadata.get('ttl', self.DEFAULT_TTL),
                    immutable=metadata.get('immutable', 0) == 1
                )
                records.append(record)
        
        return records

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
        Статистика памяти
        
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
        
        # Средняя глубина
        avg_depth = sum(m.get('depth', 0) for m in all_records) / len(all_records) if all_records else 0
        
        return {
            "total_records": total,
            "source_distribution": source_dist,
            "average_confidence": round(avg_conf, 3),
            "average_depth": round(avg_depth, 1),
            "collection": self.collection_name
        }

    def clear(self):
        """Очищает память"""
        # ChromaDB не поддерживает delete(where={}), используем get + delete по ID
        results = self.collection.get(include=[])
        if results and results['ids']:
            self.collection.delete(ids=results['ids'])
        
        # === ИСПРАВЛЕНИЕ: Очищаем кэш ===
        self._cache.clear()
        
        print("🗑️ VectorMemoryChroma очищена")


# Глобальный экземпляр
_vector_memory_chroma: Optional[VectorMemoryChroma] = None


def get_vector_memory_chroma() -> VectorMemoryChroma:
    """
    Возвращает глобальную VectorMemoryChroma
    
    Returns:
        VectorMemoryChroma
    """
    global _vector_memory_chroma
    if _vector_memory_chroma is None:
        _vector_memory_chroma = VectorMemoryChroma()
    return _vector_memory_chroma
