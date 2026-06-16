"""
🧪 Тесты для MetricsCollector

Проверяет:
- Counters (счетчики)
- Gauges (датчики)
- Histograms (гистограммы)
- Time series (временные ряды)
- Prometheus экспорт
"""

import pytest
import sys
from pathlib import Path
import time

# Добавляем backend в path для импортов
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.metrics_collector import (
    MetricsCollector,
    MetricPoint,
    get_metrics,
    reset_metrics,
    timer,
)


@pytest.fixture
def metrics():
    """Создает новый MetricsCollector для каждого теста"""
    return MetricsCollector(retention_hours=1)


@pytest.fixture
def global_metrics():
    """Сбрасывает глобальный MetricsCollector"""
    reset_metrics()
    yield get_metrics()
    reset_metrics()


class TestCounters:
    """Тесты счетчиков"""
    
    def test_increment_counter(self, metrics):
        """Увеличение счетчика"""
        metrics.increment("requests_total")
        assert metrics.get_counter("requests_total") == 1
        
        metrics.increment("requests_total", 5)
        assert metrics.get_counter("requests_total") == 6
    
    def test_counter_with_labels(self, metrics):
        """Счетчик с метками"""
        metrics.increment("requests_total", labels={"method": "GET"})
        metrics.increment("requests_total", labels={"method": "POST"})
        metrics.increment("requests_total", labels={"method": "GET"})
        
        assert metrics.get_counter("requests_total", labels={"method": "GET"}) == 2
        assert metrics.get_counter("requests_total", labels={"method": "POST"}) == 1


class TestGauges:
    """Тесты датчиков"""
    
    def test_set_gauge(self, metrics):
        """Установка значения gauge"""
        metrics.set_gauge("memory_usage", 75.5)
        assert metrics.get_gauge("memory_usage") == 75.5
        
        metrics.set_gauge("memory_usage", 80.2)
        assert metrics.get_gauge("memory_usage") == 80.2
    
    def test_gauge_with_labels(self, metrics):
        """Gauge с метками"""
        metrics.set_gauge("cpu_usage", 50.0, labels={"core": "0"})
        metrics.set_gauge("cpu_usage", 60.0, labels={"core": "1"})
        
        assert metrics.get_gauge("cpu_usage", labels={"core": "0"}) == 50.0
        assert metrics.get_gauge("cpu_usage", labels={"core": "1"}) == 60.0


class TestHistograms:
    """Тесты гистограмм"""
    
    def test_record_value(self, metrics):
        """Запись значений в гистограмму"""
        metrics.record_value("response_time", 100)
        metrics.record_value("response_time", 200)
        metrics.record_value("response_time", 150)
        
        stats = metrics.get_histogram_stats("response_time")
        
        assert stats["count"] == 3
        assert stats["avg"] == 150
        assert stats["min"] == 100
        assert stats["max"] == 200
    
    def test_histogram_percentiles(self, metrics):
        """Процентили в гистограмме"""
        # Записываем 100 значений от 1 to 100
        for i in range(1, 101):
            metrics.record_value("latency", float(i))
        
        stats = metrics.get_histogram_stats("latency")
        
        assert stats["count"] == 100
        # p50 должен быть около 50-51
        assert 50 <= stats["p50"] <= 51
        assert stats["p95"] >= 95
        assert stats["p99"] >= 99
    
    def test_empty_histogram(self, metrics):
        """Пустая гистограмма"""
        stats = metrics.get_histogram_stats("empty_metric")
        
        assert stats["count"] == 0
        assert stats["avg"] == 0
        assert stats["min"] == 0
        assert stats["max"] == 0


class TestTimeSeries:
    """Тесты временных рядов"""
    
    def test_get_time_series(self, metrics):
        """Получение временного ряда"""
        # Записываем несколько точек
        metrics.set_gauge("temperature", 20.0)
        time.sleep(0.1)
        metrics.set_gauge("temperature", 21.0)
        time.sleep(0.1)
        metrics.set_gauge("temperature", 22.0)
        
        series = metrics.get_time_series("temperature", hours=1)
        
        assert len(series) > 0
        # Проверяем, что данные агрегированы по минутам
        assert "timestamp" in series[0]
        assert "value" in series[0]
    
    def test_time_series_aggregation(self, metrics):
        """Агрегация временного ряда"""
        # Записываем значения
        for i in range(5):
            metrics.set_gauge("metric", float(i))
        
        series = metrics.get_time_series("metric", hours=1, aggregation="avg")
        
        # Все значения должны быть агрегированы
        assert len(series) >= 1


class TestPrometheusExport:
    """Тесты экспорта в Prometheus"""
    
    def test_export_prometheus_format(self, metrics):
        """Экспорт в формате Prometheus"""
        metrics.increment("http_requests_total")
        metrics.set_gauge("memory_bytes", 1024)
        
        output = metrics.export_prometheus()
        
        assert "http_requests_total 1" in output
        assert "memory_bytes 1024" in output
        assert "# TYPE" in output
    
    def test_export_includes_uptime(self, metrics):
        """Экспорт включает uptime"""
        output = metrics.export_prometheus()
        
        assert "padplus_uptime_seconds" in output


class TestDashboardData:
    """Тесты данных для дашборда"""
    
    def test_get_dashboard_data(self, metrics):
        """Получение данных для дашборда"""
        metrics.increment("requests")
        metrics.set_gauge("cpu", 50.0)
        
        data = metrics.get_dashboard_data()
        
        assert "uptime_seconds" in data
        assert "counters" in data
        assert "gauges" in data
        assert "histograms" in data
        assert "time_series" in data
        assert "collected_at" in data


class TestSummary:
    """Тесты сводки"""
    
    def test_get_summary(self, metrics):
        """Получение сводки"""
        metrics.increment("counter1")
        metrics.set_gauge("gauge1", 10)
        metrics.record_value("histogram1", 5)
        
        summary = metrics.get_summary()
        
        assert summary["total_counters"] >= 1
        assert summary["total_gauges"] >= 1
        assert summary["total_histograms"] >= 1
        assert "uptime_seconds" in summary


class TestTimer:
    """Тесты таймера"""
    
    def test_timer_with_labels(self, metrics):
        """Таймер с метками"""
        with timer("operation", {"method": "GET"}) as t:
            time.sleep(0.1)
        
        assert t.duration is not None
        assert t.duration >= 100  # 100ms
    
    def test_timer_without_labels(self, metrics):
        """Таймер без меток"""
        with timer("operation") as t:
            time.sleep(0.05)
        
        assert t.duration >= 50


class TestGlobalMetrics:
    """Тесты глобального MetricsCollector"""
    
    def test_get_global_instance(self, global_metrics):
        """Получение глобального экземпляра"""
        assert global_metrics is not None
        assert isinstance(global_metrics, MetricsCollector)
    
    def test_reset_global_instance(self):
        """Сброс глобального экземпляра"""
        m1 = get_metrics()
        m1.increment("test_counter", 100)
        
        reset_metrics()
        
        m2 = get_metrics()
        assert m2 is not m1  # Новый экземпляр
        assert m2.get_counter("test_counter") == 0