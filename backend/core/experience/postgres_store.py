"""
ExperiencePostgresStore — PostgreSQL хранилище для Experience Layer.

Заменяет JSON-файловое хранение на PostgreSQL.
Обеспечивает персистентность между деплоями Render.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging
import os

logger = logging.getLogger("padplus.experience_pg")

postgres_available = False
try:
    import psycopg2
    from psycopg2.extras import Json
    postgres_available = True
    logger.info("PostgreSQL доступен для Experience Layer")
except Exception as e:
    logger.warning("PostgreSQL недоступен для Experience Layer: %s", e)
    psycopg2 = None
    Json = None


def _get_connection():
    """Создаёт подключение к PostgreSQL через DATABASE_URL."""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL не настроен")
    return psycopg2.connect(db_url)


class ExperiencePostgresStore:
    """PostgreSQL хранилище для записей опыта."""

    def save(self, record) -> str:
        data = record.to_dict() if hasattr(record, "to_dict") else record

        dialog_id = data.get("dialog_id", "")
        user_message = data.get("user_message", "")[:200]
        ai_response = data.get("ai_response", "")[:200]
        interaction_type = data.get("interaction_type", "unknown")
        significance = float(data.get("significance", 0))
        expectation = data.get("expectation", "")
        reality = data.get("reality", "")
        delta = data.get("delta", "")
        lessons = Json(data.get("lessons", []))
        strategy_success = float(data.get("strategy_success", 0))
        impulse_before = Json(data.get("impulse_before", {}))
        emotion_before = Json(data.get("emotion_before", {}))
        persona_before = Json(data.get("persona_before", {}))
        signals = Json(data.get("signals", {}))

        try:
            conn = _get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO experiences
                            (dialog_id, user_message, ai_response, interaction_type,
                             signals, significance, expectation, reality, delta,
                             lessons, strategy_success, impulse_before,
                             emotion_before, persona_before)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (dialog_id, user_message, ai_response, interaction_type,
                         signals, significance, expectation, reality, delta,
                         lessons, strategy_success, impulse_before,
                         emotion_before, persona_before),
                    )
                conn.commit()
            finally:
                conn.close()
            logger.debug("Experience saved to PostgreSQL: %s | type=%s sig=%.3f",
                         dialog_id, interaction_type, significance)
            return dialog_id
        except Exception as e:
            logger.error("Failed to save experience to PostgreSQL: %s", e)
            return ""

    def load_all(self) -> List[Dict[str, Any]]:
        try:
            conn = _get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT dialog_id, user_message, ai_response, interaction_type,
                               signals, significance, expectation, reality, delta,
                               lessons, strategy_success, impulse_before,
                               emotion_before, persona_before, created_at
                        FROM experiences
                        ORDER BY created_at DESC
                        """
                    )
                    rows = cur.fetchall()
                    results = []
                    for row in rows:
                        results.append({
                            "dialog_id": row[0],
                            "user_message": row[1],
                            "ai_response": row[2],
                            "interaction_type": row[3],
                            "signals": row[4] if isinstance(row[4], dict) else {},
                            "significance": float(row[5]) if row[5] else 0.0,
                            "expectation": row[6] or "",
                            "reality": row[7] or "",
                            "delta": row[8] or "",
                            "lessons": row[9] if isinstance(row[9], list) else [],
                            "strategy_success": float(row[10]) if row[10] else 0.0,
                            "impulse_before": row[11] if isinstance(row[11], dict) else {},
                            "emotion_before": row[12] if isinstance(row[12], dict) else {},
                            "persona_before": row[13] if isinstance(row[13], dict) else {},
                            "timestamp": row[14].isoformat() if row[14] else "",
                        })
                    return results
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to load experiences from PostgreSQL: %s", e)
            return []

    def count(self) -> int:
        try:
            conn = _get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM experiences")
                    return cur.fetchone()[0]
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to count experiences: %s", e)
            return 0
