"""
pg_storage.py — PostgreSQL storage backend для Persona/Roots/Emotion

Использует psycopg2 (как rag_postgres.py) для работы с Supabase PostgreSQL.
Заменяет хранение в JSON-файлах.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger("PAD+.pg_storage")


class PgStorage:
    """
    Упрощённый storage-слой для модулей памяти.
    Поддерживает два режима:
    - `singleton`: одна строка с фиксированным id (persona_state, emotion_state)
    - `collection`: много строк с разными id (roots_knowledge)
    
    ВАЖНО: соединения возвращаются в пул после каждой операции,
    чтобы избежать "connection pool exhausted" на Render free tier.
    """

    def __init__(self, table: str, mode: str = "singleton", pk: str = "id"):
        self.table = table
        self.mode = mode
        self.pk = pk

    def _with_conn(self, func):
        """Выполняет функцию с соединением из пула и возвращает его."""
        from .pg_pool import get_connection, put_connection
        conn = None
        try:
            conn = get_connection()
            return func(conn)
        except Exception as e:
            raise
        finally:
            if conn is not None:
                put_connection(conn)

    def _ensure_table(self):
        def _do(conn):
            cur = conn.cursor()
            try:
                if self.table == "persona_state":
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS persona_state (
                            id TEXT PRIMARY KEY DEFAULT 'system',
                            data JSONB NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            updated_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)
                elif self.table == "emotion_state":
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS emotion_state (
                            id TEXT PRIMARY KEY DEFAULT 'system',
                            data JSONB NOT NULL,
                            updated_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)
                elif self.table == "roots_knowledge":
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS roots_knowledge (
                            id TEXT PRIMARY KEY,
                            text TEXT NOT NULL,
                            category TEXT DEFAULT 'philosophy',
                            priority INTEGER DEFAULT 50,
                            immutable BOOLEAN DEFAULT TRUE,
                            source TEXT DEFAULT 'system',
                            metadata JSONB DEFAULT '{}',
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cur.close()
        try:
            self._with_conn(_do)
        except Exception as e:
            logger.warning(f"PgStorage._ensure_table({self.table}): {e}")

    def load_singleton(self, default_factory) -> Dict[str, Any]:
        def _do(conn):
            cur = conn.cursor()
            try:
                cur.execute(f"SELECT data FROM {self.table} WHERE id = 'system'")
                row = cur.fetchone()
                if row:
                    data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                    return data
            finally:
                cur.close()
            return default_factory()
        try:
            self._ensure_table()
            return self._with_conn(_do)
        except Exception as e:
            logger.warning(f"PgStorage.load_singleton({self.table}): {e}")
        return default_factory()

    def save_singleton(self, data: dict):
        def _do(conn):
            cur = conn.cursor()
            try:
                cur.execute(
                    f"INSERT INTO {self.table} (id, data, updated_at) "
                    f"VALUES ('system', %s, NOW()) "
                    f"ON CONFLICT (id) DO UPDATE SET data = %s, updated_at = NOW()",
                    [json.dumps(data, ensure_ascii=False), json.dumps(data, ensure_ascii=False)]
                )
                conn.commit()
            finally:
                cur.close()
        try:
            self._ensure_table()
            self._with_conn(_do)
        except Exception as e:
            logger.warning(f"PgStorage.save_singleton({self.table}): {e}")

    def load_collection(self, default_factory) -> List[Dict[str, Any]]:
        def _do(conn):
            cur = conn.cursor()
            try:
                cur.execute(f"SELECT * FROM {self.table} ORDER BY priority DESC")
                cols = [desc[0] for desc in cur.description]
                rows = []
                for row in cur.fetchall():
                    item = dict(zip(cols, row))
                    if isinstance(item.get("metadata"), str):
                        item["metadata"] = json.loads(item["metadata"])
                    rows.append(item)
                return rows
            finally:
                cur.close()
        try:
            self._ensure_table()
            return self._with_conn(_do)
        except Exception as e:
            logger.warning(f"PgStorage.load_collection({self.table}): {e}")
        return default_factory()

    def save_collection_item(self, item: dict):
        def _do(conn):
            cur = conn.cursor()
            try:
                pk_value = item.get(self.pk)
                if not pk_value:
                    raise ValueError(f"Нет первичного ключа '{self.pk}' в данных")
                meta = item.get("metadata", {})
                if isinstance(meta, dict):
                    meta = json.dumps(meta, ensure_ascii=False)
                cur.execute(
                    f"INSERT INTO {self.table} "
                    f"(id, text, category, priority, immutable, source, metadata, created_at) "
                    f"VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s) "
                    f"ON CONFLICT (id) DO UPDATE SET "
                    f"text = EXCLUDED.text, priority = EXCLUDED.priority, "
                    f"metadata = EXCLUDED.metadata",
                    (
                        pk_value,
                        item.get("text", ""),
                        item.get("category", "philosophy"),
                        item.get("priority", 50),
                        item.get("immutable", True),
                        item.get("source", "system"),
                        meta,
                        item.get("created_at", datetime.now(timezone.utc).isoformat())
                    )
                )
                conn.commit()
            finally:
                cur.close()
        try:
            self._ensure_table()
            self._with_conn(_do)
        except Exception as e:
            logger.warning(f"PgStorage.save_collection_item({self.table}): {e}")

    def delete_collection_item(self, pk_value: str):
        def _do(conn):
            cur = conn.cursor()
            try:
                cur.execute(f"DELETE FROM {self.table} WHERE {self.pk} = %s", [pk_value])
                conn.commit()
            finally:
                cur.close()
        try:
            self._ensure_table()
            self._with_conn(_do)
        except Exception as e:
            logger.warning(f"PgStorage.delete_collection_item({self.table}): {e}")

    def close(self):
        pass
