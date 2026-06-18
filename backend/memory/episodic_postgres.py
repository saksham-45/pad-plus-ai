"""
🧠 EpisodicMemory PostgreSQL версия

Хранит эпизоды в PostgreSQL вместо SQLite.
Обеспечивает персистентность между деплоями Render.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import json
import logging
import uuid

logger = logging.getLogger("PAD+.episodic_pg")

# Проверяем доступность PostgreSQL
postgres_available = False
try:
    import psycopg2
    from psycopg2.extras import Json
    postgres_available = True
    logger.info("✅ PostgreSQL доступен для EpisodicMemory")
except Exception as e:
    logger.warning(f"⚠️ PostgreSQL недоступен для EpisodicMemory: {e}")
    psycopg2 = None
    Json = None


@dataclass
class Episode:
    """
    Эпизод — атомарная единица эпизодической памяти
    """
    id: str
    timestamp: datetime
    user_id: Optional[str] = None
    situation: str = ""
    participants: List[str] = field(default_factory=list)
    location: str = ""
    user_message: str = ""
    ai_response: str = ""
    intent: str = "unknown"
    topic: str = "общее"
    emotion_before: Dict[str, float] = field(default_factory=dict)
    emotion_after: Dict[str, float] = field(default_factory=dict)
    emotion_impact: float = 0.0
    entities: List[Dict[str, Any]] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    related_episodes: List[str] = field(default_factory=list)
    parent_episode: Optional[str] = None
    continuation_of: Optional[str] = None
    significance: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    duration_seconds: float = 0.0
    success: bool = True
    feedback: Optional[str] = None

    def to_dict(self) -> dict:
        """Преобразует эпизод в словарь"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "situation": self.situation,
            "participants": self.participants,
            "location": self.location,
            "user_message": self.user_message,
            "ai_response": self.ai_response,
            "intent": self.intent,
            "topic": self.topic,
            "emotion_before": self.emotion_before,
            "emotion_after": self.emotion_after,
            "emotion_impact": self.emotion_impact,
            "entities": self.entities,
            "concepts": self.concepts,
            "keywords": self.keywords,
            "related_episodes": self.related_episodes,
            "parent_episode": self.parent_episode,
            "continuation_of": self.continuation_of,
            "significance": self.significance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "feedback": self.feedback
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Episode':
        """Создаёт эпизод из словаря"""
        created_at = data.get("timestamp")
        if isinstance(created_at, str):
            timestamp = datetime.fromisoformat(created_at)
        else:
            timestamp = created_at
            
        last_accessed = data.get("last_accessed")
        if isinstance(last_accessed, str):
            last_accessed_dt = datetime.fromisoformat(last_accessed) if last_accessed else None
        else:
            last_accessed_dt = last_accessed

        return cls(
            id=data["id"],
            timestamp=timestamp,
            user_id=data.get("user_id"),
            situation=data.get("situation", ""),
            participants=data.get("participants", []),
            location=data.get("location", ""),
            user_message=data.get("user_message", ""),
            ai_response=data.get("ai_response", ""),
            intent=data.get("intent", "unknown"),
            topic=data.get("topic", "общее"),
            emotion_before=data.get("emotion_before", {}),
            emotion_after=data.get("emotion_after", {}),
            emotion_impact=data.get("emotion_impact", 0.0),
            entities=data.get("entities", []),
            concepts=data.get("concepts", []),
            keywords=data.get("keywords", []),
            related_episodes=data.get("related_episodes", []),
            parent_episode=data.get("parent_episode"),
            continuation_of=data.get("continuation_of"),
            significance=data.get("significance", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=last_accessed_dt,
            duration_seconds=data.get("duration_seconds", 0.0),
            success=data.get("success", True),
            feedback=data.get("feedback")
        )


class EpisodicMemory:
    """
    🧠 Эпизодическая память (PostgreSQL версия)
    
    Хранит структурированные воспоминания о конкретных событиях в PostgreSQL.
    """

    def __init__(self):
        self._conn = None
        self._ensure_tables()
        logger.info("✅ EpisodicMemory PostgreSQL инициализирована")

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
                    raise RuntimeError("Нет PostgreSQL подключения для EpisodicMemory")
        return self._conn

    def _ensure_tables(self):
        """Создаёт таблицы, если их нет"""
        conn = self._get_conn()
        conn.autocommit = True
        cur = conn.cursor()
        
        try:
            # Основная таблица эпизодов
            cur.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    user_id TEXT,
                    situation TEXT DEFAULT '',
                    participants JSONB DEFAULT '[]',
                    location TEXT DEFAULT '',
                    user_message TEXT NOT NULL,
                    ai_response TEXT,
                    intent TEXT DEFAULT 'unknown',
                    topic TEXT DEFAULT 'общее',
                    emotion_before JSONB DEFAULT '{}',
                    emotion_after JSONB DEFAULT '{}',
                    emotion_impact REAL DEFAULT 0.0,
                    entities JSONB DEFAULT '[]',
                    concepts JSONB DEFAULT '[]',
                    keywords JSONB DEFAULT '[]',
                    related_episodes JSONB DEFAULT '[]',
                    parent_episode TEXT,
                    continuation_of TEXT,
                    significance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMPTZ,
                    duration_seconds REAL DEFAULT 0.0,
                    success BOOLEAN DEFAULT TRUE,
                    feedback TEXT
                )
            """)

            # Индексы
            cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON episodes(timestamp DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_topic ON episodes(topic)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_significance ON episodes(significance DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_user_id ON episodes(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_intent ON episodes(intent)")

            # Связи между эпизодами
            cur.execute("""
                CREATE TABLE IF NOT EXISTS episode_relations (
                    id BIGSERIAL PRIMARY KEY,
                    episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
                    related_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
                    relation_type TEXT DEFAULT 'related',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_episode_relations_episode_id ON episode_relations(episode_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_episode_relations_related_id ON episode_relations(related_id)")

        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц EpisodicMemory: {e}")
            raise
        finally:
            cur.close()

    def add_episode(
        self,
        user_message: str,
        ai_response: str,
        intent: str = "unknown",
        topic: str = "общее",
        emotion_before: dict = None,
        emotion_after: dict = None,
        entities: List[dict] = None,
        concepts: List[str] = None,
        keywords: List[str] = None,
        significance: float = 0.5,
        duration_seconds: float = 0.0,
        success: bool = True,
        situation: str = "",
        participants: List[str] = None,
        location: str = "",
        continuation_of: str = None,
        user_id: Optional[str] = None
    ) -> Episode:
        """Добавляет новый эпизод в память"""
        episode_id = str(uuid.uuid4())[:12]
        now = datetime.now(timezone.utc)

        # Вычисляем эмоциональный импакт
        emotion_impact = 0.0
        if emotion_before and emotion_after:
            before_conf = emotion_before.get("уверенность", 0.5)
            after_conf = emotion_after.get("уверенность", 0.5)
            before_pleasure = emotion_before.get("удовольствие", 0.0)
            after_pleasure = emotion_after.get("удовольствие", 0.0)
            emotion_impact = ((after_conf - before_conf) + (after_pleasure - before_pleasure)) / 2

        episode = Episode(
            id=episode_id,
            timestamp=now,
            user_id=user_id,
            situation=situation,
            participants=participants or [],
            location=location,
            user_message=user_message,
            ai_response=ai_response,
            intent=intent,
            topic=topic,
            emotion_before=emotion_before or {},
            emotion_after=emotion_after or {},
            emotion_impact=emotion_impact,
            entities=entities or [],
            concepts=concepts or [],
            keywords=keywords or [],
            significance=significance,
            duration_seconds=duration_seconds,
            success=success,
            continuation_of=continuation_of
        )

        self._save_episode(episode)
        logger.info(f"📝 Эпизод добавлен: {episode_id} (тема: {topic}, значимость: {significance:.2f})")
        return episode

    def _save_episode(self, episode: Episode):
        """Сохраняет эпизод в PostgreSQL"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO episodes (
                id, timestamp, user_id, situation, participants, location,
                user_message, ai_response, intent, topic,
                emotion_before, emotion_after, emotion_impact,
                entities, concepts, keywords,
                related_episodes, parent_episode, continuation_of,
                significance, access_count, last_accessed,
                duration_seconds, success, feedback
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                timestamp = EXCLUDED.timestamp,
                user_id = EXCLUDED.user_id,
                situation = EXCLUDED.situation,
                participants = EXCLUDED.participants,
                location = EXCLUDED.location,
                user_message = EXCLUDED.user_message,
                ai_response = EXCLUDED.ai_response,
                intent = EXCLUDED.intent,
                topic = EXCLUDED.topic,
                emotion_before = EXCLUDED.emotion_before,
                emotion_after = EXCLUDED.emotion_after,
                emotion_impact = EXCLUDED.emotion_impact,
                entities = EXCLUDED.entities,
                concepts = EXCLUDED.concepts,
                keywords = EXCLUDED.keywords,
                related_episodes = EXCLUDED.related_episodes,
                parent_episode = EXCLUDED.parent_episode,
                continuation_of = EXCLUDED.continuation_of,
                significance = EXCLUDED.significance,
                access_count = EXCLUDED.access_count,
                last_accessed = EXCLUDED.last_accessed,
                duration_seconds = EXCLUDED.duration_seconds,
                success = EXCLUDED.success,
                feedback = EXCLUDED.feedback
        """, (
            episode.id,
            episode.timestamp,
            episode.user_id,
            episode.situation,
            Json(episode.participants),
            episode.location,
            episode.user_message,
            episode.ai_response,
            episode.intent,
            episode.topic,
            Json(episode.emotion_before),
            Json(episode.emotion_after),
            episode.emotion_impact,
            Json(episode.entities),
            Json(episode.concepts),
            Json(episode.keywords),
            Json(episode.related_episodes),
            episode.parent_episode,
            episode.continuation_of,
            episode.significance,
            episode.access_count,
            episode.last_accessed,
            episode.duration_seconds,
            episode.success,
            episode.feedback
        ))
        conn.commit()
        cur.close()

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Получает эпизод по ID"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM episodes WHERE id = %s", (episode_id,))
        row = cur.fetchone()
        cur.close()

        if row:
            return self._row_to_episode(row)
        return None

    def _row_to_episode(self, row) -> Episode:
        """Преобразует строку БД в Episode"""
        return Episode(
            id=row[0],
            timestamp=row[1],
            user_id=row[2],
            situation=row[3],
            participants=row[4] if isinstance(row[4], list) else [],
            location=row[5],
            user_message=row[6],
            ai_response=row[7],
            intent=row[8],
            topic=row[9],
            emotion_before=row[10] if isinstance(row[10], dict) else {},
            emotion_after=row[11] if isinstance(row[11], dict) else {},
            emotion_impact=row[12],
            entities=row[12] if isinstance(row[12], list) else [],
            concepts=row[14] if isinstance(row[14], list) else [],
            keywords=row[15] if isinstance(row[15], list) else [],
            related_episodes=row[16] if isinstance(row[16], list) else [],
            parent_episode=row[17],
            continuation_of=row[18],
            significance=row[19],
            access_count=row[20],
            last_accessed=row[21],
            duration_seconds=row[22],
            success=row[23],
            feedback=row[24]
        )

    def search_episodes(
        self,
        query: str = None,
        topic: str = None,
        intent: str = None,
        min_significance: float = 0.0,
        limit: int = 10,
        user_id: Optional[str] = None
    ) -> List[Episode]:
        """Поиск эпизодов по критериям"""
        conn = self._get_conn()
        cur = conn.cursor()

        conditions = []
        params = []

        if query:
            conditions.append("(user_message ILIKE %s OR ai_response ILIKE %s)")
            params.extend([f"%{query}%", f"%{query}%"])

        if topic:
            conditions.append("topic = %s")
            params.append(topic)

        if intent:
            conditions.append("intent = %s")
            params.append(intent)

        if min_significance > 0:
            conditions.append("significance >= %s")
            params.append(min_significance)

        if user_id:
            conditions.append("(user_id = %s OR user_id IS NULL)")
            params.append(user_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT * FROM episodes
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s
        """
        params.append(limit)

        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()

        episodes = [self._row_to_episode(row) for row in rows]

        # Обновляем access_count
        for ep in episodes:
            ep.access_count += 1
            ep.last_accessed = datetime.now(timezone.utc)
            self._save_episode(ep)

        return episodes

    def get_timeline(self, days: int = 7, limit: int = 50) -> List[Episode]:
        """Получает хронологию эпизодов за период"""
        from datetime import timedelta

        conn = self._get_conn()
        cur = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days))

        cur.execute("""
            SELECT * FROM episodes 
            WHERE timestamp >= %s
            ORDER BY timestamp ASC
            LIMIT %s
        """, (cutoff, limit))

        rows = cur.fetchall()
        cur.close()
        return [self._row_to_episode(row) for row in rows]

    def link_episodes(self, episode_id: str, related_id: str, relation_type: str = "related"):
        """Создаёт связь между эпизодами"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO episode_relations (episode_id, related_id, relation_type, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (episode_id, related_id, relation_type))

        # Обновляем related_episodes в обоих эпизодах
        for ep_id in [episode_id, related_id]:
            cur.execute("SELECT related_episodes FROM episodes WHERE id = %s", (ep_id,))
            row = cur.fetchone()
            if row:
                related = row[0] if isinstance(row[0], list) else []
                if ep_id == episode_id:
                    other_id = related_id
                else:
                    other_id = episode_id
                if other_id not in related:
                    related.append(other_id)
                    cur.execute("""
                        UPDATE episodes SET related_episodes = %s 
                        WHERE id = %s
                    """, (Json(related), ep_id))

        conn.commit()
        cur.close()
        logger.info(f"🔗 Эпизоды связаны: {episode_id} <-> {related_id}")

    def get_significant_episodes(self, min_significance: float = 0.7, limit: int = 20) -> List[Episode]:
        """Получает наиболее значимые эпизоды"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM episodes 
            WHERE significance >= %s
            ORDER BY significance DESC, timestamp DESC
            LIMIT %s
        """, (min_significance, limit))

        rows = cur.fetchall()
        cur.close()
        return [self._row_to_episode(row) for row in rows]

    def get_emotionally_charged(self, min_impact: float = 0.3, limit: int = 20) -> List[Episode]:
        """Получает эмоционально заряженные эпизоды"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM episodes 
            WHERE ABS(emotion_impact) >= %s
            ORDER BY ABS(emotion_impact) DESC
            LIMIT %s
        """, (min_impact, limit))

        rows = cur.fetchall()
        cur.close()
        return [self._row_to_episode(row) for row in rows]

    def get_stats(self) -> Dict[str, Any]:
        """Статистика эпизодической памяти"""
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM episodes")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT topic, COUNT(*) as cnt 
            FROM episodes 
            GROUP BY topic 
            ORDER BY cnt DESC
        """)
        by_topic = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("""
            SELECT intent, COUNT(*) as cnt 
            FROM episodes 
            GROUP BY intent 
            ORDER BY cnt DESC
        """)
        by_intent = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("SELECT AVG(significance) FROM episodes")
        avg_significance = cur.fetchone()[0] or 0.0

        cur.execute("SELECT AVG(ABS(emotion_impact)) FROM episodes")
        avg_emotion_impact = cur.fetchone()[0] or 0.0

        cur.execute("SELECT COUNT(*) FROM episode_relations")
        total_relations = cur.fetchone()[0]

        cur.execute("""
            SELECT id, access_count 
            FROM episodes 
            ORDER BY access_count DESC 
            LIMIT 5
        """)
        most_accessed = cur.fetchall()

        cur.close()

        return {
            "total_episodes": total,
            "total_relations": total_relations,
            "by_topic": by_topic,
            "by_intent": by_intent,
            "avg_significance": round(avg_significance, 3),
            "avg_emotion_impact": round(avg_emotion_impact, 3),
            "most_accessed": [
                {"id": row[0], "access_count": row[1]}
                for row in most_accessed
            ]
        }

    def clear(self):
        """Очищает эпизодическую память"""
        conn = self._get_conn()
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("DELETE FROM episodes")
        cur.execute("DELETE FROM episode_relations")
        conn.commit()
        cur.close()

        logger.info("🗑️ EpisodicMemory PostgreSQL очищена")

    def close(self):
        """Закрывает соединение"""
        if self._conn and not self._conn.closed:
            self._conn.close()


# Глобальный экземпляр
_episodic_memory: Optional[EpisodicMemory] = None


def get_episodic_memory() -> EpisodicMemory:
    """Возвращает глобальную эпизодическую память"""
    global _episodic_memory
    if _episodic_memory is None:
        _episodic_memory = EpisodicMemory()
    return _episodic_memory
