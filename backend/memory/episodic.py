"""
🧠 Эпизодическая память — Episodic Memory

Структурированное хранение диалогов с контекстом ситуации.
Позволяет "вспоминать" конкретные события и их обстоятельства.

Особенности:
- Контекст ситуации (где, когда, кто)
- Эмоциональный след эпизода
- Связи между эпизодами
- Важность для консолидации
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import os
import sqlite3
import logging

logger = logging.getLogger("PAD+.episodic")


@dataclass
class Episode:
    """
    Эпизод — атомарная единица эпизодической памяти
    
    Хранит не только факт диалога, но и контекст ситуации
    """
    
    # Идентификация
    id: str
    timestamp: datetime
    
    # === ФАЗА 3: Персонализация ===
    user_id: Optional[str] = None    # ID владельца эпизода (None для общих)

    # Контекст ситуации
    situation: str = ""              # Описание ситуации
    participants: List[str] = field(default_factory=list)  # Участники
    location: str = ""               # Контекст (работа, учёба, etc.)
    
    # Содержимое диалога
    user_message: str = ""
    ai_response: str = ""
    intent: str = "unknown"          # Намерение пользователя
    topic: str = "общее"             # Тема диалога
    
    # Эмоциональный контекст
    emotion_before: Dict[str, float] = field(default_factory=dict)
    emotion_after: Dict[str, float] = field(default_factory=dict)
    emotion_impact: float = 0.0      # Влияние на эмоции (-1 до +1)
    
    # Метки для поиска
    entities: List[Dict[str, Any]] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # Связи с другими эпизодами
    related_episodes: List[str] = field(default_factory=list)
    parent_episode: Optional[str] = None
    continuation_of: Optional[str] = None  # Продолжение предыдущего эпизода
    
    # Важность (для консолидации)
    significance: float = 0.5        # 0.0 - 1.0
    access_count: int = 0            # Сколько раз использовался
    last_accessed: Optional[datetime] = None
    
    # Метаданные
    duration_seconds: float = 0.0    # Длительность обработки
    success: bool = True
    feedback: Optional[str] = None   # Обратная связь пользователя
    
    def to_dict(self) -> dict:
        """Преобразует эпизод в словарь"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,  # === ФАЗА 3: Персонализация ===
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
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data.get("user_id"),  # === ФАЗА 3: Персонализация ===
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
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            duration_seconds=data.get("duration_seconds", 0.0),
            success=data.get("success", True),
            feedback=data.get("feedback")
        )


