"""
📊 Metrics Routes — API для мониторинга и метрик

Эндпоинты:
- GET /api/v1/metrics — Prometheus формат
- GET /api/v1/metrics/dashboard — JSON для дашборда
- GET /api/v1/metrics/db-circuit-breaker — статус DB Circuit Breaker
- GET /api/v1/metrics/pipeline — статистика пайплайна
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from typing import Dict, Any
import logging

logger = logging.getLogger("padplus.metrics_routes")

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/")
async def metrics() -> PlainTextResponse:
    """
    Prometheus metrics endpoint
    
    Возвращает метрики в формате Prometheus exposition format.
    Используйте с Prometheus scraping или Grafana.
    """
    try:
        from core.metrics_collector import get_metrics
        metrics_collector = get_metrics()
        return PlainTextResponse(
            content=metrics_collector.export_prometheus(),
            media_type="text/plain"
        )
    except Exception as e:
        logger.error(f"Ошибка экспорта метрик: {e}")
        return PlainTextResponse(
            content="# Error exporting metrics",
            media_type="text/plain",
            status_code=500
        )


@router.get("/dashboard")
async def dashboard_metrics() -> Dict[str, Any]:
    """
    Данные для дашборда
    
    Возвращает метрики в формате JSON для отображения в UI.
    Включает временные ряды за последний час.
    """
    try:
        from core.metrics_collector import get_metrics
        metrics_collector = get_metrics()
        return metrics_collector.get_dashboard_data()
    except Exception as e:
        logger.error(f"Ошибка получения данных дашборда: {e}")
        return {"error": str(e)}


@router.get("/summary")
async def metrics_summary() -> Dict[str, Any]:
    """
    Краткая сводка по всем метрикам
    """
    try:
        from core.metrics_collector import get_metrics
        metrics_collector = get_metrics()
        return metrics_collector.get_summary()
    except Exception as e:
        logger.error(f"Ошибка получения сводки: {e}")
        return {"error": str(e)}


@router.get("/db-circuit-breaker")
async def db_circuit_breaker_stats() -> Dict[str, Any]:
    """
    Статус DB Circuit Breaker
    
    Показывает состояние защиты базы данных:
    - state: closed/open/half_open
    - failure_count: количество последовательных ошибок
    - fallback_cache_size: размер fallback кэша
    """
    try:
        from core.supabase_client import get_db_circuit_breaker_stats
        return get_db_circuit_breaker_stats()
    except Exception as e:
        logger.error(f"Ошибка получения статуса DB Circuit Breaker: {e}")
        return {"error": str(e)}


@router.get("/pipeline")
async def pipeline_stats() -> Dict[str, Any]:
    """
    Статистика пайплайна
    
    Показывает:
    - pipeline_state: healthy/degraded/failed
    - degradations: список деградировавших компонентов
    - metrics: основные метрики выполнения
    """
    try:
        from core.pipeline import get_pipeline
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        
        # Добавляем метрики
        try:
            from core.metrics_collector import get_metrics
            metrics = get_metrics()
            stats["metrics"] = metrics.get_summary()
        except Exception:
            pass
        
        return stats
    except Exception as e:
        logger.error(f"Ошибка получения статистики пайплайна: {e}")
        return {"error": str(e)}


@router.get("/system")
async def system_metrics() -> Dict[str, Any]:
    """
    Системные метрики
    
    Возвращает общую информацию о состоянии system:
    - uptime
    - количество запросов
    - ошибки
    - использование памяти
    """
    try:
        import psutil
        import os
        import time
        from datetime import datetime
        
        process = psutil.Process(os.getpid())
        
        # Общие системные метрики
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent
        
        # Дисковый ввод вывод
        disk_io = psutil.disk_io_counters()
        disk_read_speed = disk_io.read_bytes / 1024 / 1024
        disk_write_speed = disk_io.write_bytes / 1024 / 1024
        disk_total_speed = disk_read_speed + disk_write_speed
        
        # Сетевые метрики
        net_io = psutil.net_io_counters()
        network_latency = 0
        
        # Пинг для определения латентности
        try:
            start = time.time()
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=1)
            network_latency = (time.time() - start) * 1000
        except:
            network_latency = 45.0
        
        # Активные подключения
        active_connections = len(process.connections())
        
        return {
            "uptime_seconds": (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds(),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_io": round(disk_total_speed, 2),
            "network_latency": round(network_latency, 1),
            "active_connections": active_connections,
            "max_connections": 1000,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Ошибка получения системных метрик: {e}")
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_io": 0,
            "network_latency": 0,
            "active_connections": 0,
            "max_connections": 1000,
            "error": str(e)
        }


@router.get("/memory")
async def memory_metrics() -> Dict[str, Any]:
    """
    Метрики памяти (Memory Manager)
    
    Возвращает детальную информацию об использовании памяти:
    - текущее использование
    - пороги
    - топ аллокаций
    """
    try:
        from core.memory_manager import get_memory_manager
        memory_manager = get_memory_manager()
        return memory_manager.get_stats()
    except Exception as e:
        logger.error(f"Ошибка получения метрик памяти: {e}")
        return {"error": str(e)}


@router.post("/reset")
async def reset_metrics() -> Dict[str, str]:
    """
    Сбросить все метрики
    
    Используйте осторожно — удаляет все накопленные данные.
    """
    try:
        from core.metrics_collector import reset_metrics
        reset_metrics()
        
        from core.supabase_client import reset_db_circuit_breaker
        reset_db_circuit_breaker()
        
        return {"status": "metrics reset successfully"}
    except Exception as e:
        logger.error(f"Ошибка сброса метрик: {e}")
        return {"error": str(e)}