"""
🧠 Семантическая память — Semantic Memory

Типизированное хранение знаний с разделением на:
- Декларативные (факты)
- Процедурные (навыки)
- Концептуальные (понятия)
- Метакогнитивные (о себе)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import os
import sqlite3
import logging

logger = logging.getLogger("PAD+.semantic")


class KnowledgeType(Enum):
    """Типы знаний"""
    DECLARATIVE = "declarative"      # Факты (Париж — столица Франции)
    PROCEDURAL = "procedural"        # Навыки (как решать уравнения)
    CONCEPTUAL = "conceptual"        # Концепции (что такое демократия)
    METACOGNITIVE = "metacognitive"  # О себе (я хорошо объясняю)


@dataclass
class SemanticKnowledge:
    """
    Единица семантического знания
    """
    
    # Идентификация
    id: str
    knowledge_type: KnowledgeType
    
    # Содержимое
    content: str                     # Основное содержание
    summary: str = ""                # Краткое описание
    
    # Для процедурных знаний
    procedure_steps: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)  # Когда применять
    success_rate: float = 0.5        # % успешного применения
    
    # Для концептуальных знаний
    related_concepts: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    
    # Связи
    parent_knowledge: Optional[str] = None
    derived_from: List[str] = field(default_factory=list)
    
    # Метаданные
    confidence: float = 0.5
    source: str = "unknown"          # user, self_learned, system, inference
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    last_modified: Optional[datetime] = None
    
    # Теги для поиска
    tags: List[str] = field(default_factory=list)
    domain: str = "general"          # Область знания
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            "id": self.id,
            "knowledge_type": self.knowledge_type.value,
            "content": self.content,
            "summary": self.summary,
            "procedure_steps": self.procedure_steps,
            "triggers": self.triggers,
            "success_rate": self.success_rate,
            "related_concepts": self.related_concepts,
            "examples": self.examples,
            "parent_knowledge": self.parent_knowledge,
            "derived_from": self.derived_from,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "tags": self.tags,
            "domain": self.domain
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SemanticKnowledge':
        """Создаёт из словаря"""
        return cls(
            id=data["id"],
            knowledge_type=KnowledgeType(data["knowledge_type"]),
            content=data["content"],
            summary=data.get("summary", ""),
            procedure_steps=data.get("procedure_steps", []),
            triggers=data.get("triggers", []),
            success_rate=data.get("success_rate", 0.5),
            related_concepts=data.get("related_concepts", []),
            examples=data.get("examples", []),
            parent_knowledge=data.get("parent_knowledge"),
            derived_from=data.get("derived_from", []),
            confidence=data.get("confidence", 0.5),
            source=data.get("source", "unknown"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            access_count=data.get("access_count", 0),
            last_modified=datetime.fromisoformat(data["last_modified"]) if data.get("last_modified") else None,
            tags=data.get("tags", []),
            domain=data.get("domain", "general")
        )


class SemanticMemory:
    """
    🧠 Семантическая память
    
    Типизированное хранение знаний с разделением на категории.
    Поддерживает процедурные знания (навыки) и их применение.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "semantic.db"
            )
        self.db_path = db_path
        self._ensure_tables()
        
        # Кэш процедурных знаний для быстрого доступа
        self._procedures_cache: Dict[str, SemanticKnowledge] = {}
        self._load_procedures_cache()
        
        logger.info(f"✅ Семантическая память инициализирована: {db_path}")
    
    def _ensure_tables(self):
        """Создаёт таблицы БД"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Основная таблица знаний
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_knowledge (
                id TEXT PRIMARY KEY,
                knowledge_type TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT DEFAULT '',
                procedure_steps TEXT DEFAULT '[]',
                triggers TEXT DEFAULT '[]',
                success_rate REAL DEFAULT 0.5,
                related_concepts TEXT DEFAULT '[]',
                examples TEXT DEFAULT '[]',
                parent_knowledge TEXT,
                derived_from TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.5,
                source TEXT DEFAULT 'unknown',
                created_at TEXT NOT NULL,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                last_modified TEXT,
                tags TEXT DEFAULT '[]',
                domain TEXT DEFAULT 'general'
            )
        """)
        
        # Индексы
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_type 
            ON semantic_knowledge(knowledge_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_domain 
            ON semantic_knowledge(domain)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_confidence 
            ON semantic_knowledge(confidence DESC)
        """)
        
        # Таблица применений процедур
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedure_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_id TEXT NOT NULL,
                context TEXT NOT NULL,
                success INTEGER DEFAULT 1,
                applied_at TEXT NOT NULL,
                feedback TEXT,
                FOREIGN KEY (procedure_id) REFERENCES semantic_knowledge(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_procedures_cache(self):
        """Загружает процедурные знания в кэш"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM semantic_knowledge 
            WHERE knowledge_type = 'procedural'
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            knowledge = self._row_to_knowledge(row)
            self._procedures_cache[knowledge.id] = knowledge
    
    def _row_to_knowledge(self, row: sqlite3.Row) -> SemanticKnowledge:
        """Преобразует строку БД в SemanticKnowledge"""
        return SemanticKnowledge(
            id=row["id"],
            knowledge_type=KnowledgeType(row["knowledge_type"]),
            content=row["content"],
            summary=row["summary"],
            procedure_steps=json.loads(row["procedure_steps"]),
            triggers=json.loads(row["triggers"]),
            success_rate=row["success_rate"],
            related_concepts=json.loads(row["related_concepts"]),
            examples=json.loads(row["examples"]),
            parent_knowledge=row["parent_knowledge"],
            derived_from=json.loads(row["derived_from"]),
            confidence=row["confidence"],
            source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
            access_count=row["access_count"],
            last_modified=datetime.fromisoformat(row["last_modified"]) if row["last_modified"] else None,
            tags=json.loads(row["tags"]),
            domain=row["domain"]
        )
    
    def add_knowledge(
        self,
        content: str,
        knowledge_type: KnowledgeType = KnowledgeType.DECLARATIVE,
        summary: str = "",
        confidence: float = 0.5,
        source: str = "user",
        tags: List[str] = None,
        domain: str = "general",
        procedure_steps: List[str] = None,
        triggers: List[str] = None,
        related_concepts: List[str] = None,
        examples: List[str] = None,
        parent_knowledge: str = None
    ) -> SemanticKnowledge:
        """
        Добавляет новое знание в память
        """
        import uuid
        
        knowledge_id = str(uuid.uuid4())[:12]
        now = datetime.now()
        
        knowledge = SemanticKnowledge(
            id=knowledge_id,
            knowledge_type=knowledge_type,
            content=content,
            summary=summary,
            confidence=confidence,
            source=source,
            created_at=now,
            tags=tags or [],
            domain=domain,
            procedure_steps=procedure_steps or [],
            triggers=triggers or [],
            related_concepts=related_concepts or [],
            examples=examples or [],
            parent_knowledge=parent_knowledge
        )
        
        self._save_knowledge(knowledge)
        
        # Обновляем кэш процедур
        if knowledge_type == KnowledgeType.PROCEDURAL:
            self._procedures_cache[knowledge_id] = knowledge
        
        logger.info(f"📚 Знание добавлено: {knowledge_id} ({knowledge_type.value}, domain: {domain})")
        
        return knowledge
    
    def _save_knowledge(self, knowledge: SemanticKnowledge):
        """Сохраняет знание в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO semantic_knowledge (
                id, knowledge_type, content, summary,
                procedure_steps, triggers, success_rate,
                related_concepts, examples,
                parent_knowledge, derived_from,
                confidence, source, created_at, last_accessed,
                access_count, last_modified, tags, domain
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            knowledge.id,
            knowledge.knowledge_type.value,
            knowledge.content,
            knowledge.summary,
            json.dumps(knowledge.procedure_steps),
            json.dumps(knowledge.triggers),
            knowledge.success_rate,
            json.dumps(knowledge.related_concepts),
            json.dumps(knowledge.examples),
            knowledge.parent_knowledge,
            json.dumps(knowledge.derived_from),
            knowledge.confidence,
            knowledge.source,
            knowledge.created_at.isoformat(),
            knowledge.last_accessed.isoformat() if knowledge.last_accessed else None,
            knowledge.access_count,
            knowledge.last_modified.isoformat() if knowledge.last_modified else None,
            json.dumps(knowledge.tags),
            knowledge.domain
        ))
        
        conn.commit()
        conn.close()
    
    def get_knowledge(self, knowledge_id: str) -> Optional[SemanticKnowledge]:
        """Получает знание по ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM semantic_knowledge WHERE id = ?", (knowledge_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_knowledge(row)
        return None
    
    def search_knowledge(
        self,
        query: str = None,
        knowledge_type: KnowledgeType = None,
        domain: str = None,
        min_confidence: float = 0.0,
        tags: List[str] = None,
        limit: int = 10
    ) -> List[SemanticKnowledge]:
        """
        Поиск знаний по критериям
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if query:
            conditions.append("(content LIKE ? OR summary LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if knowledge_type:
            conditions.append("knowledge_type = ?")
            params.append(knowledge_type.value)
        
        if domain:
            conditions.append("domain = ?")
            params.append(domain)
        
        if min_confidence > 0:
            conditions.append("confidence >= ?")
            params.append(min_confidence)
        
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT * FROM semantic_knowledge 
            WHERE {where_clause}
            ORDER BY confidence DESC, created_at DESC
            LIMIT ?
        """
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        results = [self._row_to_knowledge(row) for row in rows]
        
        # Обновляем access_count
        for k in results:
            k.access_count += 1
            k.last_accessed = datetime.now()
            self._save_knowledge(k)
        
        return results
    
    # === Процедурные знания ===
    
    def learn_procedure(
        self,
        name: str,
        steps: List[str],
        triggers: List[str],
        domain: str = "general",
        confidence: float = 0.5
    ) -> SemanticKnowledge:
        """
        Выучить новую процедуру (навык)
        """
        return self.add_knowledge(
            content=name,
            knowledge_type=KnowledgeType.PROCEDURAL,
            summary=f"Процедура: {name}",
            procedure_steps=steps,
            triggers=triggers,
            domain=domain,
            confidence=confidence,
            source="learned"
        )
    
    def find_applicable_procedure(self, context: str) -> Optional[SemanticKnowledge]:
        """
        Находит процедуру, применимую к контексту
        """
        context_lower = context.lower()
        
        best_match = None
        best_score = 0
        
        for proc in self._procedures_cache.values():
            for trigger in proc.triggers:
                if trigger.lower() in context_lower:
                    # Оцениваем качество матча
                    score = proc.success_rate * proc.confidence
                    if score > best_score:
                        best_score = score
                        best_match = proc
        
        return best_match
    
    def apply_procedure(
        self,
        procedure_id: str,
        context: str,
        success: bool = True,
        feedback: str = None
    ) -> Dict[str, Any]:
        """
        Применяет процедуру и записывает результат
        """
        procedure = self.get_knowledge(procedure_id)
        
        if not procedure or procedure.knowledge_type != KnowledgeType.PROCEDURAL:
            return {"error": "Procedure not found"}
        
        # Записываем применение
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO procedure_applications 
            (procedure_id, context, success, applied_at, feedback)
            VALUES (?, ?, ?, ?, ?)
        """, (
            procedure_id,
            context[:500],  # Ограничиваем длину контекста
            1 if success else 0,
            datetime.now().isoformat(),
            feedback
        ))
        
        # Обновляем success_rate
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM procedure_applications
            WHERE procedure_id = ?
        """, (procedure_id,))
        
        row = cursor.fetchone()
        total = row[0]
        successful = row[1]
        
        new_success_rate = successful / total if total > 0 else 0.5
        
        cursor.execute("""
            UPDATE semantic_knowledge 
            SET success_rate = ?, last_accessed = ?, access_count = access_count + 1
            WHERE id = ?
        """, (new_success_rate, datetime.now().isoformat(), procedure_id))
        
        conn.commit()
        conn.close()
        
        # Обновляем кэш
        procedure.success_rate = new_success_rate
        procedure.access_count += 1
        procedure.last_accessed = datetime.now()
        self._procedures_cache[procedure_id] = procedure
        
        return {
            "procedure_id": procedure_id,
            "steps": procedure.procedure_steps,
            "success_rate": new_success_rate,
            "recorded": True
        }
    
    def improve_procedure(
        self,
        procedure_id: str,
        new_steps: List[str] = None,
        new_triggers: List[str] = None
    ) -> Optional[SemanticKnowledge]:
        """
        Улучшает процедуру на основе опыта
        """
        procedure = self.get_knowledge(procedure_id)
        
        if not procedure:
            return None
        
        if new_steps:
            procedure.procedure_steps = new_steps
        if new_triggers:
            procedure.triggers = list(set(procedure.triggers + new_triggers))
        
        procedure.last_modified = datetime.now()
        
        self._save_knowledge(procedure)
        self._procedures_cache[procedure_id] = procedure
        
        logger.info(f"🔧 Процедура улучшена: {procedure_id}")
        
        return procedure
    
    # === Концептуальные знания ===
    
    def add_concept(
        self,
        name: str,
        definition: str,
        examples: List[str] = None,
        related_concepts: List[str] = None,
        domain: str = "general"
    ) -> SemanticKnowledge:
        """
        Добавляет концептуальное знание
        """
        return self.add_knowledge(
            content=definition,
            knowledge_type=KnowledgeType.CONCEPTUAL,
            summary=f"Концепция: {name}",
            examples=examples,
            related_concepts=related_concepts,
            domain=domain,
            tags=[name]
        )
    
    # === Метакогнитивные знания ===
    
    def add_self_knowledge(
        self,
        content: str,
        confidence: float = 0.5
    ) -> SemanticKnowledge:
        """
        Добавляет знание о себе
        """
        return self.add_knowledge(
            content=content,
            knowledge_type=KnowledgeType.METACOGNITIVE,
            source="self_reflection",
            confidence=confidence
        )
    
    def get_self_knowledge(self) -> List[SemanticKnowledge]:
        """
        Получает все знания о себе
        """
        return self.search_knowledge(
            knowledge_type=KnowledgeType.METACOGNITIVE,
            limit=50
        )
    
    # === Статистика ===
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Статистика семантической памяти
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общее количество
        cursor.execute("SELECT COUNT(*) FROM semantic_knowledge")
        total = cursor.fetchone()[0]
        
        # По типам
        cursor.execute("""
            SELECT knowledge_type, COUNT(*) as cnt 
            FROM semantic_knowledge 
            GROUP BY knowledge_type
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        # По доменам
        cursor.execute("""
            SELECT domain, COUNT(*) as cnt 
            FROM semantic_knowledge 
            GROUP BY domain 
            ORDER BY cnt DESC
            LIMIT 10
        """)
        by_domain = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Средняя уверенность
        cursor.execute("SELECT AVG(confidence) FROM semantic_knowledge")
        avg_confidence = cursor.fetchone()[0] or 0.0
        
        # Процедуры
        cursor.execute("SELECT COUNT(*) FROM procedure_applications")
        total_applications = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT AVG(success_rate) FROM semantic_knowledge 
            WHERE knowledge_type = 'procedural'
        """)
        avg_procedure_success = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            "total_knowledge": total,
            "by_type": by_type,
            "by_domain": by_domain,
            "avg_confidence": round(avg_confidence, 3),
            "procedures": {
                "count": by_type.get("procedural", 0),
                "total_applications": total_applications,
                "avg_success_rate": round(avg_procedure_success, 3)
            }
        }
    
    def clear(self):
        """Очищает семантическую память"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM semantic_knowledge")
        cursor.execute("DELETE FROM procedure_applications")
        
        conn.commit()
        conn.close()
        
        self._procedures_cache.clear()
        
        logger.info("🗑️ Семантическая память очищена")


# Глобальный экземпляр
_semantic_memory: Optional[SemanticMemory] = None


def get_semantic_memory() -> SemanticMemory:
    """Возвращает глобальную семантическую память"""
    global _semantic_memory
    if _semantic_memory is None:
        _semantic_memory = SemanticMemory()
    return _semantic_memory