class EpisodicMemory:
    """
    🧠 Эпизодическая память
    
    Хранит структурированные воспоминания о конкретных событиях.
    В отличие от RAG, хранит контекст ситуации, а не только текст.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "episodic.db"
            )
        self.db_path = db_path
        self._ensure_tables()
        
        # Кэш недавних эпизодов
        self._recent_episodes: List[Episode] = []
        self._max_recent = 50
        
        logger.info(f"✅ Эпизодическая память инициализирована: {db_path}")
    
    def _ensure_tables(self):
        """Создаёт таблицы БД"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Основная таблица эпизодов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                situation TEXT DEFAULT '',
                participants TEXT DEFAULT '[]',
                location TEXT DEFAULT '',
                user_message TEXT NOT NULL,
                ai_response TEXT,
                intent TEXT DEFAULT 'unknown',
                topic TEXT DEFAULT 'общее',
                emotion_before TEXT DEFAULT '{}',
                emotion_after TEXT DEFAULT '{}',
                emotion_impact REAL DEFAULT 0.0,
                entities TEXT DEFAULT '[]',
                concepts TEXT DEFAULT '[]',
                keywords TEXT DEFAULT '[]',
                related_episodes TEXT DEFAULT '[]',
                parent_episode TEXT,
                continuation_of TEXT,
                significance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                duration_seconds REAL DEFAULT 0.0,
                success INTEGER DEFAULT 1,
                feedback TEXT
            )
        """)
        
        # === ФАЗА 3: Добавляем user_id если нет ===
        cursor.execute("PRAGMA table_info(episodes)")
        columns = [row[1] for row in cursor.fetchall()]
        if "user_id" not in columns:
            print(f"🔄 Добавление колонки user_id в episodes...")
            cursor.execute("ALTER TABLE episodes ADD COLUMN user_id TEXT")

        # Индексы для поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodes_timestamp
            ON episodes(timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodes_topic
            ON episodes(topic)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodes_significance
            ON episodes(significance DESC)
        """)
        
        # === ФАЗА 3: Индекс для user_id ===
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodes_user_id
            ON episodes(user_id)
        """)
        
        # Таблица связей между эпизодами
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episode_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id TEXT NOT NULL,
                related_id TEXT NOT NULL,
                relation_type TEXT DEFAULT 'related',
                created_at TEXT NOT NULL,
                FOREIGN KEY (episode_id) REFERENCES episodes(id),
                FOREIGN KEY (related_id) REFERENCES episodes(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
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
        user_id: Optional[str] = None  # === ФАЗА 3: Персонализация ===
    ) -> Episode:
        """
        Добавляет новый эпизод в память
        
        Args:
            user_id: ID владельца эпизода (None для общих записей)
        """
        import uuid

        episode_id = str(uuid.uuid4())[:12]
        now = datetime.now()

        # Вычисляем эмоциональный импакт
        emotion_impact = 0.0
        if emotion_before and emotion_after:
            # Сравниваем уверенность и удовольствие
            before_conf = emotion_before.get("уверенность", 0.5)
            after_conf = emotion_after.get("уверенность", 0.5)
            before_pleasure = emotion_before.get("удовольствие", 0.0)
            after_pleasure = emotion_after.get("удовольствие", 0.0)

            emotion_impact = ((after_conf - before_conf) + (after_pleasure - before_pleasure)) / 2

        episode = Episode(
            id=episode_id,
            timestamp=now,
            user_id=user_id,  # === ФАЗА 3: Персонализация ===
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
        
        # Добавляем в кэш
        self._recent_episodes.append(episode)
        if len(self._recent_episodes) > self._max_recent:
            self._recent_episodes.pop(0)
        
        logger.info(f"📝 Эпизод добавлен: {episode_id} (тема: {topic}, значимость: {significance:.2f})")
        
        return episode
    
    def _save_episode(self, episode: Episode):
        """Сохраняет эпизод в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO episodes (
                id, timestamp, user_id, situation, participants, location,
                user_message, ai_response, intent, topic,
                emotion_before, emotion_after, emotion_impact,
                entities, concepts, keywords,
                related_episodes, parent_episode, continuation_of,
                significance, access_count, last_accessed,
                duration_seconds, success, feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode.id,
            episode.timestamp.isoformat(),
            episode.user_id,  # === ФАЗА 3: Персонализация ===
            episode.situation,
            json.dumps(episode.participants),
            episode.location,
            episode.user_message,
            episode.ai_response,
            episode.intent,
            episode.topic,
            json.dumps(episode.emotion_before),
            json.dumps(episode.emotion_after),
            episode.emotion_impact,
            json.dumps(episode.entities),
            json.dumps(episode.concepts),
            json.dumps(episode.keywords),
            json.dumps(episode.related_episodes),
            episode.parent_episode,
            episode.continuation_of,
            episode.significance,
            episode.access_count,
            episode.last_accessed.isoformat() if episode.last_accessed else None,
            episode.duration_seconds,
            1 if episode.success else 0,
            episode.feedback
        ))

        conn.commit()
        conn.close()
    
    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Получает эпизод по ID"""
        # Сначала проверяем кэш
        for ep in self._recent_episodes:
            if ep.id == episode_id:
                return ep
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_episode(row)
        return None
    
    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        """Преобразует строку БД в Episode"""
        # Безопасная загрузка JSON с fallback на пустые значения
        def safe_json_loads(value, default=None):
            if value is None:
                return default if default is not None else {}
            try:
                result = json.loads(value)
                return result if result is not None else default if default is not None else {}
            except (json.JSONDecodeError, TypeError):
                return default if default is not None else {}
        
        return Episode(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            situation=row["situation"],
            participants=safe_json_loads(row["participants"], []),
            location=row["location"],
            user_message=row["user_message"],
            ai_response=row["ai_response"],
            intent=row["intent"],
            topic=row["topic"],
            emotion_before=safe_json_loads(row["emotion_before"]),
            emotion_after=safe_json_loads(row["emotion_after"]),
            emotion_impact=row["emotion_impact"],
            entities=safe_json_loads(row["entities"], []),
            concepts=safe_json_loads(row["concepts"], []),
            keywords=safe_json_loads(row["keywords"], []),
            related_episodes=safe_json_loads(row["related_episodes"], []),
            parent_episode=row["parent_episode"],
            continuation_of=row["continuation_of"],
            significance=row["significance"],
            access_count=row["access_count"],
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
            duration_seconds=row["duration_seconds"],
            success=bool(row["success"]),
            feedback=row["feedback"]
        )
    
    def search_episodes(
        self,
        query: str = None,
        topic: str = None,
        intent: str = None,
        min_significance: float = 0.0,
        limit: int = 10,
        user_id: Optional[str] = None  # === ФАЗА 3: Персонализация ===
    ) -> List[Episode]:
        """
        Поиск эпизодов по различным критериям
        
        Args:
            user_id: ID владельца (None для поиска по всем + общим записям)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        conditions = []
        params = []

        if query:
            conditions.append("(user_message LIKE ? OR ai_response LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])

        if topic:
            conditions.append("topic = ?")
            params.append(topic)

        if intent:
            conditions.append("intent = ?")
            params.append(intent)

        if min_significance > 0:
            conditions.append("significance >= ?")
            params.append(min_significance)

        # === ФАЗА 3: Фильтр по user_id ===
        if user_id:
            # Ищем записи пользователя ИЛИ общие (user_id IS NULL)
            conditions.append("(user_id = ? OR user_id IS NULL)")
            params.append(user_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT * FROM episodes
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        episodes = [self._row_to_episode(row) for row in rows]

        # Обновляем access_count
        for ep in episodes:
            ep.access_count += 1
            ep.last_accessed = datetime.now()
            self._save_episode(ep)

        return episodes
    
    def get_timeline(
        self,
        days: int = 7,
        limit: int = 50
    ) -> List[Episode]:
        """
        Получает хронологию эпизодов за период
        """
        from datetime import timedelta
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT * FROM episodes 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (cutoff, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_episode(row) for row in rows]
    
    def get_related_episodes(self, episode_id: str) -> List[Episode]:
        """
        Получает связанные эпизоды
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем эпизод
        cursor.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return []
        
        episode = self._row_to_episode(row)
        related_ids = episode.related_episodes
        
        # Также ищем continuation_of
        cursor.execute("""
            SELECT * FROM episodes WHERE continuation_of = ?
        """, (episode_id,))
        
        continuation_rows = cursor.fetchall()
        for cont_row in continuation_rows:
            cont_ep = self._row_to_episode(cont_row)
            if cont_ep.id not in related_ids:
                related_ids.append(cont_ep.id)
        
        # Загружаем связанные эпизоды
        if not related_ids:
            conn.close()
            return []
        
        placeholders = ",".join("?" * len(related_ids))
        cursor.execute(f"""
            SELECT * FROM episodes WHERE id IN ({placeholders})
        """, related_ids)
        
        related_rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_episode(row) for row in related_rows]
    
    def get_significant_episodes(
        self,
        min_significance: float = 0.7,
        limit: int = 20
    ) -> List[Episode]:
        """
        Получает наиболее значимые эпизоды
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM episodes 
            WHERE significance >= ?
            ORDER BY significance DESC, timestamp DESC
            LIMIT ?
        """, (min_significance, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_episode(row) for row in rows]
    
    def link_episodes(
        self,
        episode_id: str,
        related_id: str,
        relation_type: str = "related"
    ):
        """
        Создаёт связь между эпизодами
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO episode_relations (episode_id, related_id, relation_type, created_at)
            VALUES (?, ?, ?, ?)
        """, (episode_id, related_id, relation_type, datetime.now().isoformat()))
        
        # Обновляем related_episodes в обоих эпизодах
        cursor.execute("SELECT related_episodes FROM episodes WHERE id = ?", (episode_id,))
        row = cursor.fetchone()
        if row:
            related = json.loads(row[0])
            if related_id not in related:
                related.append(related_id)
                cursor.execute("UPDATE episodes SET related_episodes = ? WHERE id = ?", 
                             (json.dumps(related), episode_id))
        
        cursor.execute("SELECT related_episodes FROM episodes WHERE id = ?", (related_id,))
        row = cursor.fetchone()
        if row:
            related = json.loads(row[0])
            if episode_id not in related:
                related.append(episode_id)
                cursor.execute("UPDATE episodes SET related_episodes = ? WHERE id = ?",
                             (json.dumps(related), related_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🔗 Эпизоды связаны: {episode_id} <-> {related_id}")
    
    def get_emotionally_charged(
        self,
        min_impact: float = 0.3,
        limit: int = 20
    ) -> List[Episode]:
        """
        Получает эмоционально заряженные эпизоды
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM episodes 
            WHERE ABS(emotion_impact) >= ?
            ORDER BY ABS(emotion_impact) DESC
            LIMIT ?
        """, (min_impact, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_episode(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Статистика эпизодической памяти
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общее количество
        cursor.execute("SELECT COUNT(*) FROM episodes")
        total = cursor.fetchone()[0]
        
        # По темам
        cursor.execute("""
            SELECT topic, COUNT(*) as cnt 
            FROM episodes 
            GROUP BY topic 
            ORDER BY cnt DESC
        """)
        by_topic = {row[0]: row[1] for row in cursor.fetchall()}
        
        # По намерениям
        cursor.execute("""
            SELECT intent, COUNT(*) as cnt 
            FROM episodes 
            GROUP BY intent 
            ORDER BY cnt DESC
        """)
        by_intent = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Средняя значимость
        cursor.execute("SELECT AVG(significance) FROM episodes")
        avg_significance = cursor.fetchone()[0] or 0.0
        
        # Эмоциональный импакт
        cursor.execute("SELECT AVG(ABS(emotion_impact)) FROM episodes")
        avg_emotion_impact = cursor.fetchone()[0] or 0.0
        
        # Связи
        cursor.execute("SELECT COUNT(*) FROM episode_relations")
        total_relations = cursor.fetchone()[0]
        
        # Наиболее используемые
        cursor.execute("""
            SELECT id, access_count 
            FROM episodes 
            ORDER BY access_count DESC 
            LIMIT 5
        """)
        most_accessed = cursor.fetchall()
        
        conn.close()
        
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
    
    async def update(self, id: str, data: Dict[str, Any]) -> bool:
        """Обновляет эпизод по ID"""
        episode = self.get_episode(id)
        if not episode:
            return False
        for key, value in data.items():
            if hasattr(episode, key):
                setattr(episode, key, value)
        self._save_episode(episode)
        return True

    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Получает эпизод по ID"""
        episode = self.get_episode(id)
        return episode.to_dict() if episode else None

    def clear(self):
        """Очищает эпизодическую память"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM episodes")
        cursor.execute("DELETE FROM episode_relations")
        
        conn.commit()
        conn.close()
        
        self._recent_episodes.clear()
        
        logger.info("🗑️ Эпизодическая память очищена")


# Глобальный экземпляр
_episodic_memory: Optional[EpisodicMemory] = None


def get_episodic_memory() -> EpisodicMemory:
    """Возвращает глобальную эпизодическую память"""
    global _episodic_memory
    if _episodic_memory is None:
        _episodic_memory = EpisodicMemory()
    return _episodic_memory