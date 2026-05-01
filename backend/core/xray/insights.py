"""
📊 Insights — Аналитика и извлечение выводов

Анализирует трассировки и когнитивные состояния для:
- Обнаружения аномалий
- Выявления узких мест
- Агрегации статистики
- Генерации рекомендаций
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger("padplus.xray")


@dataclass
class Anomaly:
    """Аномалия в работе системы"""
    type: str  # "slow_stage", "low_confidence", "high_load", "failure"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    trace_id: Optional[str]
    span_id: Optional[str]
    value: float
    threshold: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity,
            "description": self.description,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "value": round(self.value, 3),
            "threshold": round(self.threshold, 3),
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class StageStats:
    """Статистика стадии пайплайна"""
    name: str
    count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = float('-inf')
    durations: List[float] = field(default_factory=list)
    errors: int = 0
    
    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.count if self.count > 0 else 0
    
    @property
    def p50_duration_ms(self) -> float:
        if not self.durations:
            return 0
        return statistics.median(self.durations)
    
    @property
    def p95_duration_ms(self) -> float:
        if not self.durations:
            return 0
        sorted_d = sorted(self.durations)
        idx = int(len(sorted_d) * 0.95)
        return sorted_d[min(idx, len(sorted_d) - 1)]
    
    @property
    def error_rate(self) -> float:
        return self.errors / self.count if self.count > 0 else 0
    
    def add_sample(self, duration_ms: float, success: bool = True):
        self.count += 1
        self.total_duration_ms += duration_ms
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        self.durations.append(duration_ms)
        if not success:
            self.errors += 1
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "count": self.count,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "p50_duration_ms": round(self.p50_duration_ms, 2),
            "p95_duration_ms": round(self.p95_duration_ms, 2),
            "min_duration_ms": round(self.min_duration_ms, 2) if self.min_duration_ms != float('inf') else 0,
            "max_duration_ms": round(self.max_duration_ms, 2) if self.max_duration_ms != float('-inf') else 0,
            "error_rate": round(self.error_rate, 3),
            "total_errors": self.errors
        }


class InsightsEngine:
    """
    📊 Движок аналитики
    
    Анализирует трассировки и выявляет:
    - Аномалии производительности
    - Узкие места
    - Паттерны ошибок
    - Рекомендации по оптимизации
    """
    
    def __init__(self):
        # Статистика по стадиям
        self._stage_stats: Dict[str, StageStats] = {}
        
        # Аномалии
        self._anomalies: List[Anomaly] = []
        self._max_anomalies = 100
        
        # Пороги для обнаружения аномалий
        self._thresholds = {
            "slow_stage_ms": 2000,      # Стадия дольше 2 секунд
            "low_confidence": 0.4,       # Уверенность ниже 40%
            "high_cognitive_load": 0.8,  # Нагрузка выше 80%
            "high_error_rate": 0.1,      # Ошибки выше 10%
            "total_timeout_ms": 10000,   # Общий таймаут 10 секунд
        }
        
        # История для трендов
        self._confidence_history: List[float] = []
        self._load_history: List[float] = []
        self._latency_history: List[float] = []
        
        logger.info("✅ InsightsEngine инициализирован")
    
    def record_trace(self, trace_data: Dict[str, Any]):
        """Записывает трассировку для анализа"""
        # Анализируем спаны
        spans = trace_data.get("spans", {})
        for span_id, span_data in spans.items():
            stage_name = span_data.get("name", "unknown")
            duration_ms = span_data.get("duration_ms", 0)
            status = span_data.get("status", "ok")
            
            # Обновляем статистику стадии
            if stage_name not in self._stage_stats:
                self._stage_stats[stage_name] = StageStats(name=stage_name)
            
            self._stage_stats[stage_name].add_sample(
                duration_ms,
                status == "ok"
            )
            
            # Проверяем на аномалии
            self._check_anomalies(span_data, trace_data)
        
        # Записываем метрики в историю
        metrics = trace_data.get("metrics", {})
        if "confidence" in metrics:
            self._confidence_history.append(metrics["confidence"])
        if "cognitive_load" in metrics:
            self._load_history.append(metrics["cognitive_load"])
        
        total_duration = trace_data.get("total_duration_ms", 0)
        if total_duration > 0:
            self._latency_history.append(total_duration)
        
        # Ограничиваем историю
        max_history = 1000
        self._confidence_history = self._confidence_history[-max_history:]
        self._load_history = self._load_history[-max_history:]
        self._latency_history = self._latency_history[-max_history:]
    
    def _check_anomalies(self, span_data: Dict, trace_data: Dict):
        """Проверяет данные на аномалии"""
        trace_id = trace_data.get("trace_id")
        span_id = span_data.get("span_id")
        stage_name = span_data.get("name", "unknown")
        duration_ms = span_data.get("duration_ms", 0)
        status = span_data.get("status", "ok")
        
        # Аномалия: медленная стадия
        if duration_ms > self._thresholds["slow_stage_ms"]:
            self._add_anomaly(Anomaly(
                type="slow_stage",
                severity="medium",
                description=f"Стадия '{stage_name}' выполнилась за {duration_ms:.0f}ms (порог: {self._thresholds['slow_stage_ms']}ms)",
                trace_id=trace_id,
                span_id=span_id,
                value=duration_ms,
                threshold=self._thresholds["slow_stage_ms"],
                metadata={"stage": stage_name}
            ))
        
        # Аномалия: ошибка
        if status == "error":
            self._add_anomaly(Anomaly(
                type="failure",
                severity="high",
                description=f"Ошибка на стадии '{stage_name}'",
                trace_id=trace_id,
                span_id=span_id,
                value=1.0,
                threshold=0.0,
                metadata={"stage": stage_name, "status": status}
            ))
        
        # Проверяем метрики
        metrics = trace_data.get("metrics", {})
        
        # Аномалия: низкая уверенность
        confidence = metrics.get("confidence", 1.0)
        if confidence < self._thresholds["low_confidence"]:
            self._add_anomaly(Anomaly(
                type="low_confidence",
                severity="medium",
                description=f"Низкая уверенность: {confidence:.2f} (порог: {self._thresholds['low_confidence']})",
                trace_id=trace_id,
                span_id=span_id,
                value=confidence,
                threshold=self._thresholds["low_confidence"],
                metadata={"metrics": metrics}
            ))
        
        # Аномалия: высокая когнитивная нагрузка
        cognitive_load = metrics.get("cognitive_load", 0.0)
        if cognitive_load > self._thresholds["high_cognitive_load"]:
            self._add_anomaly(Anomaly(
                type="high_load",
                severity="high",
                description=f"Высокая когнитивная нагрузка: {cognitive_load:.2f} (порог: {self._thresholds['high_cognitive_load']})",
                trace_id=trace_id,
                span_id=span_id,
                value=cognitive_load,
                threshold=self._thresholds["high_cognitive_load"],
                metadata={"metrics": metrics}
            ))
        
        # Аномалия: общий таймаут
        total_duration = trace_data.get("total_duration_ms", 0)
        if total_duration > self._thresholds["total_timeout_ms"]:
            self._add_anomaly(Anomaly(
                type="timeout",
                severity="critical",
                description=f"Общее время выполнения превысило таймаут: {total_duration:.0f}ms",
                trace_id=trace_id,
                span_id=None,
                value=total_duration,
                threshold=self._thresholds["total_timeout_ms"],
                metadata={"total_duration_ms": total_duration}
            ))
    
    def _add_anomaly(self, anomaly: Anomaly):
        """Добавляет аномалию"""
        self._anomalies.append(anomaly)
        
        # Ограничиваем количество
        if len(self._anomalies) > self._max_anomalies:
            self._anomalies = self._anomalies[-self._max_anomalies:]
        
        logger.warning(f"🚨 Anomaly detected: {anomaly.type} — {anomaly.description}")
    
    def get_stage_stats(self) -> Dict[str, Dict]:
        """Возвращает статистику по стадиям"""
        return {
            name: stats.to_dict() 
            for name, stats in self._stage_stats.items()
        }
    
    def get_anomalies(
        self, 
        limit: int = 20,
        severity: str = None,
        type_filter: str = None
    ) -> List[Dict]:
        """Возвращает аномалии с фильтрацией"""
        anomalies = self._anomalies
        
        if severity:
            anomalies = [a for a in anomalies if a.severity == severity]
        if type_filter:
            anomalies = [a for a in anomalies if a.type == type_filter]
        
        # Сортируем по времени (новые первые)
        anomalies.sort(key=lambda a: a.timestamp, reverse=True)
        
        return [a.to_dict() for a in anomalies[:limit]]
    
    def get_trends(self) -> Dict[str, Any]:
        """Возвращает тренды"""
        def calculate_trend(history: List[float]) -> Dict:
            if len(history) < 2:
                return {"current": 0, "trend": "stable", "change": 0}
            
            recent = history[-10:] if len(history) >= 10 else history
            older = history[:-10] if len(history) >= 10 else history[:len(history)//2]
            
            if not older or not recent:
                return {"current": 0, "trend": "stable", "change": 0}
            
            current_avg = statistics.mean(recent)
            older_avg = statistics.mean(older)
            
            change = current_avg - older_avg
            change_pct = (change / older_avg * 100) if older_avg > 0 else 0
            
            if abs(change_pct) < 5:
                trend = "stable"
            elif change > 0:
                trend = "increasing"
            else:
                trend = "decreasing"
            
            return {
                "current": round(current_avg, 3),
                "trend": trend,
                "change": round(change, 3),
                "change_percent": round(change_pct, 1)
            }
        
        return {
            "confidence": calculate_trend(self._confidence_history),
            "cognitive_load": calculate_trend(self._load_history),
            "latency": calculate_trend(self._latency_history)
        }
    
    def get_recommendations(self) -> List[Dict]:
        """Генерирует рекомендации на основе анализа"""
        recommendations = []
        
        # Проверяем статистику стадий
        for name, stats in self._stage_stats.items():
            # Медленные стадии
            if stats.avg_duration_ms > 1000:
                recommendations.append({
                    "type": "performance",
                    "priority": "high",
                    "message": f"Стадия '{name}' медленная (среднее: {stats.avg_duration_ms:.0f}ms). "
                              f"Рассмотрите оптимизацию или кэширование.",
                    "stage": name,
                    "metric": "avg_duration_ms",
                    "value": round(stats.avg_duration_ms, 0)
                })
            
            # Высокий error rate
            if stats.error_rate > 0.05:
                recommendations.append({
                    "type": "reliability",
                    "priority": "critical",
                    "message": f"Стадия '{name}' имеет высокий rate ошибок ({stats.error_rate:.1%}). "
                              f"Требуется investigation.",
                    "stage": name,
                    "metric": "error_rate",
                    "value": round(stats.error_rate, 3)
                })
        
        # Проверяем тренды
        trends = self.get_trends()
        
        if trends["confidence"]["trend"] == "decreasing":
            recommendations.append({
                "type": "quality",
                "priority": "medium",
                "message": f"Уверенность системы снижается ({trends['confidence']['change_percent']:.1f}%). "
                          f"Проверьте качество источников данных.",
                "metric": "confidence_trend",
                "value": trends["confidence"]["current"]
            })
        
        if trends["latency"]["trend"] == "increasing":
            recommendations.append({
                "type": "performance",
                "priority": "medium",
                "message": f"Задержка растёт ({trends['latency']['change_percent']:.1f}%). "
                          f"Возможна деградация производительности.",
                "metric": "latency_trend",
                "value": trends["latency"]["current"]
            })
        
        return recommendations
    
    def get_summary(self) -> Dict[str, Any]:
        """Возвращает сводную аналитику"""
        return {
            "stage_stats": self.get_stage_stats(),
            "recent_anomalies": self.get_anomalies(limit=10),
            "anomaly_count": len(self._anomalies),
            "trends": self.get_trends(),
            "recommendations": self.get_recommendations()
        }
    
    def clear(self):
        """Очищает все данные"""
        self._stage_stats.clear()
        self._anomalies.clear()
        self._confidence_history.clear()
        self._load_history.clear()
        self._latency_history.clear()


# Глобальный экземпляр
_insights_engine: Optional[InsightsEngine] = None


def get_insights_engine() -> InsightsEngine:
    """Возвращает глобальный движок аналитики"""
    global _insights_engine
    if _insights_engine is None:
        _insights_engine = InsightsEngine()
    return _insights_engine