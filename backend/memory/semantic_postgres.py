"""
🧠 SemanticMemory PostgreSQL версия

Хранит семантические знания в PostgreSQL вместо SQLite.
Обеспечивает персистентность между деплоями Render.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import logging
import uuid

logger = logging.getLogger("PAD+.semantic_pg")

# Проверяем доступность PostgreSQL
postgres_available = False
try:
    import psycopg2
    from psycopg2.extras import Json
    postgres_available = True
    logger.info("✅ PostgreSQL доступен для SemanticMemory")
except Exception as e:
    logger.warning(f"⚠️ PostgreSQL недоступен для SemanticMemory: {e}")
    psycopg2 = None
    Json = None


class KnowledgeType(Enum):
    """Типы знаний"""
    DECLARATIVE = "declarative"      # Факты
    PROCEDURAL = "procedural"        # Навыки
    CONCEPTUAL = "conceptual"        # Концепции
    METACOGNITIVE = "metacognitive"  # О себе


@dataclass
class SemanticKnowledge:
    """Единица семантического знания"""
    id: str
    knowledge_type: KnowledgeType
    content: str
    summary: str = ""
    procedure_steps: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    success_rate: float = 0.5
    related_concepts: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    parent_knowledge: Optional[str] = None
    derived_from: List[str] = field(default_factory=list)
    confidence: float = 0.5
    source: str = "unknown"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    last_modified: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    domain: str = "general"

    def to_dict(self) -> dict:
        """Преобразует знание в словарь"""
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
        """Создаёт знание из словаря"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at_dt = datetime.fromisoformat(created_at)
        else:
            created_at_dt = created_at

        last_accessed = data.get("last_accessed")
        if isinstance(last_accessed, str):
            last_accessed_dt = datetime.fromisoformat(last_accessed) if last_accessed else None
        else:
            last_accessed_dt = last_accessed

        last_modified = data.get("last_modified")
        if isinstance(last_modified, str):
            last_modified_dt = datetime.fromisoformat(last_modified) if last_modified else None
        else:
            last_modified_dt = last_modified

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
            created_at=created_at_dt,
            last_accessed=last_accessed_dt,
            access_count=data.get("access_count", 0),
            last_modified=last_modified_dt,
            tags=data.get("tags", []),
            domain=data.get("domain", "general")
        )


