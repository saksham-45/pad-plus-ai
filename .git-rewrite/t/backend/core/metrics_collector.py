"""
📊 MetricsCollector — Сбор и экспорт метрик для мониторинга

Поддерживаемые типы метрик:
- Counters (счетчики) — увеличивающиеся значения
- Gauges (датчики) — текущие значения
- Histograms (гистограммы) — распределение значений

Экспорт:
- Prometheus format (для scraping)
- JSON (для API/dashboard)
- Временные ряды (для графиков)

Цель: Обеспечить видимость того, что происходит в системе
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger("padplus.metrics")


@dataclass
class MetricPoint:
    """Точка данных временного ряда"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "labels": self.labels,
        }


@dataclass
class MetricSummary:
    """Сводка по метрике"""
    count: int = 0
    total: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    sum: float = 0.0
    
    @property
    def avg(self) -> float:
        return self.total / self.count if self.count > 0 else 0.0
    
    def add(self, value: float):
        self.count += 1
        self.total += value
        self.sum += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
    
    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "avg": self.avg,
            "min": self.min if self.min != float('inf') else 0,
            "max": self.max if self.max != float('-inf') else 0,
            "sum": self.sum,
        }


class MetricsCollector:
    """
    Сборщик метрик для мониторинга системы
    
    Особенности:
    - Автоматическая очистка старых данных
    - Поддержка label'ов для группировки
    - Экспорт в формате Prometheus
    - Временные ряды для графиков
    """
    
    def __init__(
        self,
        retention_hours: int = 24,      # Хранить данные 24 часа
        max_points_per_metric: int = 10000,  # Макс точек на метрику
    ):
        self.retention_hours = retention_hours
        self.max_points_per_metric = max_points_per_metric
        
        # Счетчики (_counters)
        self._counters: Dict[str, int] = defaultdict(int)
        
        # Гистограммы (значения для статистики)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Временные ряды (точки для графиков)
        self._time_series: Dict[str, List[MetricPoint]] = defaultdict(list)
        
        # Gauge (текущие значения)
        self._gauges: Dict[str, float] = {}
        
        # Время старта для uptime
        self._started_at = datetime.now()
        
        logger.info(f"📊 MetricsCollector initialized: retention={retention_hours}h")
    
    # === Counters (Счетчики) ===
    
    def increment(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """
        Увеличивает счетчик
        
        Args:
            name: Название метрики
            value: На сколько увеличить
            labels: Дополнительные метки (user_id, provider, etc.)
        """
        key = self._make_key(name, labels)
        self._counters[key] += value
        
        # Также записываем во временной ряд
        self._add_time_series_point(name, float(self._counters[key]), labels)
        
        logger.debug(f"📈 {key} = {self._counters[key]}")
    
    def get_counter(self, name: str, labels: Dict[str, str] = None) -> int:
        """Получает значение счетчика"""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)
    
    # === Gauges (Датчики) ===
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Устанавливает значение gauge"""
        key = self._make_key(name, labels)
        self._gauges[key] = value
        
        # Также записываем во временной ряд
        self._add_time_series_point(name, value, labels)
    
    def get_gauge(self, name: str, labels: Dict[str, str] = None) -> Optional[float]:
        """Получает значение gauge"""
        key = self._make_key(name, labels)
        return self._gauges.get(key)
    
    # === Histograms (Гистограммы) ===
    
    def record_value(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Записывает значение в гистограмму
        
        Args:
            name: Название метрики
            value: Значение
            labels: Дополнительные метки
        """
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        
        # Также записываем во временной ряд
        self._add_time_series_point(name, value, labels)
        
        # Очищаем старые значения если слишком много
        if len(self._histograms[key]) > self.max_points_per_metric:
            self._histograms[key] = self._histograms[key][-self.max_points_per_metric:]
        
        # Периодическая очистка старых данных
        self._cleanup_old_data()
    
    # Alias для совместимости
    def record_duration(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None):
        """Записывает длительность операции (alias для record_value)"""
        self.record_value(name, duration_ms, labels)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> dict:
        """Получает статистику гистограммы"""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])
        
        if not values:
            return {
                "count": 0,
                "avg": 0,
                "min": 0,
                "max": 0,
                "sum": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
            }
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            "count": count,
            "avg": sum(sorted_values) / count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "sum": sum(sorted_values),
            "p50": sorted_values[count // 2],
            "p95": sorted_values[int(count * 0.95)] if count > 1 else sorted_values[-1],
            "p99": sorted_values[int(count * 0.99)] if count > 1 else sorted_values[-1],
        }
    
    # === Time Series (Временные ряды) ===
    
    def _add_time_series_point(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Добавляет точку во временной ряд"""
        key = self._make_key(name, labels)
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            labels=labels or {},
        )
        self._time_series[key].append(point)
    
    def get_time_series(
        self,
        name: str,
        hours: int = 1,
        labels: Optional[Dict[str, str]] = None,
        aggregation: str = "avg"
    ) -> List[dict]:
        """
        Возвращает временной ряд за последние N часов
        
        Args:
            name: Название метрики
            hours: За сколько часов
            labels: Фильтр по меткам
            aggregation: Метод агрегации (avg, sum, min, max)
        
        Returns:
            Список точек с агрегацией по минутам
        """
        key = self._make_key(name, labels)
        points = self._time_series.get(key, [])
        
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [p for p in points if p.timestamp > cutoff]
        
        if not recent:
            return []
        
        # Агрегируем по минутам
        aggregated = defaultdict(list)
        for p in recent:
            minute_key = p.timestamp.replace(second=0, microsecond=0)
            aggregated[minute_key].append(p.value)
        
        # Применяем агрегацию
        result = []
        for ts, vals in sorted(aggregated.items()):
            if aggregation == "avg":
                value = sum(vals) / len(vals)
            elif aggregation == "sum":
                value = sum(vals)
            elif aggregation == "min":
                value = min(vals)
            elif aggregation == "max":
                value = max(vals)
            else:
                value = sum(vals) / len(vals)
            
            result.append({
                "timestamp": ts.isoformat(),
                "value": round(value, 4),
                "count": len(vals),
            })
        
        return result
    
    # === Export (Экспорт) ===
    
    def export_prometheus(self) -> str:
        """
        Экспорт метрик в формате Prometheus
        
        Returns:
            Строка в формате Prometheus exposition format
        """
        lines = []
        now = datetime.now().isoformat()
        
        # Метрика uptime
        uptime_seconds = (datetime.now() - self._started_at).total_seconds()
        lines.append("# TYPE padplus_uptime_seconds gauge")
        lines.append(f"padplus_uptime_seconds {uptime_seconds:.0f}")
        
        # Метрика времени сбора
        lines.append("# TYPE padplus_metrics_collected_at gauge")
        lines.append(f"padplus_metrics_collected_at {time.time():.0f}")
        
        # Счетчики
        for key, value in self._counters.items():
            metric_name = key.split("{")[0] if "{" in key else key
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{key} {value}")
        
        # Gauges
        for key, value in self._gauges.items():
            metric_name = key.split("{")[0] if "{" in key else key
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{key} {value}")
        
        # Гистограммы (как summary)
        for key in self._histograms:
            if not self._histograms[key]:
                continue
            
            metric_name = key.split("{")[0] if "{" in key else key
            stats = self.get_histogram_stats(key)
            
            lines.append(f"# TYPE {metric_name} summary")
            lines.append(f"{key}_count {stats['count']}")
            lines.append(f"{key}_sum {stats['sum']:.4f}")
            lines.append(f"{key}{{quantile=\"0.5\"}} {stats['p50']:.4f}")
            lines.append(f"{key}{{quantile=\"0.95\"}} {stats['p95']:.4f}")
            lines.append(f"{key}{{quantile=\"0.99\"}} {stats['p99']:.4f}")
        
        return "\n".join(lines)
    
    def get_dashboard_data(self) -> dict:
        """
        Данные для дашборда
        
        Returns:
            Dict с основными метриками для отображения
        """
        return {
            "uptime_seconds": (datetime.now() - self._started_at).total_seconds(),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                key: self.get_histogram_stats(key)
                for key in self._histograms
                if self._histograms[key]
            },
            "time_series": {
                "pipeline_duration_ms": self.get_time_series("pipeline_duration_ms", hours=1),
                "requests_total": self.get_time_series("requests_total", hours=1),
                "errors_total": self.get_time_series("errors_total", hours=1),
                "active_users": self.get_time_series("active_users", hours=1),
            },
            "collected_at": datetime.now().isoformat(),
        }
    
    def get_summary(self) -> dict:
        """Краткая сводка по всем метрикам"""
        return {
            "total_counters": len(self._counters),
            "total_gauges": len(self._gauges),
            "total_histograms": len(self._histograms),
            "total_time_series": len(self._time_series),
            "uptime_seconds": (datetime.now() - self._started_at).total_seconds(),
            "retention_hours": self.retention_hours,
        }
    
    # === Utility Methods ===
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Создает ключ метрики с labels"""
        if not labels:
            return name
        
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _cleanup_old_data(self):
        """Удаляет старые данные за пределами retention периода"""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        
        # Очищаем временные ряды
        for key in list(self._time_series.keys()):
            self._time_series[key] = [
                p for p in self._time_series[key]
                if p.timestamp > cutoff
            ]
            if not self._time_series[key]:
                del self._time_series[key]
    
    def reset(self):
        """Сбрасывает все метрики"""
        self._counters.clear()
        self._histograms.clear()
        self._time_series.clear()
        self._gauges.clear()
        self._started_at = datetime.now()
        logger.info("📊 MetricsCollector сброшен")
    
    def record_timing(self, name: str, start_time: float, labels: Optional[Dict[str, str]] = None):
        """Записывает время выполнения операции (в мс)"""
        duration_ms = (time.time() - start_time) * 1000
        self.record_duration(name, duration_ms, labels)
        return duration_ms


# === Convenience Context Manager ===

class Timer:
    """Контекстный менеджер для замера времени"""
    
    def __init__(self, metrics: MetricsCollector, name: str, labels: Optional[Dict[str, str]] = None):
        self.metrics = metrics
        self.name = name
        self.labels = labels
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = self.metrics.record_timing(self.name, self.start_time, self.labels)
        return False


# === Global Instance ===

_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Возвращает глобальный MetricsCollector"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def reset_metrics():
    """Сбрасывает глобальный MetricsCollector (для тестов)"""
    global _metrics
    _metrics = None


def timer(name: str, labels: Optional[Dict[str, str]] = None) -> Timer:
    """Создает Timer для замера времени"""
    return Timer(get_metrics(), name, labels)