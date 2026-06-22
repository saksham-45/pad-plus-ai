"""
pg_pool.py — пул соединений PostgreSQL.

Заменяет psycopg2.ThreadedConnectionPool на queue.Queue.
Причина: ThreadedConnectionPool.putconn() вызывает conn.rollback(),
который падает если PG уже закрыл коннект (Render free tier),
слот в _used не очищается, пул исчерпывается.
"""

import logging
import os
import queue
import threading
import time
from typing import Optional

logger = logging.getLogger("padplus.pg_pool")

_available = False
try:
    import psycopg2
    _available = True
except Exception as e:
    logger.warning("PostgreSQL недоступен: %s", e)
    psycopg2 = None


class PgPool:
    """Потокобезопасный пул соединений на queue.Queue."""

    def __init__(self, maxconn: int = None):
        self._maxconn = maxconn or int(os.getenv("PG_POOL_MAX", "20"))
        self._queue: queue.Queue = queue.Queue(maxsize=self._maxconn)
        self._dsn: Optional[str] = None
        self._lock = threading.Lock()
        self._size = 0  # сколько соединений всего создано
        self._retries = int(os.getenv("PG_POOL_RETRIES", "3"))
        self._retry_delay = float(os.getenv("PG_POOL_RETRY_DELAY", "0.5"))
        self._closed = False
        logger.info("PgPool создан: maxconn=%d", self._maxconn)

    @property
    def available(self) -> bool:
        return _available

    def _resolve_dsn(self) -> str:
        from core.config_manager import get_database_url
        dsn = get_database_url()
        if dsn and dsn.startswith("postgresql"):
            return dsn
        env_url = os.environ.get("DATABASE_URL")
        if env_url and env_url.startswith("postgresql"):
            return env_url
        raise RuntimeError("Нет DATABASE_URL для PostgreSQL")

    def _connect(self) -> object:
        dsn = self._dsn or self._resolve_dsn()
        self._dsn = dsn
        return psycopg2.connect(
            dsn,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
            connect_timeout=5,
        )

    def _is_alive(self, conn) -> bool:
        try:
            if conn.closed:
                return False
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return True
        except Exception:
            return False

    def get_conn(self):
        if self._closed:
            raise RuntimeError("Pool closed")
        last_error = None
        for attempt in range(self._retries + 1):
            try:
                # Пробуем взять из очереди с таймаутом
                try:
                    conn = self._queue.get(timeout=2)
                except queue.Empty:
                    conn = None

                if conn is not None:
                    # Проверяем жив ли коннект
                    if self._is_alive(conn):
                        return conn
                    # Мёртвый — закрываем
                    try:
                        if not conn.closed:
                            conn.close()
                    except Exception:
                        pass
                    with self._lock:
                        self._size -= 1
                    conn = None

                # Создаём новый, если не превысили лимит
                with self._lock:
                    if self._size < self._maxconn:
                        conn = self._connect()
                        self._size += 1
                        return conn
                    # Лимит исчерпан — ждём освобождения
                    # (conn остаётся None, цикл повторится)
            except Exception as e:
                last_error = e
                if "timeout" in str(e).lower() or "could not connect" in str(e).lower():
                    logger.warning("Pool timeout, retry %d/%d in %.1fs",
                                   attempt + 1, self._retries, self._retry_delay)
                    time.sleep(self._retry_delay)
                    continue
                # Если коннект уже взят но упал — не теряем
                if conn is not None:
                    self._put_conn_internal(conn)
                raise

        raise last_error or RuntimeError("connection pool exhausted")

    def _put_conn_internal(self, conn):
        """Безопасно возвращает коннект в очередь или закрывает."""
        if conn is None:
            return
        try:
            if conn.closed:
                with self._lock:
                    self._size -= 1
                return
            # Откатываем незавершённую транзакцию перед возвратом
            try:
                conn.rollback()
            except Exception:
                pass
            if self._is_alive(conn):
                self._queue.put(conn, timeout=1)
            else:
                try:
                    conn.close()
                except Exception:
                    pass
                with self._lock:
                    self._size -= 1
        except Exception:
            try:
                if not conn.closed:
                    conn.close()
            except Exception:
                pass
            with self._lock:
                self._size -= 1

    def put_conn(self, conn):
        if conn is None:
            return
        self._put_conn_internal(conn)

    def close_all(self):
        self._closed = True
        count = 0
        while True:
            try:
                conn = self._queue.get_nowait()
                try:
                    conn.close()
                except Exception:
                    pass
                count += 1
            except queue.Empty:
                break
        with self._lock:
            self._size = 0
        logger.info("PostgreSQL pool закрыт: закрыто %d соединений", count)


_pool: Optional[PgPool] = None


def get_pool() -> PgPool:
    global _pool
    if _pool is None:
        _pool = PgPool()
    return _pool


def close_pool():
    global _pool
    if _pool is not None:
        _pool.close_all()
        _pool = None


def get_connection():
    """Получить соединение из пула."""
    if not _available:
        raise RuntimeError("PostgreSQL недоступен (psycopg2 не загружен)")
    pool = get_pool()
    return pool.get_conn()


def put_connection(conn):
    """Вернуть соединение в пул."""
    if not _available or conn is None:
        return
    pool = get_pool()
    pool.put_conn(conn)