class SemanticMemory:
    """
    🧠 Семантическая память (PostgreSQL версия)
    
    Хранит типизированные знания в PostgreSQL.
    """

    def __init__(self):
        self._conn = None
        self._ensure_tables()
        logger.info("✅ SemanticMemory PostgreSQL инициализирована")

    def _get_conn(self):
        """Получает соединение с PostgreSQL"""
        from core.config_manager import get_database_url
        if self._conn is None or self._conn.closed:
            db_url = get_database_url()
            if db_url and db_url.startswith("postgresql"):
                self._conn = psycopg2.connect(db_url)
            else:
                env_url = os.environ.get("DATABASE_URL")
                if env_url and env_url.startswith("postgresql"):
                    self._conn = psycopg2.connect(env_url)
                else:
                    raise RuntimeError("Нет PostgreSQL подключения для SemanticMemory")
        return self._conn

    def _ensure_tables(self):
        """Создаёт таблицы, если их нет"""
        conn = self._get_conn()
        conn.autocommit = True
        cur = conn.cursor()

        try:
            # Основная таблица знаний
            cur.execute("""
                CREATE TABLE IF NOT EXISTS semantic_knowledge (
                    id TEXT PRIMARY KEY,
                    knowledge_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT DEFAULT '',
                    procedure_steps JSONB DEFAULT '[]',
                    triggers JSONB DEFAULT '[]',
                    success_rate REAL DEFAULT 0.5,
                    related_concepts JSONB DEFAULT '[]',
                    examples JSONB DEFAULT '[]',
                    parent_knowledge TEXT,
                    derived_from JSONB DEFAULT '[]',
                    confidence REAL DEFAULT 0.5,
                    source TEXT DEFAULT 'unknown',
                    created_at TIMESTAMPTZ NOT NULL,
                    last_accessed TIMESTAMPTZ,
                    access_count INTEGER DEFAULT 0,
                    last_modified TIMESTAMPTZ,
                    tags JSONB DEFAULT '[]',
                    domain TEXT DEFAULT 'general'
                )
            """)

            # Индексы
            cur.execute("CREATE INDEX IF NOT EXISTS idx_semantic_type ON semantic_knowledge(knowledge_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_semantic_domain ON semantic_knowledge(domain)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_semantic_confidence ON semantic_knowledge(confidence DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_semantic_created ON semantic_knowledge(created_at DESC)")

            # Таблица применений процедур
            cur.execute("""
                CREATE TABLE IF NOT EXISTS procedure_applications (
                    id BIGSERIAL PRIMARY KEY,
                    procedure_id TEXT NOT NULL REFERENCES semantic_knowledge(id) ON DELETE CASCADE,
                    context TEXT NOT NULL,
                    success BOOLEAN DEFAULT TRUE,
                    applied_at TIMESTAMPTZ DEFAULT NOW(),
                    feedback TEXT
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_procedure_applications_procedure_id ON procedure_applications(procedure_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_procedure_applications_applied_at ON procedure_applications(applied_at)")

        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц SemanticMemory: {e}")
            raise
        finally:
            cur.close()

    def add_knowledge(
        self,
        content: str,
        knowledge_type: KnowledgeType,
        summary: str = "",
        procedure_steps: List[str] = None,
        triggers: List[str] = None,
        related_concepts: List[str] = None,
        examples: List[str] = None,
        parent_knowledge: str = None,
        confidence: float = 0.5,
        source: str = "unknown",
        domain: str = "general",
        tags: List[str] = None
    ) -> SemanticKnowledge:
        """Добавляет новое знание"""
        knowledge_id = str(uuid.uuid4())[:12]
        now = datetime.now(timezone.utc)

        knowledge = SemanticKnowledge(
            id=knowledge_id,
            knowledge_type=knowledge_type,
            content=content,
            summary=summary,
            procedure_steps=procedure_steps or [],
            triggers=triggers or [],
            related_concepts=related_concepts or [],
            examples=examples or [],
            parent_knowledge=parent_knowledge,
            confidence=confidence,
            source=source,
            domain=domain,
            tags=tags or [],
            created_at=now
        )

        self._save_knowledge(knowledge)
        logger.info(f"📝 Знание добавлено: {knowledge_id} ({knowledge_type.value})")
        return knowledge

    def _save_knowledge(self, knowledge: SemanticKnowledge):
        """Сохраняет знание в PostgreSQL"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO semantic_knowledge (
                id, knowledge_type, content, summary, procedure_steps, triggers,
                success_rate, related_concepts, examples, parent_knowledge,
                derived_from, confidence, source, created_at, last_accessed,
                access_count, last_modified, tags, domain
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                knowledge_type = EXCLUDED.knowledge_type,
                content = EXCLUDED.content,
                summary = EXCLUDED.summary,
                procedure_steps = EXCLUDED.procedure_steps,
                triggers = EXCLUDED.triggers,
                success_rate = EXCLUDED.success_rate,
                related_concepts = EXCLUDED.related_concepts,
                examples = EXCLUDED.examples,
                parent_knowledge = EXCLUDED.parent_knowledge,
                derived_from = EXCLUDED.derived_from,
                confidence = EXCLUDED.confidence,
                source = EXCLUDED.source,
                created_at = EXCLUDED.created_at,
                last_accessed = EXCLUDED.last_accessed,
                access_count = EXCLUDED.access_count,
                last_modified = EXCLUDED.last_modified,
                tags = EXCLUDED.tags,
                domain = EXCLUDED.domain
        """, (
            knowledge.id,
            knowledge.knowledge_type.value,
            knowledge.content,
            knowledge.summary,
            Json(knowledge.procedure_steps),
            Json(knowledge.triggers),
            knowledge.success_rate,
            Json(knowledge.related_concepts),
            Json(knowledge.examples),
            knowledge.parent_knowledge,
            Json(knowledge.derived_from),
            knowledge.confidence,
            knowledge.source,
            knowledge.created_at,
            knowledge.last_accessed,
            knowledge.access_count,
            knowledge.last_modified,
            Json(knowledge.tags),
            knowledge.domain
        ))
        conn.commit()
        cur.close()

    def get_knowledge(self, knowledge_id: str) -> Optional[SemanticKnowledge]:
        """Получает знание по ID"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM semantic_knowledge WHERE id = %s", (knowledge_id,))
        row = cur.fetchone()
        cur.close()

        if row:
            return self._row_to_knowledge(row)
        return None

    def _row_to_knowledge(self, row) -> SemanticKnowledge:
        """Преобразует строку БД в SemanticKnowledge"""
        return SemanticKnowledge(
            id=row[0],
            knowledge_type=KnowledgeType(row[1]),
            content=row[2],
            summary=row[3],
            procedure_steps=row[4] if isinstance(row[4], list) else [],
            triggers=row[5] if isinstance(row[5], list) else [],
            success_rate=row[6],
            related_concepts=row[7] if isinstance(row[7], list) else [],
            examples=row[8] if isinstance(row[8], list) else [],
            parent_knowledge=row[9],
            derived_from=row[10] if isinstance(row[10], list) else [],
            confidence=row[11],
            source=row[12],
            created_at=row[13],
            last_accessed=row[14],
            access_count=row[15],
            last_modified=row[16],
            tags=row[17] if isinstance(row[17], list) else [],
            domain=row[18]
        )

    def search_knowledge(
        self,
        query: str = None,
        knowledge_type: str = None,
        domain: str = None,
        min_confidence: float = 0.0,
        limit: int = 10
    ) -> List[SemanticKnowledge]:
        """Поиск знаний по критериям"""
        conn = self._get_conn()
        cur = conn.cursor()

        conditions = []
        params = []

        if query:
            conditions.append("(content ILIKE %s OR summary ILIKE %s)")
            params.extend([f"%{query}%", f"%{query}%"])

        if knowledge_type:
            conditions.append("knowledge_type = %s")
            params.append(knowledge_type)

        if domain:
            conditions.append("domain = %s")
            params.append(domain)

        if min_confidence > 0:
            conditions.append("confidence >= %s")
            params.append(min_confidence)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT * FROM semantic_knowledge
            WHERE {where_clause}
            ORDER BY confidence DESC, created_at DESC
            LIMIT %s
        """
        params.append(limit)

        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()

        knowledge_list = [self._row_to_knowledge(row) for row in rows]

        # Обновляем access_count
        for kn in knowledge_list:
            kn.access_count += 1
            kn.last_accessed = datetime.now(timezone.utc)
            self._save_knowledge(kn)

        return knowledge_list

    def get_by_type(self, knowledge_type: str, limit: int = 20) -> List[SemanticKnowledge]:
        """Получает знания по типу"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM semantic_knowledge 
            WHERE knowledge_type = %s
            ORDER BY confidence DESC, created_at DESC
            LIMIT %s
        """, (knowledge_type, limit))

        rows = cur.fetchall()
        cur.close()
        return [self._row_to_knowledge(row) for row in rows]

    def get_high_confidence(self, min_confidence: float = 0.8, limit: int = 20) -> List[SemanticKnowledge]:
        """Получает высоконадёжные знания"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM semantic_knowledge 
            WHERE confidence >= %s
            ORDER BY confidence DESC
            LIMIT %s
        """, (min_confidence, limit))

        rows = cur.fetchall()
        cur.close()
        return [self._row_to_knowledge(row) for row in rows]

    def get_recent(self, days: int = 7, limit: int = 20) -> List[SemanticKnowledge]:
        """Получает недавно добавленные знания"""
        from datetime import timedelta

        conn = self._get_conn()
        cur = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days))

        cur.execute("""
            SELECT * FROM semantic_knowledge 
            WHERE created_at >= %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (cutoff, limit))

        rows = cur.fetchall()
        cur.close()
        return [self._row_to_knowledge(row) for row in rows]

    def get_frequently_accessed(self, min_accesses: int = 3, limit: int = 20) -> List[SemanticKnowledge]:
        """Получает часто используемые знания"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM semantic_knowledge 
            WHERE access_count >= %s
            ORDER BY access_count DESC
            LIMIT %s
        """, (min_accesses, limit))

        rows = cur.fetchall()
        cur.close()
        return [self._row_to_knowledge(row) for row in rows]

    def record_procedure_application(
        self,
        procedure_id: str,
        context: str,
        success: bool = True,
        feedback: str = None
    ):
        """Записывает применение процедуры"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO procedure_applications 
            (procedure_id, context, success, applied_at, feedback)
            VALUES (%s, %s, %s, NOW(), %s)
        """, (procedure_id, context, success, feedback))

        # Обновляем success_rate процедуры
        cur.execute("""
            SELECT AVG(success::int) 
            FROM procedure_applications 
            WHERE procedure_id = %s
        """, (procedure_id,))
        avg_success = cur.fetchone()[0] or 0.5

        cur.execute("""
            UPDATE semantic_knowledge 
            SET success_rate = %s
            WHERE id = %s
        """, (avg_success, procedure_id))

        conn.commit()
        cur.close()

        logger.info(f"🔧 Процедура применена: {procedure_id} ({'успешно' if success else 'неудачно'})")

    def get_procedure_applications(self, procedure_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает историю применений процедуры"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM procedure_applications 
            WHERE procedure_id = %s
            ORDER BY applied_at DESC
            LIMIT %s
        """, (procedure_id, limit))

        rows = cur.fetchall()
        cur.close()

        return [
            {
                "id": row[0],
                "procedure_id": row[1],
                "context": row[2],
                "success": row[3],
                "applied_at": row[4],
                "feedback": row[5]
            }
            for row in rows
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Статистика семантической памяти"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM semantic_knowledge")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT knowledge_type, COUNT(*) as cnt 
            FROM semantic_knowledge 
            GROUP BY knowledge_type 
            ORDER BY cnt DESC
        """)
        by_type = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("""
            SELECT domain, COUNT(*) as cnt 
            FROM semantic_knowledge 
            GROUP BY domain 
            ORDER BY cnt DESC
        """)
        by_domain = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("SELECT AVG(confidence) FROM semantic_knowledge")
        avg_confidence = cur.fetchone()[0] or 0.0

        cur.execute("SELECT COUNT(*) FROM procedure_applications")
        total_applications = cur.fetchone()[0]

        cur.execute("""
            SELECT id, access_count 
            FROM semantic_knowledge 
            ORDER BY access_count DESC 
            LIMIT 5
        """)
        most_accessed = cur.fetchall()

        cur.close()

        return {
            "total_knowledge": total,
            "total_applications": total_applications,
            "by_type": by_type,
            "by_domain": by_domain,
            "avg_confidence": round(avg_confidence, 3),
            "most_accessed": [
                {"id": row[0], "access_count": row[1]}
                for row in most_accessed
            ]
        }

    def clear(self):
        """Очищает семантическую память"""
        conn = self._get_conn()
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("DELETE FROM semantic_knowledge")
        cur.execute("DELETE FROM procedure_applications")
        conn.commit()
        cur.close()

        logger.info("🗑️ SemanticMemory PostgreSQL очищена")

    def close(self):
        """Закрывает соединение"""
        if self._conn and not self._conn.closed:
            self._conn.close()


# Глобальный экземпляр
_semantic_memory: Optional[SemanticMemory] = None


def get_semantic_memory() -> SemanticMemory:
    """Возвращает глобальную семантическую память"""
    global _semantic_memory
    if _semantic_memory is None:
        _semantic_memory = SemanticMemory()
    return _semantic_memory
