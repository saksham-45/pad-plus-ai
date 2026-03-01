"""
🌱 Почва (VectorMemory) — долговременная память

- SQLite хранилище
- TTL = 30 дней
- Факты, уроки, эпизоды
- Поддержка confidence и depth
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import sqlite3
import json
import uuid
import os
from pathlib import Path

from .smartcache import MemoryRecord


class VectorMemory:
    """
    🌱 Почва — долговременная память
    
    - SQLite хранилище
    - TTL = 30 дней (2592000 секунд)
    - Факты, уроки, эпизоды
    - Поддержка confidence и depth
    """
    
    DEFAULT_TTL = 2592000  # 30 дней
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "memory.db"
            )
        self.db_path = db_path
        self._ensure_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Создаёт соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_tables(self):
        """Создаёт таблицы если не существуют"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Таблица памяти (почва)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_soil (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                source TEXT DEFAULT 'user',
                layer TEXT DEFAULT 'soil',
                confidence REAL DEFAULT 0.5,
                depth INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                ttl INTEGER DEFAULT 2592000,
                immutable INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Индекс для поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_text 
            ON memory_soil(text)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_confidence 
            ON memory_soil(confidence)
        """)
        
        conn.commit()
        conn.close()
    
    def store(self, text: str, source: str = "user",
              confidence: float = 0.5, depth: int = 0,
              ttl: int = None, metadata: dict = None) -> MemoryRecord:
        """Сохраняет запись в память"""
        record = MemoryRecord(
            text=text,
            source=source,
            layer="soil",
            confidence=confidence,
            depth=depth,
            ttl=ttl or self.DEFAULT_TTL,
            metadata=metadata or {}
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO memory_soil 
            (id, text, source, layer, confidence, depth, created_at, ttl, immutable, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            record.text,
            record.source,
            record.layer,
            record.confidence,
            record.depth,
            record.created_at.isoformat(),
            record.ttl,
            1 if record.immutable else 0,
            json.dumps(record.metadata, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
        
        return record
    
    def get(self, record_id: str) -> Optional[MemoryRecord]:
        """Получает запись по ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM memory_soil WHERE id = ?", (record_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_record(row)
        return None
    
    def search(self, query: str, limit: int = 10,
               min_confidence: float = 0.0) -> List[MemoryRecord]:
        """Поиск по тексту"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM memory_soil 
            WHERE text LIKE ? AND confidence >= ?
            ORDER BY confidence DESC, created_at DESC
            LIMIT ?
        """, (f"%{query}%", min_confidence, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_record(row) for row in rows]
    
    def get_by_source(self, source: str, limit: int = 100) -> List[MemoryRecord]:
        """Получает записи по источнику"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM memory_soil 
            WHERE source = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (source, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_record(row) for row in rows]
    
    def get_low_confidence(self, threshold: float = 0.5,
                           limit: int = 100) -> List[MemoryRecord]:
        """Получает записи с низкой уверенностью"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM memory_soil 
            WHERE confidence < ?
            ORDER BY confidence ASC, created_at DESC
            LIMIT ?
        """, (threshold, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_record(row) for row in rows]
    
    def update_confidence(self, record_id: str, delta: float) -> bool:
        """Обновляет confidence записи"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Получаем текущий confidence
        cursor.execute(
            "SELECT confidence FROM memory_soil WHERE id = ?", (record_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        new_confidence = max(0.0, min(1.0, row['confidence'] + delta))
        
        cursor.execute(
            "UPDATE memory_soil SET confidence = ? WHERE id = ?",
            (new_confidence, record_id)
        )
        
        conn.commit()
        conn.close()
        
        return True
    
    def delete(self, record_id: str) -> bool:
        """Удаляет запись (если не immutable)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Проверяем immutable
        cursor.execute(
            "SELECT immutable FROM memory_soil WHERE id = ?", (record_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        if row['immutable']:
            conn.close()
            return False
        
        cursor.execute("DELETE FROM memory_soil WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        
        return True
    
    def get_all(self, limit: int = 1000) -> List[MemoryRecord]:
        """Получает все записи"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM memory_soil 
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_record(row) for row in rows]
    
    def count(self) -> int:
        """Возвращает количество записей"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as cnt FROM memory_soil")
        row = cursor.fetchone()
        conn.close()
        
        return row['cnt'] if row else 0
    
    def cleanup_expired(self) -> int:
        """Удаляет устаревшие записи"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Вычисляем пороговую дату
        now = datetime.now()
        
        # Получаем все записи
        cursor.execute("SELECT id, created_at, ttl, immutable FROM memory_soil")
        rows = cursor.fetchall()
        
        deleted = 0
        for row in rows:
            if row['immutable']:
                continue
            
            created = datetime.fromisoformat(row['created_at'])
            expires = created + timedelta(seconds=row['ttl'])
            
            if now > expires:
                cursor.execute("DELETE FROM memory_soil WHERE id = ?", (row['id'],))
                deleted += 1
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        """Преобразует строку БД в MemoryRecord"""
        return MemoryRecord(
            id=row['id'],
            text=row['text'],
            source=row['source'],
            layer=row['layer'],
            confidence=row['confidence'],
            depth=row['depth'],
            created_at=datetime.fromisoformat(row['created_at']),
            ttl=row['ttl'],
            immutable=bool(row['immutable']),
            metadata=json.loads(row['metadata'])
        )


# Глобальный экземпляр
_soil_memory: Optional[VectorMemory] = None


def get_soil_memory() -> VectorMemory:
    """Возвращает глобальную память почвы"""
    global _soil_memory
    if _soil_memory is None:
        _soil_memory = VectorMemory()
    return _soil_memory