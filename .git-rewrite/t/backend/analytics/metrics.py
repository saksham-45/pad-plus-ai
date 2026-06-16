"""
📊 Analytics Metrics — сбор и анализ метрик

- Метрики использования (сообщения, токены, время)
- Граф активностей (по часам/дням)
- Статистика по темам диалогов
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
import logging

logger = logging.getLogger("PAD+.analytics")


class Analytics:
    """
    📊 Аналитика использования PAD+ AI
    
    - Подсчёт сообщений и сессий
    - Граф активностей по времени
    - Топ темы диалогов
    - Экспорт отчётов
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "analytics.db"
            )
        
        self.db_path = db_path
        
        # Создаём директорию если не существует
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self._ensure_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_tables(self):
        """Создаёт таблицы аналитики"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Таблица событий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                user_agent TEXT
            )
        """)
        
        # Таблица сессий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                message_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0
            )
        """)
        
        # Индексы
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp 
            ON analytics_events(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type 
            ON analytics_events(event_type)
        """)
        
        conn.commit()
        conn.close()
    
    def track_event(
        self, 
        event_type: str, 
        event_data: Dict = None,
        session_id: str = None
    ) -> int:
        """Записывает событие аналитики"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO analytics_events 
            (event_type, event_data, timestamp, session_id)
            VALUES (?, ?, ?, ?)
        """, (
            event_type,
            json.dumps(event_data or {}, ensure_ascii=False),
            datetime.now().isoformat(),
            session_id
        ))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return event_id
    
    def track_message(
        self, 
        role: str, 
        text: str, 
        tokens: int = 0,
        session_id: str = None,
        topic: str = None
    ) -> int:
        """Записывает сообщение чата"""
        return self.track_event(
            event_type="message",
            event_data={
                "role": role,
                "text_length": len(text),
                "tokens": tokens,
                "topic": topic
            },
            session_id=session_id
        )
    
    def start_session(self, session_id: str = None) -> str:
        """Начинает новую сессию"""
        import uuid
        session_id = session_id or str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (id, started_at)
            VALUES (?, ?)
        """, (session_id, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def end_session(self, session_id: str):
        """Завершает сессию"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Подсчитываем сообщения в сессии
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM analytics_events
            WHERE session_id = ? AND event_type = 'message'
        """, (session_id,))
        
        count = cursor.fetchone()['cnt']
        
        cursor.execute("""
            UPDATE sessions 
            SET ended_at = ?, message_count = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), count, session_id))
        
        conn.commit()
        conn.close()
    
    # === МЕТРИКИ ===
    
    def get_dashboard_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Возвращает метрики для дашборда"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Общее количество сообщений
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM analytics_events
            WHERE event_type = 'message' AND timestamp >= ?
        """, (cutoff,))
        total_messages = cursor.fetchone()['cnt']
        
        # Сообщения по ролям
        cursor.execute("""
            SELECT event_data FROM analytics_events
            WHERE event_type = 'message' AND timestamp >= ?
        """, (cutoff,))
        
        by_role = {"user": 0, "ai": 0}
        total_tokens = 0
        
        for row in cursor.fetchall():
            try:
                data = json.loads(row['event_data'])
                role = data.get('role', 'unknown')
                if role in by_role:
                    by_role[role] += 1
                total_tokens += data.get('tokens', 0)
            except:
                pass
        
        # Количество сессий
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM sessions
            WHERE started_at >= ?
        """, (cutoff,))
        total_sessions = cursor.fetchone()['cnt']
        
        # Средняя длина сессии
        cursor.execute("""
            SELECT AVG(message_count) as avg FROM sessions
            WHERE started_at >= ? AND ended_at IS NOT NULL
        """, (cutoff,))
        avg_session = cursor.fetchone()['avg'] or 0
        
        conn.close()
        
        return {
            "period_days": days,
            "total_messages": total_messages,
            "messages_by_role": by_role,
            "total_sessions": total_sessions,
            "avg_session_length": round(avg_session, 1),
            "total_tokens": total_tokens,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_activity_graph(self, days: int = 7) -> Dict[str, Any]:
        """Возвращает граф активностей по времени"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT timestamp FROM analytics_events
            WHERE event_type = 'message' AND timestamp >= ?
        """, (cutoff,))
        
        # Активность по часам
        hourly = defaultdict(int)
        # Активность по дням недели
        weekday = defaultdict(int)
        # Активность по датам
        daily = defaultdict(int)
        
        for row in cursor.fetchall():
            try:
                ts = datetime.fromisoformat(row['timestamp'])
                hourly[ts.hour] += 1
                weekday[ts.weekday()] += 1
                daily[ts.strftime("%Y-%m-%d")] += 1
            except:
                pass
        
        conn.close()
        
        # Форматируем для графиков
        hour_labels = [f"{h:02d}:00" for h in range(24)]
        hour_data = [hourly.get(h, 0) for h in range(24)]
        
        weekday_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        weekday_data = [weekday.get(d, 0) for d in range(7)]
        
        return {
            "period_days": days,
            "hourly": {
                "labels": hour_labels,
                "data": hour_data,
                "peak_hour": max(hourly, key=hourly.get) if hourly else None
            },
            "weekday": {
                "labels": weekday_labels,
                "data": weekday_data,
                "peak_day": weekday_labels[max(weekday, key=weekday.get)] if weekday else None
            },
            "daily": {
                "labels": list(daily.keys()),
                "data": list(daily.values())
            },
            "total_events": sum(hourly.values()),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_topic_stats(self, days: int = 7, limit: int = 10) -> Dict[str, Any]:
        """Возвращает статистику по темам диалогов"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT event_data FROM analytics_events
            WHERE event_type = 'message' AND timestamp >= ?
        """, (cutoff,))
        
        # Собираем темы
        topics = Counter()
        
        for row in cursor.fetchall():
            try:
                data = json.loads(row['event_data'])
                topic = data.get('topic')
                if topic:
                    topics[topic] += 1
            except:
                pass
        
        conn.close()
        
        # Формируем список топ тем
        if topics:
            top_topics = [
                {"topic": t, "count": c} 
                for t, c in topics.most_common(limit)
            ]
            total_topics = len(topics)
        else:
            # Заглушка если нет данных
            top_topics = [
                {"topic": "общие вопросы", "count": 1},
                {"topic": "технические", "count": 1}
            ]
            total_topics = 2
        
        return {
            "period_days": days,
            "top_topics": top_topics,
            "total_topics": total_topics,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_full_report(self, days: int = 7) -> Dict[str, Any]:
        """Полный отчёт аналитики"""
        return {
            "dashboard": self.get_dashboard_metrics(days),
            "activity": self.get_activity_graph(days),
            "topics": self.get_topic_stats(days),
            "generated_at": datetime.now().isoformat()
        }
    
    def clear_old_data(self, days: int = 30):
        """Удаляет старые данные"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute(
            "DELETE FROM analytics_events WHERE timestamp < ?", 
            (cutoff,)
        )
        cursor.execute(
            "DELETE FROM sessions WHERE started_at < ?", 
            (cutoff,)
        )
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted


# Глобальный экземпляр
_analytics: Optional[Analytics] = None


def get_analytics() -> Analytics:
    """Возвращает глобальный экземпляр аналитики"""
    global _analytics
    if _analytics is None:
        _analytics = Analytics()
    return _analytics