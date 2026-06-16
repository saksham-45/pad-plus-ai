"""
📊 Monitoring — Система мониторинга и алертинга для PAD+ AI

Предоставляет:
- Health checks
- Performance metrics
- Error tracking
- Resource monitoring
- Alerting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

# Пытаемся импортировать psutil
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

from core.config_manager import get_config
from core.cache_manager import get_cache_manager

logger = logging.getLogger("padplus.monitoring")


@dataclass
class SystemMetrics:
    """Метрики системы"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    active_connections: int
    response_time_avg: float
    error_rate: float
    cache_hit_rate: float
    queue_size: int


@dataclass
class Alert:
    """Алерт"""
    severity: str  # info, warning, error, critical
    category: str
    message: str
    timestamp: datetime
    resolved: bool = False


class MonitoringSystem:
    """
    📊 Система мониторинга
    
    Собирает метрики, отслеживает производительность и отправляет алерты
    """
    
    def __init__(self):
        self.config = get_config()
        self.cache_manager = get_cache_manager()
        self.metrics_history: deque = deque(maxlen=1000)  # Последние 1000 метрик
        self.alerts: List[Alert] = []
        self.alert_rules = self._load_alert_rules()
        self.performance_stats = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.start_time = datetime.now()
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Пороги для алертов
        self.thresholds = {
            "cpu_critical": 90.0,
            "cpu_warning": 70.0,
            "memory_critical": 90.0,
            "memory_warning": 70.0,
            "disk_critical": 95.0,
            "disk_warning": 80.0,
            "response_time_critical": 5.0,  # seconds
            "response_time_warning": 2.0,
            "error_rate_critical": 0.1,  # 10%
            "error_rate_warning": 0.05,  # 5%
            "cache_hit_rate_critical": 0.3,  # 30%
            "cache_hit_rate_warning": 0.5,  # 50%
        }
    
    def _load_alert_rules(self) -> Dict[str, Any]:
        """Загружает правила алертинга из конфигурации"""
        return {
            "cpu_high": {
                "condition": lambda m: m.cpu_percent > self.thresholds["cpu_critical"],
                "message": "High CPU usage detected",
                "severity": "critical"
            },
            "memory_high": {
                "condition": lambda m: m.memory_percent > self.thresholds["memory_critical"],
                "message": "High memory usage detected",
                "severity": "critical"
            },
            "response_time_high": {
                "condition": lambda m: m.response_time_avg > self.thresholds["response_time_critical"],
                "message": "High response time detected",
                "severity": "warning"
            },
            "error_rate_high": {
                "condition": lambda m: m.error_rate > self.thresholds["error_rate_critical"],
                "message": "High error rate detected",
                "severity": "critical"
            },
            "cache_hit_rate_low": {
                "condition": lambda m: m.cache_hit_rate < self.thresholds["cache_hit_rate_critical"],
                "message": "Low cache hit rate detected",
                "severity": "warning"
            }
        }
    
    async def start_monitoring(self):
        """Запускает фоновый мониторинг"""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("📊 Мониторинг запущен")
    
    async def stop_monitoring(self):
        """Останавливает фоновый мониторинг"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
            logger.info("📊 Мониторинг остановлен")
    
    async def _monitoring_loop(self):
        """Фоновый цикл мониторинга"""
        while True:
            try:
                await self._collect_metrics()
                await self._check_alerts()
                await asyncio.sleep(30)  # Сбор метрик каждые 30 секунд
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
    
    async def _collect_metrics(self):
        """Собирает системные метрики"""
        try:
            # Системные метрики
            if HAS_PSUTIL:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()
            else:
                cpu_percent = 0.0
                memory = type('obj', (object,), {'percent': 0.0})()
                disk = type('obj', (object,), {'percent': 0.0})()
                network = type('obj', (object,), {'bytes_sent': 0, 'bytes_recv': 0})()
            
            # Прикладные метрики
            cache_stats = self.cache_manager.get_stats()
            response_time_avg = self._calculate_avg_response_time()
            error_rate = self._calculate_error_rate()
            active_connections = len(self._get_active_connections())
            queue_size = self._get_queue_size()
            
            # Создаем метрики
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                network_sent=network.bytes_sent,
                network_recv=network.bytes_recv,
                active_connections=active_connections,
                response_time_avg=response_time_avg,
                error_rate=error_rate,
                cache_hit_rate=cache_stats.get("memory", {}).get("hit_rate", 0.0),
                queue_size=queue_size
            )
            
            self.metrics_history.append(metrics)
            logger.debug(f"📊 Метрики собраны: CPU={cpu_percent:.1f}%, Memory={memory.percent:.1f}%")
            
        except Exception as e:
            logger.error(f"Ошибка сбора метрик: {e}")
    
    def _calculate_avg_response_time(self) -> float:
        """Рассчитывает среднее время ответа"""
        # Здесь можно интегрировать с вашей системой логирования запросов
        # Пока возвращаем заглушку
        return 0.5
    
    def _calculate_error_rate(self) -> float:
        """Рассчитывает rate ошибок"""
        total_requests = sum(self.error_counts.values()) + sum(
            self.performance_stats["success"]
        )
        if total_requests == 0:
            return 0.0
        error_count = sum(self.error_counts.values())
        return error_count / total_requests
    
    def _get_active_connections(self) -> List:
        """Получает активные соединения"""
        # Здесь можно интегрировать с вашим WebSocket менеджером
        # Пока возвращаем заглушку
        return []
    
    def _get_queue_size(self) -> int:
        """Получает размер очереди задач"""
        # Здесь можно интегрировать с вашей системой очередей
        # Пока возвращаем заглушку
        return 0
    
    async def _check_alerts(self):
        """Проверяет условия для алертов"""
        if not self.metrics_history:
            return
        
        latest_metrics = self.metrics_history[-1]
        
        for rule_name, rule in self.alert_rules.items():
            if rule["condition"](latest_metrics):
                alert = Alert(
                    severity=rule["severity"],
                    category=rule_name,
                    message=rule["message"],
                    timestamp=datetime.now()
                )
                await self._send_alert(alert)
    
    async def _send_alert(self, alert: Alert):
        """Отправляет алерт"""
        # Проверяем, не было ли уже такого алерта
        for existing_alert in self.alerts:
            if (existing_alert.category == alert.category and
                not existing_alert.resolved and
                (datetime.now() - existing_alert.timestamp).seconds < 300):  # 5 минут
                return
        
        self.alerts.append(alert)
        logger.warning(f"🚨 Алерт [{alert.severity}]: {alert.message}")
        
        # Здесь можно добавить отправку в Slack, Telegram, email и т.д.
        await self._notify_alert(alert)

    async def _notify_alert(self, alert: Alert):
        """Уведомляет о алерте (интеграция с внешними сервисами)"""
        # Заглушка для интеграции с внешними сервисами уведомлений
        # Можно добавить Slack, Telegram, email и т.д.
        pass
    
    def record_request(self, endpoint: str, response_time: float, success: bool = True):
        """Регистрирует запрос для статистики"""
        self.performance_stats["response_times"].append(response_time)
        if success:
            self.performance_stats["success"].append(1)
        else:
            self.performance_stats["success"].append(0)
            self.error_counts[endpoint] += 1
    
    def record_error(self, error_type: str, error_message: str):
        """Регистрирует ошибку"""
        self.error_counts[error_type] += 1
        logger.error(f"❌ Ошибка [{error_type}]: {error_message}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Возвращает статус здоровья системы"""
        if not self.metrics_history:
            return {"status": "unknown", "message": "Нет данных"}
        
        latest = self.metrics_history[-1]
        critical_alerts = [a for a in self.alerts if a.severity == "critical" and not a.resolved]
        warning_alerts = [a for a in self.alerts if a.severity == "warning" and not a.resolved]
        
        # Определяем статус
        if critical_alerts:
            status = "critical"
        elif warning_alerts:
            status = "warning"
        elif (latest.cpu_percent < self.thresholds["cpu_warning"] and
              latest.memory_percent < self.thresholds["memory_warning"] and
              latest.response_time_avg < self.thresholds["response_time_warning"] and
              latest.error_rate < self.thresholds["error_rate_warning"]):
            status = "healthy"
        else:
            status = "degraded"
        
        return {
            "status": status,
            "uptime": str(datetime.now() - self.start_time),
            "latest_metrics": asdict(latest),
            "active_alerts": {
                "critical": len(critical_alerts),
                "warning": len(warning_alerts)
            },
            "error_counts": dict(self.error_counts),
            "cache_stats": self.cache_manager.get_stats()
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Возвращает отчет о производительности"""
        if not self.performance_stats["response_times"]:
            return {"message": "Нет данных о производительности"}
        
        response_times = self.performance_stats["response_times"]
        success_count = sum(self.performance_stats["success"])
        total_count = len(self.performance_stats["success"])
        
        return {
            "total_requests": total_count,
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "avg_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": sorted(response_times)[int(0.95 * len(response_times))],
            "error_breakdown": dict(self.error_counts)
        }
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Возвращает историю метрик за указанное количество часов"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff]
        return [asdict(m) for m in recent_metrics]
    
    def clear_alerts(self, category: Optional[str] = None):
        """Очищает алерты"""
        if category:
            for alert in self.alerts:
                if alert.category == category:
                    alert.resolved = True
        else:
            self.alerts = []
        logger.info(f"✅ Алерты очищены: {category or 'все'}")


# Глобальный экземпляр
_monitoring_system: Optional[MonitoringSystem] = None


def get_monitoring_system() -> MonitoringSystem:
    """Возвращает глобальную систему мониторинга"""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = MonitoringSystem()
    return _monitoring_system