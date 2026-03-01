"""
📝 FactMemory — Атомарные факты NeuroMind AI

Хранит факты отдельно от личности:
- subject, predicate, object
- confidence, status
- source, timestamps
- NEVER mixes with persona
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import sqlite3
import math
import logging

logger = logging.getLogger("neuromind.facts")


class FactStatus(Enum):
    """Статус факта"""
    HYPOTHESIS = "hypothesis"       # Предположение
    SUPPORTED = "supported"         # Подтверждено
    CONTRADICTED = "contradicted"   # Опровергнуто
    OBSOLETE = "obsolete"           # Устарело
    UNKNOWN = "unknown"             # Неизвестно


@dataclass
class Fact:
    """
    Атомарный факт
    
    Тройка (subject, predicate, object) с метаданными.
    Может пересматриваться, забываться, обновляться.
    """
    id: str
    subject: str
    predicate: str
    object: str
    confidence: float = 0.5
    status: FactStatus = FactStatus.HYPOTHESIS
    source: str = "unknown"         # Откуда факт
    source_id: str = ""             # ID источника (claim_id, dialog_id)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    decay_rate: float = 0.1         # Скорость забывания
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "triple": {
                "subject": self.subject,
                "predicate": self.predicate,
                "object": self.object
            },
            "confidence": round(self.confidence, 3),
            "status": self.status.value,
            "source": self.source,
            "source_id": self.source_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count
        }
    
    def to_tuple(self) -> Tuple[str, str, str]:
        """Возвращает (subject, predicate, object)"""
        return (self.subject, self.predicate, self.object)
    
    def to_sentence(self) -> str:
        """Возвращает как предложение"""
        return f"{self.subject} {self.predicate} {self.object}"


class FactMemory:
    """
    📝 FactMemory — хранилище атомарных фактов
    
    Ключевые особенности:
    - Факты НЕ смешиваются с личностью
    - Автоматическое старение (decay)
    - Поддержка ревизии фактов
    - Поиск по субъекту/предикату/объекту
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "facts.db"
            )
        self.db_path = db_path
        self._ensure_tables()
        
        # Кэш
        self._fact_cache: Dict[str, Fact] = {}
        self._subject_index: Dict[str, List[str]] = {}
    
    def _ensure_tables(self):
        """Создаёт таблицы БД"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                confidence REAL,
                status TEXT,
                source TEXT,
                source_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                accessed_at TEXT,
                access_count INTEGER DEFAULT 0,
                decay_rate REAL DEFAULT 0.1,
                metadata TEXT
            )
        """)
        
        # Индексы для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_predicate ON facts(predicate)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_object ON facts(object)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_confidence ON facts(confidence)
        """)
        
        conn.commit()
        conn.close()
    
    def add(
        self,
        subject: str,
        predicate: str,
        object: str,
        confidence: float = 0.5,
        source: str = "unknown",
        source_id: str = "",
        status: FactStatus = FactStatus.HYPOTHESIS,
        metadata: Dict = None
    ) -> Fact:
        """
        Добавляет факт в память
        
        Если факт уже существует — обновляет confidence
        """
        import uuid
        
        # Проверяем на дубликат
        existing = self.find_exact(subject, predicate, object)
        if existing:
            # Обновляем существующий
            existing.confidence = min(
                existing.confidence + confidence * 0.3,
                0.95
            )
            existing.updated_at = datetime.now()
            existing.access_count += 1
            self._save_fact(existing)
            logger.debug(f"Обновлён факт: {subject} {predicate} {object}")
            return existing
        
        # Создаём новый факт
        fact = Fact(
            id=f"fact_{uuid.uuid4().hex[:8]}",
            subject=subject.lower().strip(),
            predicate=predicate.lower().strip(),
            object=object.lower().strip(),
            confidence=confidence,
            status=status,
            source=source,
            source_id=source_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            accessed_at=datetime.now(),
            access_count=1,
            metadata=metadata or {}
        )
        
        self._save_fact(fact)
        
        # Обновляем индекс
        if fact.subject not in self._subject_index:
            self._subject_index[fact.subject] = []
        self._subject_index[fact.subject].append(fact.id)
        
        logger.info(f"📝 Факт добавлен: {fact.to_sentence()}")
        return fact
    
    def _save_fact(self, fact: Fact):
        """Сохраняет факт в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO facts 
            (id, subject, predicate, object, confidence, status, 
             source, source_id, created_at, updated_at, accessed_at,
             access_count, decay_rate, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fact.id,
            fact.subject,
            fact.predicate,
            fact.object,
            fact.confidence,
            fact.status.value,
            fact.source,
            fact.source_id,
            fact.created_at.isoformat(),
            fact.updated_at.isoformat(),
            fact.accessed_at.isoformat(),
            fact.access_count,
            fact.decay_rate,
            json.dumps(fact.metadata, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
        
        self._fact_cache[fact.id] = fact
    
    def find_exact(
        self, 
        subject: str, 
        predicate: str, 
        object: str
    ) -> Optional[Fact]:
        """Находит точное совпадение"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM facts 
            WHERE subject = ? AND predicate = ? AND object = ?
            LIMIT 1
        """, (subject.lower(), predicate.lower(), object.lower()))
        
        row = cursor.fetchone()
        conn.close()
        
        return self._row_to_fact(row) if row else None
    
    def find_by_subject(
        self, 
        subject: str,
        min_confidence: float = 0.3,
        limit: int = 20
    ) -> List[Fact]:
        """Находит все факты о субъекте"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM facts 
            WHERE subject = ? AND confidence >= ?
            ORDER BY confidence DESC, updated_at DESC
            LIMIT ?
        """, (subject.lower(), min_confidence, limit))
        
        facts = [self._row_to_fact(row) for row in cursor.fetchall()]
        conn.close()
        
        return facts
    
    def find_by_predicate(
        self,
        predicate: str,
        min_confidence: float = 0.3,
        limit: int = 20
    ) -> List[Fact]:
        """Находит все факты с данным предикатом"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM facts 
            WHERE predicate = ? AND confidence >= ?
            ORDER BY confidence DESC
            LIMIT ?
        """, (predicate.lower(), min_confidence, limit))
        
        facts = [self._row_to_fact(row) for row in cursor.fetchall()]
        conn.close()
        
        return facts
    
    def search(
        self,
        query: str,
        min_confidence: float = 0.3,
        limit: int = 10
    ) -> List[Fact]:
        """Поиск фактов по тексту"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Поиск по совпадению в любом поле
        cursor.execute("""
            SELECT * FROM facts 
            WHERE (subject LIKE ? OR predicate LIKE ? OR object LIKE ?)
            AND confidence >= ?
            ORDER BY confidence DESC, updated_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", 
              min_confidence, limit))
        
        facts = [self._row_to_fact(row) for row in cursor.fetchall()]
        conn.close()
        
        # Обновляем accessed_at
        for fact in facts:
            fact.accessed_at = datetime.now()
            fact.access_count += 1
            self._save_fact(fact)
        
        return facts
    
    def get_related(
        self,
        subject: str,
        depth: int = 2,
        min_confidence: float = 0.3
    ) -> List[Fact]:
        """Получает связанные факты (графовый обход)"""
        visited = set()
        result = []
        
        def traverse(s: str, d: int):
            if d <= 0 or s in visited:
                return
            visited.add(s)
            
            facts = self.find_by_subject(s, min_confidence)
            for fact in facts:
                if fact.id not in [f.id for f in result]:
                    result.append(fact)
                    # Рекурсивно обходим через object
                    traverse(fact.object, d - 1)
        
        traverse(subject.lower(), depth)
        return result
    
    def update_confidence(
        self,
        fact_id: str,
        delta: float
    ) -> Optional[Fact]:
        """Обновляет confidence факта"""
        fact = self.get(fact_id)
        if not fact:
            return None
        
        fact.confidence = max(0.1, min(0.95, fact.confidence + delta))
        fact.updated_at = datetime.now()
        
        # Обновляем статус
        if fact.confidence >= 0.7:
            fact.status = FactStatus.SUPPORTED
        elif fact.confidence <= 0.3:
            fact.status = FactStatus.CONTRADICTED
        
        self._save_fact(fact)
        return fact
    
    def apply_decay(self, days: int = 7) -> int:
        """
        Применяет забывание (decay)
        
        Снижает confidence фактов, к которым давно не обращались
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Находим старые факты
        cursor.execute("""
            SELECT * FROM facts 
            WHERE accessed_at < ? AND confidence > 0.2
        """, (cutoff,))
        
        updated = 0
        for row in cursor.fetchall():
            fact = self._row_to_fact(row)
            
            # Снижаем confidence
            decay_amount = fact.decay_rate * 0.1
            fact.confidence = max(0.1, fact.confidence - decay_amount)
            
            # Если confidence упал слишком низко — obsolete
            if fact.confidence < 0.2:
                fact.status = FactStatus.OBSOLETE
            
            self._save_fact(fact)
            updated += 1
        
        conn.close()
        
        logger.info(f"📉 Decay применён к {updated} фактам")
        return updated
    
    def get(self, fact_id: str) -> Optional[Fact]:
        """Получает факт по ID"""
        if fact_id in self._fact_cache:
            return self._fact_cache[fact_id]
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM facts WHERE id = ?", (fact_id,))
        row = cursor.fetchone()
        conn.close()
        
        return self._row_to_fact(row) if row else None
    
    def _row_to_fact(self, row: sqlite3.Row) -> Fact:
        """Конвертирует строку БД в Fact"""
        return Fact(
            id=row['id'],
            subject=row['subject'],
            predicate=row['predicate'],
            object=row['object'],
            confidence=row['confidence'],
            status=FactStatus(row['status']),
            source=row['source'],
            source_id=row['source_id'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            accessed_at=datetime.fromisoformat(row['accessed_at']),
            access_count=row['access_count'],
            decay_rate=row['decay_rate'],
            metadata=json.loads(row['metadata'] or '{}')
        )
    
    def find_contradictions(self) -> List[Tuple[Fact, Fact]]:
        """Находит противоречивые факты"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Факты с одинаковыми subject + predicate, но разными object
        cursor.execute("""
            SELECT f1.*, f2.* FROM facts f1
            JOIN facts f2 ON f1.subject = f2.subject 
                AND f1.predicate = f2.predicate
                AND f1.object != f2.object
            WHERE f1.confidence > 0.3 AND f2.confidence > 0.3
        """)
        
        contradictions = []
        for row in cursor.fetchall():
            f1 = self._row_to_fact({
                k[3:]: v for k, v in dict(row).items() 
                if k.startswith('f1_')
            })
            f2 = self._row_to_fact({
                k[3:]: v for k, v in dict(row).items() 
                if k.startswith('f2_')
            })
            contradictions.append((f1, f2))
        
        conn.close()
        return contradictions
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика памяти фактов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM facts")
        total = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT status, COUNT(*) FROM facts GROUP BY status"
        )
        status_dist = dict(cursor.fetchall())
        
        cursor.execute("SELECT AVG(confidence) FROM facts")
        avg_conf = cursor.fetchone()[0] or 0
        
        cursor.execute(
            "SELECT COUNT(*) FROM facts WHERE confidence >= 0.7"
        )
        high_conf = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM facts WHERE confidence < 0.3"
        )
        low_conf = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT predicate, COUNT(*) as cnt FROM facts "
            "GROUP BY predicate ORDER BY cnt DESC LIMIT 5"
        )
        top_predicates = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_facts": total,
            "status_distribution": status_dist,
            "average_confidence": round(avg_conf, 3),
            "high_confidence_count": high_conf,
            "low_confidence_count": low_conf,
            "top_predicates": top_predicates
        }
    
    def clear(self):
        """Очищает память фактов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM facts")
        conn.commit()
        conn.close()
        
        self._fact_cache.clear()
        self._subject_index.clear()
        
        logger.info("🗑️ FactMemory очищена")


# Глобальный экземпляр
_fact_memory: Optional[FactMemory] = None


def get_fact_memory() -> FactMemory:
    """Возвращает глобальную память фактов"""
    global _fact_memory
    if _fact_memory is None:
        _fact_memory = FactMemory()
    return _fact_memory