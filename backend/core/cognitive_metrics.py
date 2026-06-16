"""
📊 Cognitive Metrics Dashboard

Мониторинг когнитивных функций в реальном времени:
- Memory utilization
- Emotion stability
- Autonomous activity
- Pipeline performance
- Health trends

API для получения метрик и генерации отчётов.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import os


@dataclass
class MetricSnapshot:
    """Снимок метрики на момент времени"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class CognitiveReport:
    """Отчёт о когнитивном здоровье"""
    overall_score: float
    status: str  # excellent, good, fair, poor, critical
    metrics: Dict[str, float]
    trends: Dict[str, str]  # improving, stable, declining
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "status": self.status,
            "status_emoji": {
                "excellent": "🤩",
                "good": "😊",
                "fair": "😐",
                "poor": "😟",
                "critical": "🚨"
            }.get(self.status, "❓"),
            "metrics": self.metrics,
            "trends": self.trends,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat()
        }


class CognitiveMetricsDashboard:
    """
    📊 Дашборд когнитивных метрик

    Отслеживает:
    1. Memory Utilization — использование памяти
    2. Emotion Stability — стабильность эмоций
    3. Autonomous Activity — активность автономности
    4. Pipeline Performance — производительность pipeline
    5. Health Trends — тренды здоровья
    """

    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "cognitive_metrics.json"
            )
        self.data_path = data_path
        self._history: List[Dict] = []
        self._alerts: List[Dict] = []
        self._load()

    def _load(self):
        """Загружает историю из файла"""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._history = data.get('history', [])
                    self._alerts = data.get('alerts', [])
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")

    def _save(self):
        """Сохраняет историю в файл"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        data = {
            "updated": datetime.now().isoformat(),
            "history": self._history[-1000:],  # Последние 1000 записей
            "alerts": self._alerts[-100:]  # Последние 100 алертов
        }
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ========================================================================
    # MEMORY METRICS
    # ========================================================================

    def get_memory_utilization(self, rag_memory=None) -> Dict[str, Any]:
        """
        Использование памяти

        Returns:
            {
                "rag_usage": 0.45,  # % от лимита
                "episodic_count": 123,
                "semantic_count": 456,
                "facts_count": 789,
                "consolidation_pending": 5
            }
        """
        metrics = {
            "rag_usage": 0.0,
            "episodic_count": 0,
            "semantic_count": 0,
            "facts_count": 0,
            "consolidation_pending": 0
        }

        if rag_memory:
            try:
                stats = rag_memory.get_stats()
                # RAG лимит = 10000 элементов
                total = stats.get('total_dialogs', 0)
                metrics["rag_usage"] = min(1.0, total / 10000)
                metrics["episodic_count"] = total
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")

        return metrics

    # ========================================================================
    # EMOTION METRICS
    # ========================================================================

    def get_emotion_stability(self, emotion_model=None) -> Dict[str, Any]:
        """
        Стабильность эмоций

        Returns:
            {
                "stability_index": 0.85,  # 1.0 = идеально стабильно
                "current_state": {...},
                "variance": 0.15,
                "mood": "neutral"
            }
        """
        metrics = {
            "stability_index": 1.0,
            "current_state": {},
            "variance": 0.0,
            "mood": "neutral"
        }

        if emotion_model:
            try:
                state = emotion_model.get_state()
                state_dict = state.to_dict()

                metrics["current_state"] = {
                    "pleasure": state.pleasure,
                    "arousal": state.arousal,
                    "dominance": state.dominance,
                    "curiosity": state.curiosity,
                    "confidence": state.confidence
                }

                # Вычисляем стабильность (насколько близко к нейтральному)
                neutral = {
                    "pleasure": 0.0,
                    "arousal": 0.0,
                    "dominance": 0.0,
                    "curiosity": 0.5,
                    "confidence": 0.5
                }

                variance = sum(
                    abs(state_dict.get(k, 0) - v)
                    for k, v in neutral.items()
                ) / len(neutral)

                metrics["variance"] = variance
                metrics["stability_index"] = 1.0 - variance

                # Определяем настроение
                if state.pleasure > 0.3:
                    metrics["mood"] = "positive"
                elif state.pleasure < -0.3:
                    metrics["mood"] = "negative"
                else:
                    metrics["mood"] = "neutral"

            except Exception as e:
                logger.warning(f"{__name__} error: {e}")

        return metrics

    # ========================================================================
    # AUTONOMY METRICS
    # ========================================================================

    def get_autonomous_activity(self, planner=None) -> Dict[str, Any]:
        """
        Активность автономности

        Returns:
            {
                "active_tasks": 3,
                "completed_today": 12,
                "reflection_count": 5,
                "questions_generated": 8,
                "activity_level": 0.6
            }
        """
        metrics = {
            "active_tasks": 0,
            "completed_today": 0,
            "reflection_count": 0,
            "questions_generated": 0,
            "activity_level": 0.0
        }

        if planner:
            try:
                tasks = planner.get_pending_tasks()
                metrics["active_tasks"] = len(tasks)

                # Статистика за сегодня
                stats = planner.get_status()
                metrics["completed_today"] = stats.get('completed_today', 0)
                metrics["activity_level"] = min(1.0, metrics["active_tasks"] / 10)

            except Exception as e:
                logger.warning(f"{__name__} error: {e}")

        return metrics

    # ========================================================================
    # PIPELINE METRICS
    # ========================================================================

    def get_pipeline_performance(self) -> Dict[str, Any]:
        """
        Производительность pipeline

        Returns:
            {
                "avg_response_time": 1.5,  # секунды
                "requests_per_minute": 12,
                "error_rate": 0.02,
                "success_rate": 0.98,
                "efficiency": 0.95
            }
        """
        # Заглушка — в реальности брать из метрик pipeline
        return {
            "avg_response_time": 1.5,
            "requests_per_minute": 12,
            "error_rate": 0.02,
            "success_rate": 0.98,
            "efficiency": 0.95
        }

    # ========================================================================
    # HEALTH TRENDS
    # ========================================================================

    def get_health_trends(self, health_monitor=None) -> Dict[str, Any]:
        """
        Тренды здоровья

        Returns:
            {
                "overall_score": 0.85,
                "trends": {
                    "memory": "stable",
                    "emotion": "improving",
                    "autonomy": "declining"
                },
                "issues": []
            }
        """
        trends = {
            "overall_score": 0.8,
            "trends": {},
            "issues": []
        }

        if health_monitor:
            try:
                health = health_monitor.assess_health()
                trends["overall_score"] = health.get('overall_score', 0.8)
                trends["trends"] = health.get('trends', {})
                trends["issues"] = health.get('active_issues', 0)
            except Exception as e:
                logger.warning(f"{__name__} error: {e}")

        return trends

    # ========================================================================
    # COMPREHENSIVE REPORT
    # ========================================================================

    def generate_report(
        self,
        rag_memory=None,
        emotion_model=None,
        planner=None,
        health_monitor=None
    ) -> CognitiveReport:
        """
        Генерирует полный отчёт о когнитивном здоровье

        Returns:
            CognitiveReport с метриками, трендами и рекомендациями
        """
        # Собираем все метрики
        memory = self.get_memory_utilization(rag_memory)
        emotion = self.get_emotion_stability(emotion_model)
        autonomy = self.get_autonomous_activity(planner)
        pipeline = self.get_pipeline_performance()
        health = self.get_health_trends(health_monitor)

        # Вычисляем общий score
        scores = [
            memory["rag_usage"],  # Чем больше, тем лучше (до 1.0)
            emotion["stability_index"],
            1.0 - autonomy["activity_level"],  # Инвертируем (меньше задач = лучше)
            pipeline["efficiency"],
            health["overall_score"]
        ]

        overall_score = sum(scores) / len(scores)

        # Определяем статус
        if overall_score >= 0.9:
            status = "excellent"
        elif overall_score >= 0.75:
            status = "good"
        elif overall_score >= 0.5:
            status = "fair"
        elif overall_score >= 0.3:
            status = "poor"
        else:
            status = "critical"

        # Определяем тренды
        trends = {
            "memory": "stable",
            "emotion": emotion["stability_index"] > 0.8 and "stable" or "declining",
            "autonomy": autonomy["activity_level"] > 0.5 and "active" or "stable",
            "pipeline": "stable"
        }

        # Генерируем рекомендации
        recommendations = []

        if memory["rag_usage"] > 0.9:
            recommendations.append("⚠️ RAG память заполнена на 90% — рассмотрите очистку")

        if emotion["stability_index"] < 0.7:
            recommendations.append("🎭 Эмоциональная нестабильность — рекомендуется период покоя")

        if autonomy["activity_level"] > 0.8:
            recommendations.append("🤖 Высокая автономная активность — проверьте задачи")

        if pipeline["error_rate"] > 0.05:
            recommendations.append("❌ Высокий уровень ошибок — проверьте логи")

        if health["overall_score"] < 0.5:
            recommendations.append("🏥 Низкий показатель здоровья — требуется диагностика")

        if not recommendations:
            recommendations.append("✅ Все системы работают нормально")

        # Создаём отчёт
        report = CognitiveReport(
            overall_score=round(overall_score, 3),
            status=status,
            metrics={
                "memory": memory,
                "emotion": emotion,
                "autonomy": autonomy,
                "pipeline": pipeline,
                "health": health
            },
            trends=trends,
            recommendations=recommendations
        )

        # Сохраняем в историю
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "report": report.to_dict()
        })
        self._save()

        return report

    # ========================================================================
    # ALERTS
    # ========================================================================

    def check_alerts(self, report: CognitiveReport) -> List[Dict]:
        """Проверяет метрики на алерты"""
        alerts = []

        # Critical health
        if report.overall_score < 0.3:
            alerts.append({
                "level": "critical",
                "metric": "overall_health",
                "message": f"Критическое когнитивное здоровье: {report.overall_score:.2f}",
                "timestamp": datetime.now().isoformat()
            })

        # High memory usage
        if report.metrics["memory"]["rag_usage"] > 0.95:
            alerts.append({
                "level": "warning",
                "metric": "memory_usage",
                "message": "RAG память заполнена на 95%+",
                "timestamp": datetime.now().isoformat()
            })

        # Emotion instability
        if report.metrics["emotion"]["stability_index"] < 0.5:
            alerts.append({
                "level": "warning",
                "metric": "emotion_stability",
                "message": "Эмоциональная нестабильность",
                "timestamp": datetime.now().isoformat()
            })

        self._alerts.extend(alerts)
        self._save()

        return alerts


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_dashboard: Optional[CognitiveMetricsDashboard] = None


def get_cognitive_dashboard() -> CognitiveMetricsDashboard:
    """Возвращает глобальный дашборд метрик"""
    global _dashboard
    if _dashboard is None:
        _dashboard = CognitiveMetricsDashboard()
    return _dashboard
