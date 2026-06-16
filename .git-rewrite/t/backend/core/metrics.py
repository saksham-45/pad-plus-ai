"""
📊 Prometheus Metrics для PAD+ AI

Метрики для мониторинга:
- Количество запросов
- Время ответа
- Активные WebSocket соединения
- Использование памяти
- Ошибки

Использование:
    from core.metrics import track_request, REQUEST_COUNT
    
    @router.post("/chat")
    @track_request("chat")
    async def chat(...):
        ...
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    multiprocess,
    CollectorRegistry,
)
from prometheus_client import REGISTRY
import time
import os
from functools import wraps
from typing import Callable, Any
import logging

logger = logging.getLogger("padplus.metrics")

# ============================================================================
# МЕТРИКИ
# ============================================================================

# Счётчики
REQUEST_COUNT = Counter(
    'padplus_requests_total',
    'Total requests',
    ['endpoint', 'method', 'status']
)

LLM_REQUEST_COUNT = Counter(
    'padplus_llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status']
)

ERROR_COUNT = Counter(
    'padplus_errors_total',
    'Total errors',
    ['endpoint', 'error_type']
)

WEBSOCKET_CONNECT_COUNT = Counter(
    'padplus_websocket_connections_total',
    'Total WebSocket connections'
)

# Гистограммы
REQUEST_LATENCY = Histogram(
    'padplus_request_latency_seconds',
    'Request latency',
    ['endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

LLM_LATENCY = Histogram(
    'padplus_llm_latency_seconds',
    'LLM request latency',
    ['provider'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

RESPONSE_SIZE = Histogram(
    'padplus_response_size_bytes',
    'Response size',
    ['endpoint'],
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000)
)

# Gauge
ACTIVE_WEBSOCKETS = Gauge(
    'padplus_websockets_active',
    'Active WebSocket connections'
)

MEMORY_USAGE = Gauge(
    'padplus_memory_usage_bytes',
    'Memory usage'
)

CACHE_SIZE = Gauge(
    'padplus_cache_size',
    'Cache size',
    ['cache_type']
)

PIPELINE_QUEUE_SIZE = Gauge(
    'padplus_pipeline_queue_size',
    'Pipeline queue size'
)

# ============================================================================
# ДЕКОРАТОРЫ
# ============================================================================

def track_request(endpoint: str):
    """
    Декоратор для отслеживания запросов
    
    Использование:
        @router.post("/chat")
        @track_request("chat")
        async def chat(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                ERROR_COUNT.labels(
                    endpoint=endpoint,
                    error_type=type(e).__name__
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                
                REQUEST_COUNT.labels(
                    endpoint=endpoint,
                    method="POST",
                    status=status
                ).inc()
                
                REQUEST_LATENCY.labels(
                    endpoint=endpoint
                ).observe(duration)
        
        return wrapper
    return decorator


def track_llm_request(provider: str):
    """
    Декоратор для отслеживания LLM запросов
    
    Использование:
        @track_llm_request("openai")
        async def generate(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                
                LLM_REQUEST_COUNT.labels(
                    provider=provider,
                    model=kwargs.get('model', 'unknown'),
                    status=status
                ).inc()
                
                LLM_LATENCY.labels(
                    provider=provider
                ).observe(duration)
        
        return wrapper
    return decorator


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def update_memory_usage():
    """Обновляет метрику использования памяти"""
    import psutil
    process = psutil.Process()
    MEMORY_USAGE.set(process.memory_info().rss)


def update_cache_size(cache_type: str, size: int):
    """Обновляет размер кэша"""
    CACHE_SIZE.labels(cache_type=cache_type).set(size)


def update_websocket_count(count: int):
    """Обновляет количество активных WebSocket"""
    ACTIVE_WEBSOCKETS.set(count)


def update_pipeline_queue_size(size: int):
    """Обновляет размер очереди Pipeline"""
    PIPELINE_QUEUE_SIZE.set(size)


def get_metrics() -> bytes:
    """
    Возвращает метрики в формате Prometheus
    
    Returns:
        Байты с метриками
    """
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """
    Возвращает Content-Type для метрик
    
    Returns:
        Content-Type строка
    """
    return CONTENT_TYPE_LATEST
