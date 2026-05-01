"""
🗄️ ChromaMemory — Базовый класс для памяти на ChromaDB

Устраняет дублирование кода между:
- FactMemoryChroma
- VectorMemoryChroma
- SmartCacheChroma

Использование:
    class FactMemoryChroma(ChromaMemory):
        def _create_metadata(self, record) -> Dict:
            return {"subject": record.subject, ...}
        
        def _record_from_metadata(self, metadata: Dict) -> Fact:
            return Fact(...)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime
import uuid
import logging

try:
    import chromadb
    from chromadb.api.models.Collection import Collection
    chromadb_available = True
except Exception:
    chromadb = None
    Collection = None
    chromadb_available = False

logger = logging.getLogger("PAD+.chroma_memory")

T = TypeVar('T')  # Тип записи


class ChromaMemory(ABC, Generic[T]):
    """
    🗄️ Базовый класс для памяти на ChromaDB
    
    Предоставляет:
    - Подключение к ChromaDB
    - Базовые методы (store, search, get, delete, clear)
    - Статистику
    - Кэширование
    
    Требует реализации:
    - _create_metadata() — создание метаданных
    - _record_from_metadata() — восстановление записи
    """
    
    DEFAULT_TTL = 3600  # 1 час
    MAX_SIZE = 1000
    COLLECTION_NAME = "base_memory"
    
    def __init__(
        self,
        collection_name: Optional[str] = None,
        db_path: str = "data/chroma"
    ):
        """
        Инициализирует ChromaMemory
        
        Args:
            collection_name: Имя коллекции (по умолчанию CLASS_NAME)
            db_path: Путь к хранилищу ChromaDB
        """
        self.collection_name = collection_name or self.COLLECTION_NAME
        self.db_path = db_path
        
        # Инициализация ChromaDB или SQLite fallback
        if chromadb:
            try:
                self.client = chromadb.PersistentClient(path=db_path)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                self.chroma_available = True
            except Exception:
                self.chroma_available = False
                self._init_sqlite(db_path)
        else:
            self.chroma_available = False
            self._init_sqlite(db_path)

    def _init_sqlite(self, db_path):
        import sqlite3, os
        os.makedirs(db_path, exist_ok=True)
        self.sqlite_path = os.path.join(db_path, "chroma_fallback.db")
        self.sqlite_conn = sqlite3.connect(self.sqlite_path)
        self.sqlite_conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY, document TEXT, metadata TEXT, timestamp REAL
            )
        """)
        self.sqlite_conn.commit()
        self.collection = None
        
        # Кэш
        self._cache: Dict[str, T] = {}
        
        # Статистика
        self._stats = {
            "total_stores": 0,
            "total_searches": 0,
            "total_gets": 0,
            "total_deletes": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info(f"✅ {self.__class__.__name__} инициализирована: {self.collection_name}")
    
    @abstractmethod
    def _create_metadata(self, record: T) -> Dict[str, Any]:
        """
        Создаёт метаданные для записи
        
        Args:
            record: Запись для создания метаданных
        
        Returns:
            Словарь метаданных для ChromaDB
        """
        pass
    
    @abstractmethod
    def _record_from_metadata(self, metadata: Dict[str, Any]) -> T:
        """
        Восстанавливает запись из метаданных
        
        Args:
            metadata: Метаданные из ChromaDB
        
        Returns:
            Восстановленная запись
        """
        pass
    
    def store(self, record: T, ttl: Optional[int] = None) -> str:
        """
        Сохраняет запись
        
        Args:
            record: Запись для сохранения
            ttl: Время жизни в секундах
        
        Returns:
            ID сохранённой записи
        """
        record_id = f"{self.collection_name}_{uuid.uuid4().hex[:8]}"
        
        # Создаём метаданные
        metadata = self._create_metadata(record)
        metadata["created_at"] = datetime.now().isoformat()
        metadata["ttl"] = ttl or self.DEFAULT_TTL
        
        # Сохраняем в ChromaDB
        self.collection.add(
            ids=[record_id],
            documents=[str(record)],
            metadatas=[metadata]
        )
        
        # Кэшируем
        self._cache[record_id] = record
        
        # Статистика
        self._stats["total_stores"] += 1
        
        logger.debug(f"📦 {self.__class__.__name__} store: {record_id}")
        
        return record_id
    
    def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        **kwargs
    ) -> List[T]:
        """
        Ищет записи
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            min_confidence: Минимальная уверенность
            **kwargs: Дополнительные фильтры
        
        Returns:
            Список найденных записей
        """
        # Фильтр по confidence
        where_filter = {}
        if min_confidence > 0:
            where_filter["confidence"] = {"$gte": min_confidence}
        
        # Дополнительные фильтры
        for key, value in kwargs.items():
            if value is not None:
                where_filter[key] = value
        
        # Поиск в ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )
        
        # Восстанавливаем записи
        records = []
        if results["ids"] and results["ids"][0]:
            for metadata in results["metadatas"][0]:
                try:
                    record = self._record_from_metadata(metadata)
                    records.append(record)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to restore record: {e}")
        
        # Статистика
        self._stats["total_searches"] += 1
        
        logger.debug(f"🔍 {self.__class__.__name__} search: {len(records)} results")
        
        return records
    
    def get(self, record_id: str) -> Optional[T]:
        """
        Получает запись по ID
        
        Args:
            record_id: ID записи
        
        Returns:
            Запись или None
        """
        # Проверяем кэш
        if record_id in self._cache:
            self._stats["cache_hits"] += 1
            return self._cache[record_id]
        
        self._stats["cache_misses"] += 1
        
        # Ищем в ChromaDB
        results = self.collection.get(ids=[record_id], include=["metadatas"])
        
        if not results["ids"] or not results["ids"][0]:
            return None
        
        # Восстанавливаем запись
        metadata = results["metadatas"][0]
        record = self._record_from_metadata(metadata)
        
        # Кэшируем
        self._cache[record_id] = record
        
        # Статистика
        self._stats["total_gets"] += 1
        
        logger.debug(f"📥 {self.__class__.__name__} get: {record_id}")
        
        return record
    
    def delete(self, record_id: str) -> bool:
        """
        Удаляет запись по ID
        
        Args:
            record_id: ID записи
        
        Returns:
            True если удалено
        """
        # Удаляем из ChromaDB
        self.collection.delete(ids=[record_id])
        
        # Удаляем из кэша
        if record_id in self._cache:
            del self._cache[record_id]
        
        # Статистика
        self._stats["total_deletes"] += 1
        
        logger.debug(f"🗑️ {self.__class__.__name__} delete: {record_id}")
        
        return True
    
    def clear(self) -> None:
        """Очищает всю память"""
        # Получаем все ID
        results = self.collection.get(include=[])
        
        if results and results["ids"]:
            self.collection.delete(ids=results["ids"])
        
        # Очищаем кэш
        self._cache.clear()
        
        logger.info(f"🗑️ {self.__class__.__name__} cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику
        
        Returns:
            Словарь со статистикой
        """
        total = self.collection.count()
        
        return {
            "total_records": total,
            "collection": self.collection_name,
            "cache_size": len(self._cache),
            **self._stats
        }
    
    def count(self) -> int:
        """
        Возвращает количество записей
        
        Returns:
            Количество записей в коллекции
        """
        return self.collection.count()
    
    def _get_record_text(self, record: T) -> str:
        """
        Возвращает текстовое представление записи для поиска
        
        Args:
            record: Запись
        
        Returns:
            Текстовое представление
        """
        # По умолчанию используем str()
        # Можно переопределить в наследниках
        return str(record)
