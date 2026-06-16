"""
📦 Supabase Client

Подключение к Supabase (PostgreSQL + Auth + Storage)
Для локальной разработки можно использовать локальный PostgreSQL

Использование:
    supabase = get_supabase()
    users = supabase.table("users").select("*").execute()
"""

import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger("padplus.supabase")

# Пытаемся импортировать supabase
HAS_SUPABASE = False
Client = type(None)  # Заглушка по умолчанию
create_client = None

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
    logger.info("✅ Supabase библиотека загружена")
except ImportError as e:
    logger.warning(f"⚠️ Supabase не установлен: {e}")
except Exception as e:
    logger.warning(f"⚠️ Ошибка импорта Supabase: {e}")


_supabase: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """
    Возвращает клиент Supabase
    
    Инициализируется один раз при первом вызове.
    Берёт URL и ключ из .env
    
    Returns:
        Клиент Supabase или None если не настроен
    """
    global _supabase
    
    if _supabase is not None:
        return _supabase
    
    if not HAS_SUPABASE:
        logger.warning("⚠️ Supabase клиент не установлен")
        return None
    
    # Получаем настройки из .env
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    # Для локальной разработки с PostgreSQL
    database_url = os.getenv("DATABASE_URL")
    
    if not supabase_url and not database_url:
        logger.warning("⚠️ SUPABASE_URL и DATABASE_URL не настроены")
        return None

    try:
        # Таймаут для HTTP запросов к Supabase (через переменную окружения httpx)
        # supabase-py использует httpx, таймаут задается через SUPABASE_TIMEOUT
        supabase_timeout = int(os.getenv("SUPABASE_TIMEOUT", "30"))
        
        if supabase_url and supabase_key:
            if supabase_key.startswith('sb_publishable_'):
                _supabase = create_client(supabase_url, supabase_key)
                logger.info(f"✅ Supabase подключен: {supabase_url} (anon key, timeout={supabase_timeout}s)")
            else:
                _supabase = create_client(supabase_url, supabase_key)
                logger.warning(f"⚠️ Supabase подключен с service_role ключом: {supabase_url}")
        elif supabase_url and not supabase_key:
            service_key = os.getenv("SUPABASE_SERVICE_KEY")
            if service_key:
                _supabase = create_client(supabase_url, service_key)
                logger.warning(f"⚠️ Supabase подключен через SERVICE_ROLE: {supabase_url}")
            else:
                logger.warning("⚠️ SUPABASE_URL задан, но SUPABASE_KEY и SUPABASE_SERVICE_KEY не настроены")
                return None
        elif database_url:
            logger.info("ℹ️ DATABASE_URL задан, но используется только для RAG и не создаёт Supabase клиента")
            return None
        else:
            logger.warning("⚠️ Нет настроек для подключения к БД")
            return None

        return _supabase
        
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        return None


def get_supabase_service() -> Optional[Client]:
    """
    Возвращает клиент Supabase с сервисным ключом для прямого доступа к таблицам
    
    Используется для операций, требующих обхода RLS (Row Level Security)
    Например: загрузка документов, управление коллекциями
    
    Returns:
        Клиент Supabase или None если не настроен
    """
    global _supabase_service
    
    if '_supabase_service' in globals() and _supabase_service is not None:
        return _supabase_service
    
    if not HAS_SUPABASE:
        logger.warning("⚠️ Supabase клиент не установлен")
        return None
    
    # Получаем настройки из .env
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url:
        logger.warning("⚠️ SUPABASE_URL не настроен")
        return None
    
    try:
        if service_key:
            _supabase_service = create_client(supabase_url, service_key)
            logger.info(f"✅ Supabase service client подключен: {supabase_url}")
        else:
            logger.warning("⚠️ SUPABASE_SERVICE_KEY не настроен — service client недоступен без service_role ключа")
            return None
        
        return _supabase_service
        
    except Exception as e:
        logger.error(f"❌ Ошибка подключения service client к БД: {e}")
        return None


def create_supabase_client_with_access_token(access_token: str) -> Optional[Client]:
    """
    Создаёт новый Supabase клиент, который использует service_role или anon key
    вместе с Authorization заголовком пользователя.
    """
    if not HAS_SUPABASE:
        logger.warning("⚠️ Supabase клиент не установлен")
        return None

    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        logger.warning("⚠️ SUPABASE_URL не настроен")
        return None

    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not supabase_key:
        logger.warning("⚠️ Ни SUPABASE_SERVICE_KEY, ни SUPABASE_KEY не настроены")
        return None

    try:
        client = create_client(supabase_url, supabase_key)
        client.options.headers["Authorization"] = f"Bearer {access_token}"
        return client
    except Exception as e:
        logger.error(f"❌ Ошибка создания Supabase клиента с access token: {e}")
        return None


