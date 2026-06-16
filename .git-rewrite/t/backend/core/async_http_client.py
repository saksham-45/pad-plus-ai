"""
🚀 Async HTTP Client для LLM запросов

Connection pooling, retry logic, timeout management
Оптимизация для высокой пропускной способности
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger("padplus.async_http")


@dataclass
class RequestMetrics:
    """Метрики запроса"""
    url: str
    method: str
    status: int
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    retries: int = 0
    error: Optional[str] = None


class AsyncHTTPClient:
    """
    🚀 Асинхронный HTTP клиент с connection pooling

    Преимущества:
    - Connection pooling (переиспользование соединений)
    - Автоматические retry при ошибках
    - Timeout management
    - Метрики производительности
    - Rate limiting
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_retries: int = 3,
        timeout_seconds: int = 30,
        rate_limit_per_second: int = 10
    ):
        self.max_connections = max_connections
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.rate_limit = rate_limit_per_second

        # Connection pool
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None

        # Rate limiting
        self._rate_limiter = asyncio.Semaphore(rate_limit_per_second)
        self._request_times: list = []

        # Метрики
        self._metrics: list = []
        self._total_requests = 0
        self._failed_requests = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получает или создаёт сессию"""
        if self._session is None or self._session.closed:
            # Оптимизированный connector
            self._connector = aiohttp.TCPConnector(
                limit=self.max_connections,  # Лимит соединений
                limit_per_host=10,  # Лимит на хост
                ttl_dns_cache=300,  # Кэш DNS
                use_dns_cache=True,
                enable_cleanup_closed=True,
            )

            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers={
                    "User-Agent": "PAD+ AI/4.0",
                    "Accept": "application/json",
                }
            )

        return self._session

    async def close(self):
        """Закрывает сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def post(
        self,
        url: str,
        json: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        max_retries: int = None
    ) -> Dict[str, Any]:
        """
        POST запрос с retry logic

        Args:
            url: URL запроса
            json: JSON данные
            headers: Заголовки
            max_retries: Максимум попыток (переопределяет дефолтный)

        Returns:
            JSON ответ
        """
        retries = max_retries or self.max_retries
        last_error = None

        for attempt in range(retries):
            try:
                # Rate limiting
                async with self._rate_limiter:
                    session = await self._get_session()

                    start_time = datetime.now()

                    async with session.post(url, json=json, headers=headers or {}) as response:
                        duration = (datetime.now() - start_time).total_seconds() * 1000

                        # Логирование метрик
                        metrics = RequestMetrics(
                            url=url,
                            method="POST",
                            status=response.status,
                            duration_ms=duration,
                            retries=attempt
                        )
                        self._record_metrics(metrics)

                        if response.status != 200:
                            error_text = await response.text()
                            raise aiohttp.ClientError(
                                f"HTTP {response.status}: {error_text}"
                            )

                        return await response.json()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(f"Попытка {attempt + 1}/{retries} не удалась: {e}")

                if attempt < retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                    await asyncio.sleep(wait_time)
                continue

        # Все попытки исчерпаны
        self._failed_requests += 1
        logger.error(f"Все {retries} попыток не удались: {last_error}")
        raise last_error

    async def get(
        self,
        url: str,
        headers: Dict[str, str] = None,
        max_retries: int = None
    ) -> Dict[str, Any]:
        """GET запрос с retry logic"""
        retries = max_retries or self.max_retries
        last_error = None

        for attempt in range(retries):
            try:
                async with self._rate_limiter:
                    session = await self._get_session()

                    start_time = datetime.now()

                    async with session.get(url, headers=headers or {}) as response:
                        duration = (datetime.now() - start_time).total_seconds() * 1000

                        metrics = RequestMetrics(
                            url=url,
                            method="GET",
                            status=response.status,
                            duration_ms=duration,
                            retries=attempt
                        )
                        self._record_metrics(metrics)

                        if response.status != 200:
                            raise aiohttp.ClientError(f"HTTP {response.status}")

                        return await response.json()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(f"Попытка {attempt + 1}/{retries} не удалась: {e}")

                if attempt < retries - 1:
                    wait_time = (2 ** attempt) * 0.5
                    await asyncio.sleep(wait_time)
                continue

        self._failed_requests += 1
        logger.error(f"Все {retries} попыток не удались: {last_error}")
        raise last_error

    def _record_metrics(self, metrics: RequestMetrics):
        """Записывает метрики"""
        self._metrics.append(metrics)
        self._total_requests += 1

        # Храним только последние 1000
        if len(self._metrics) > 1000:
            self._metrics = self._metrics[-1000:]

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        if not self._metrics:
            return {
                "total_requests": 0,
                "failed_requests": 0,
                "avg_duration_ms": 0,
                "success_rate": 0
            }

        durations = [m.duration_ms for m in self._metrics]
        successful = len([m for m in self._metrics if m.status == 200])

        return {
            "total_requests": self._total_requests,
            "failed_requests": self._failed_requests,
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "success_rate": successful / len(self._metrics) if self._metrics else 0,
            "active_connections": len(self._request_times)
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_http_client: Optional[AsyncHTTPClient] = None


def get_async_http_client() -> AsyncHTTPClient:
    """Возвращает глобальный HTTP клиент"""
    global _http_client
    if _http_client is None:
        _http_client = AsyncHTTPClient(
            max_connections=100,
            max_retries=3,
            timeout_seconds=30,
            rate_limit_per_second=10
        )
    return _http_client