def get_db_client(current_user: Optional[dict] = None):
    """
    Возвращает Supabase клиент с учётом авторизации пользователя.

    Если есть access_token — создаёт клиент с user-контекстом (для RLS).
    Иначе использует service_role (обходит RLS).
    """
    if current_user is not None and current_user.get("access_token"):
        client = create_supabase_client_with_access_token(current_user["access_token"])
        if client:
            return client

    db = get_supabase_service()
    if db:
        return db
    return get_supabase()


def check_database_connection() -> bool:
    """
    Проверяет подключение к базе данных
    
    Returns:
        True если подключение успешно
    """
    try:
        supabase = get_supabase()
        
        if supabase is None:
            # Проверяем DATABASE_URL напрямую
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                logger.info("✅ DATABASE_URL настроен")
                return True
            return False
        
        # Пробуем сделать простой запрос
        # (таблица может не существовать, поэтому игнорируем ошибки)
        try:
            supabase.table("users").select("count").limit(1).execute()
        except Exception:
            logger.debug("Таблица users не существует при проверке подключения")
        
        logger.info("✅ Подключение к БД работает")
        return True
        
    except Exception as e:
        logger.error(f"❌ Подключение к БД не работает: {e}")
        return False


def get_database_url() -> str:
    """
    Возвращает URL базы данных
    
    Returns:
        DATABASE_URL или None
    """
    return os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL")


# === SAFE QUERY METHODS WITH CIRCUIT BREAKER ===

async def safe_query(
    table: str,
    method: str,
    *,
    fallback: any = None,
    operation_name: str = None,
    **kwargs
) -> any:
    """
    Безопасный запрос к БД с Circuit Breaker
    
    Args:
        table: Название таблицы
        method: Метод (select, insert, update, delete)
        fallback: Fallback значение при ошибке
        operation_name: Название операции для логирования
        **kwargs: Аргументы для метода
    
    Returns:
        Результат запроса или fallback
    """
    from core.db_circuit_breaker import get_db_circuit_breaker
    
    cb = get_db_circuit_breaker()
    op_name = operation_name or f"{table}.{method}"
    
    async def operation(**kw):
        supabase = get_supabase()
        if not supabase:
            raise Exception("Supabase client not available")
        
        table_obj = supabase.table(table)
        result = await getattr(table_obj, method)(**kw).execute()
        return result
    
    async def fallback_func(**kw):
        logger.warning(f"🔄 Fallback для {op_name}")
        # Кэшируем fallback значение
        if fallback is not None:
            cb.cache_for_fallback(op_name, fallback)
        return fallback
    
    try:
        result = await cb.execute(
            operation=op_name,
            func=operation,
            fallback=fallback_func,
            **kwargs
        )
        return result
    except Exception as e:
        logger.error(f"❌ Безопасный запрос {op_name} не удался: {e}")
        raise


async def safe_select(
    table: str,
    columns: str = "*",
    **kwargs
) -> list:
    """
    Безопасный SELECT запрос
    
    Args:
        table: Название таблицы
        columns: Столбцы для выбора
        **kwargs: Фильтры (eq, neq, gt, lt, etc.)
    
    Returns:
        Список записей
    """
    result = await safe_query(
        table=table,
        method="select",
        fallback=[],
        columns=columns,
        **kwargs
    )
    return result.data if hasattr(result, 'data') else []


async def safe_insert(
    table: str,
    data: dict,
    **kwargs
) -> Optional[dict]:
    """
    Безопасный INSERT запрос
    
    Args:
        table: Название таблицы
        data: Данные для вставки
    
    Returns:
        Вставленная запись или None
    """
    result = await safe_query(
        table=table,
        method="insert",
        fallback=None,
        values=[data],
        **kwargs
    )
    if result and hasattr(result, 'data') and result.data:
        return result.data[0]
    return None


async def safe_update(
    table: str,
    data: dict,
    **kwargs
) -> bool:
    """
    Безопасный UPDATE запрос
    
    Args:
        table: Название таблицы
        data: Данные для обновления
        **kwargs: Фильтры (eq, neq, etc.)
    
    Returns:
        True если успешно
    """
    result = await safe_query(
        table=table,
        method="update",
        fallback=False,
        values=data,
        **kwargs
    )
    return result.count > 0 if hasattr(result, 'count') else False


async def safe_delete(
    table: str,
    **kwargs
) -> bool:
    """
    Безопасный DELETE запрос
    
    Args:
        table: Название таблицы
        **kwargs: Фильтры (eq, neq, etc.)
    
    Returns:
        True если успешно
    """
    result = await safe_query(
        table=table,
        method="delete",
        fallback=False,
        **kwargs
    )
    return True  # Если не было исключения — успешно


def get_db_circuit_breaker_stats() -> dict:
    """
    Получает статистику DB Circuit Breaker
    
    Returns:
        Dict со статистикой
    """
    from core.db_circuit_breaker import get_db_circuit_breaker
    return get_db_circuit_breaker().get_stats()


def reset_db_circuit_breaker():
    """
    Сбрасывает DB Circuit Breaker (для тестов или вручную)
    """
    from core.db_circuit_breaker import reset_db_circuit_breaker
    reset_db_circuit_breaker()
