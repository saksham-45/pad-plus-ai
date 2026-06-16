"""
🏥 CognitiveHealthMonitor — Монитор когнитивного здоровья

Оценивает и поддерживает когнитивное состояние системы:
- Способность к рефлексии
- Скорость обучения
- Адаптивность
- Здоровье памяти
- Когерентность ответов
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json
import os
import asyncio


@dataclass
class HealthMetric:
    """Метрика здоровья"""
    name: str
    value: float  # 0.0 - 1.0
    weight: float = 1.0  # Вес в общем score
    trend: str = "stable"  # improving, declining, stable
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "weight": self.weight,
            "trend": self.trend,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class HealthIssue:
    """Проблема здоровья"""
    severity: str  # low, medium, high, critical
    category: str
    description: str
    recommendation: str
    detected_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "recommendation": self.recommendation,
            "detected_at": self.detected_at.isoformat()
        }


class CognitiveHealthMonitor:
    """
    🏥 Монитор когнитивного здоровья
    
    Оценивает когнитивные способности системы:
    - reflection_score: способность к рефлексии
    - learning_rate: скорость обучения
    - adaptation_score: адаптивность
    - memory_health: здоровье памяти
    - coherence: когерентность ответов
    - response_quality: качество ответов
    """
    
    # Пороги для определения проблем
    THRESHOLDS = {
        "critical": 0.3,
        "low": 0.5,
        "good": 0.7,
        "excellent": 0.9
    }
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "health.json"
            )
        self.data_path = data_path
        self._metrics: Dict[str, HealthMetric] = {}
        self._issues: List[HealthIssue] = []
        self._history: List[Dict] = []
        self._init_metrics()
        self._load()
    
    def _init_metrics(self):
        """Инициализирует метрики"""
        default_metrics = [
            ("reflection_score", 0.8, 1.0),
            ("learning_rate", 0.7, 0.9),
            ("adaptation_score", 0.75, 0.8),
            ("memory_health", 0.85, 1.0),
            ("coherence", 0.9, 0.9),
            ("response_quality", 0.8, 0.95),
            ("safety_compliance", 1.0, 1.0),
            ("emotional_balance", 0.7, 0.7)
        ]
        
        for name, value, weight in default_metrics:
            self._metrics[name] = HealthMetric(
                name=name,
                value=value,
                weight=weight
            )
    
    def _load(self):
        """Загружает состояние из файла"""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for item in data.get('metrics', []):
                        self._metrics[item['name']] = HealthMetric(
                            name=item['name'],
                            value=item['value'],
                            weight=item.get('weight', 1.0),
                            trend=item.get('trend', 'stable'),
                            last_updated=datetime.fromisoformat(
                                item['last_updated']
                            ) if item.get('last_updated') else datetime.now()
                        )
                    
                    for item in data.get('issues', []):
                        self._issues.append(HealthIssue(
                            severity=item['severity'],
                            category=item['category'],
                            description=item['description'],
                            recommendation=item['recommendation'],
                            detected_at=datetime.fromisoformat(
                                item['detected_at']
                            ) if item.get('detected_at') else datetime.now()
                        ))
                    
                    self._history = data.get('history', [])
            except Exception as e:
                print(f"Ошибка загрузки здоровья: {e}")
    
    def _save(self):
        """Сохраняет состояние в файл"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        data = {
            "updated": datetime.now().isoformat(),
            "overall_score": self.get_overall_score(),
            "metrics": [m.to_dict() for m in self._metrics.values()],
            "issues": [i.to_dict() for i in self._issues[-50:]],  # Последние 50
            "history": self._history[-100:]  # Последние 100 записей
        }
        
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_metric(self, name: str) -> Optional[HealthMetric]:
        """Получает метрику по имени"""
        return self._metrics.get(name)
    
    def update_metric(self, name: str, value: float, 
                      reason: str = None) -> bool:
        """Обновляет значение метрики"""
        if name not in self._metrics:
            return False
        
        metric = self._metrics[name]
        old_value = metric.value
        
        # Ограничиваем значение
        value = max(0.0, min(1.0, value))
        
        # Определяем тренд
        if value > old_value + 0.05:
            metric.trend = "improving"
        elif value < old_value - 0.05:
            metric.trend = "declining"
        else:
            metric.trend = "stable"
        
        metric.value = value
        metric.last_updated = datetime.now()
        
        # Проверяем на проблемы
        self._check_threshold(name, value)
        
        # Добавляем в историю
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "metric": name,
            "old_value": old_value,
            "new_value": value,
            "reason": reason
        })
        
        self._save()
        return True
    
    def _check_threshold(self, metric_name: str, value: float):
        """Проверяет пороговые значения"""
        if value < self.THRESHOLDS["critical"]:
            self._add_issue(
                severity="critical",
                category=metric_name,
                description=f"Критически низкий уровень: {metric_name} = {value:.2f}",
                recommendation=f"Требуется немедленное внимание к {metric_name}"
            )
        elif value < self.THRESHOLDS["low"]:
            self._add_issue(
                severity="high",
                category=metric_name,
                description=f"Низкий уровень: {metric_name} = {value:.2f}",
                recommendation=f"Рекомендуется улучшить {metric_name}"
            )
    
    def _add_issue(self, severity: str, category: str,
                   description: str, recommendation: str):
        """Добавляет проблему"""
        # Проверяем, нет ли уже такой проблемы
        for issue in self._issues:
            if (issue.category == category and 
                issue.severity == severity and
                issue.description == description):
                return
        
        issue = HealthIssue(
            severity=severity,
            category=category,
            description=description,
            recommendation=recommendation
        )
        self._issues.append(issue)
    
    def get_overall_score(self) -> float:
        """Вычисляет общий score здоровья"""
        if not self._metrics:
            return 0.0
        
        total_weight = sum(m.weight for m in self._metrics.values())
        weighted_sum = sum(m.value * m.weight for m in self._metrics.values())
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def assess_health(self) -> Dict[str, Any]:
        """Полная оценка здоровья системы"""
        overall = self.get_overall_score()
        
        # Определяем статус
        if overall >= self.THRESHOLDS["excellent"]:
            status = "excellent"
            status_emoji = "💚"
        elif overall >= self.THRESHOLDS["good"]:
            status = "good"
            status_emoji = "💚"
        elif overall >= self.THRESHOLDS["low"]:
            status = "fair"
            status_emoji = "💛"
        elif overall >= self.THRESHOLDS["critical"]:
            status = "poor"
            status_emoji = "🧡"
        else:
            status = "critical"
            status_emoji = "❤️"
        
        return {
            "overall_score": round(overall, 3),
            "status": status,
            "status_emoji": status_emoji,
            "metrics": {k: v.to_dict() for k, v in self._metrics.items()},
            "active_issues": len([i for i in self._issues 
                                if i.severity in ['high', 'critical']]),
            "trends": self._get_trends_summary()
        }
    
    def _get_trends_summary(self) -> Dict[str, int]:
        """Сводка трендов"""
        trends = {"improving": 0, "stable": 0, "declining": 0}
        for metric in self._metrics.values():
            trends[metric.trend] = trends.get(metric.trend, 0) + 1
        return trends
    
    def detect_issues(self) -> List[HealthIssue]:
        """Выявляет проблемы в работе системы"""
        active_issues = []
        
        for metric in self._metrics.values():
            if metric.value < self.THRESHOLDS["low"]:
                active_issues.append(HealthIssue(
                    severity="high" if metric.value < self.THRESHOLDS["critical"] 
                    else "medium",
                    category=metric.name,
                    description=f"Низкий показатель: {metric.name} = {metric.value:.2f}",
                    recommendation=self._get_recommendation(metric.name),
                    detected_at=datetime.now()
                ))
        
        return active_issues
    
    def _get_recommendation(self, metric_name: str) -> str:
        """Возвращает рекомендацию для метрики"""
        recommendations = {
            "reflection_score": "Запустить процесс саморефлексии",
            "learning_rate": "Увеличить частоту обучения на новых данных",
            "adaptation_score": "Проверить адаптивные механизмы",
            "memory_health": "Запустить гигиену памяти",
            "coherence": "Проверить truth loop и валидацию",
            "response_quality": "Проанализировать недавние диалоги",
            "safety_compliance": "Проверить safety layer",
            "emotional_balance": "Скорректировать PAD модель"
        }
        return recommendations.get(metric_name, "Требуется внимание")
    
    def generate_recommendations(self) -> List[str]:
        """Генерирует рекомендации по улучшению"""
        recommendations = []
        
        for metric in self._metrics.values():
            if metric.value < self.THRESHOLDS["good"]:
                rec = self._get_recommendation(metric.name)
                recommendations.append(f"[{metric.name}] {rec}")
        
        return recommendations
    
    def record_event(self, event_type: str, impact: float):
        """Записывает событие, влияющее на здоровье"""
        # События могут влиять на конкретные метрики
        impacts = {
            "successful_reflection": ("reflection_score", 0.05),
            "failed_reflection": ("reflection_score", -0.05),
            "learned_fact": ("learning_rate", 0.03),
            "contradiction_found": ("coherence", -0.02),
            "safety_violation": ("safety_compliance", -0.1),
            "good_dialog": ("response_quality", 0.02),
            "memory_cleanup": ("memory_health", 0.05),
            "adaptation_success": ("adaptation_score", 0.04)
        }
        
        if event_type in impacts:
            metric_name, delta = impacts[event_type]
            if metric_name in self._metrics:
                new_value = self._metrics[metric_name].value + delta * impact
                self.update_metric(metric_name, new_value, event_type)
    
    def get_health_report(self) -> str:
        """Генерирует текстовый отчёт о здоровье"""
        health = self.assess_health()
        
        lines = [
            f"# 🏥 Отчёт о когнитивном здоровье",
            f"",
            f"**Общий_score:** {health['overall_score']:.2f} {health['status_emoji']}",
            f"**Статус:** {health['status']}",
            f"",
            f"## Метрики:",
            ""
        ]
        
        for name, metric in health['metrics'].items():
            trend_icon = "📈" if metric['trend'] == 'improving' else \
                        "📉" if metric['trend'] == 'declining' else "➡️"
            lines.append(f"- {name}: {metric['value']:.2f} {trend_icon}")
        
        issues = self.detect_issues()
        if issues:
            lines.extend([
                "",
                "## ⚠️ Проблемы:",
                ""
            ])
            for issue in issues[:5]:  # Топ 5
                lines.append(f"- [{issue.severity}] {issue.description}")
        
        recommendations = self.generate_recommendations()
        if recommendations:
            lines.extend([
                "",
                "## 💡 Рекомендации:",
                ""
            ])
            for rec in recommendations[:5]:
                lines.append(f"- {rec}")
        
        return "\n".join(lines)
    
    def clear_resolved_issues(self):
        """Очищает решённые проблемы"""
        # Удаляем проблемы старше 24 часов
        cutoff = datetime.now() - timedelta(hours=24)
        self._issues = [i for i in self._issues 
                       if i.detected_at > cutoff or i.severity == "critical"]
        self._save()
    
    def reset(self):
        """Сбрасывает состояние монитора"""
        self._init_metrics()
        self._issues = []
        self._history = []
        self._save()
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Возвращает историю изменений"""
        return self._history[-limit:]

    # === ИСПРАВЛЕНИЕ 7: Health Checks для сервисов ===

    async def check_redis(self) -> bool:
        """Проверяет подключение к Redis"""
        try:
            from core.cache_manager import get_cache_manager
            cache = get_cache_manager()
            if cache and hasattr(cache, 'redis'):
                await cache.redis.ping()
                return True
            return False
        except Exception:
            return False

    async def check_supabase(self) -> bool:
        """Проверяет подключение к Supabase"""
        try:
            from core.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                # Простая проверка подключения
                await asyncio.get_event_loop().run_in_executor(None, lambda: True)
                return True
            return False
        except Exception:
            return False

    async def check_llm(self) -> bool:
        """Проверяет доступность LLM сервиса"""
        try:
            from runtime.litellm_service import get_litellm_service
            service = get_litellm_service()
            # Проверяем, что Circuit Breaker не открыт
            if hasattr(service, '_circuit_breaker'):
                return service._circuit_breaker.is_closed() or service._circuit_breaker.is_half_open()
            return True
        except Exception:
            return False

    async def run_health_check(self):
        """Запускает полную проверку всех сервисов"""
        redis_ok = await self.check_redis()
        supabase_ok = await self.check_supabase()
        llm_ok = await self.check_llm()

        # Обновляем метрики
        self.update_metric('cache_health', 1.0 if redis_ok else 0.0, 'health_check')
        self.update_metric('database_health', 1.0 if supabase_ok else 0.0, 'health_check')
        self.update_metric('llm_health', 1.0 if llm_ok else 0.0, 'health_check')

        # Проверяем на критичные проблемы
        if not llm_ok:
            self._add_issue(
                severity="critical",
                category="llm",
                description="LLM сервис недоступен",
                recommendation="Проверьте API ключи и Circuit Breaker"
            )

    async def start_periodic_health_check(self, interval: int = 30):
        """Запускает периодическую проверку здоровья"""
        import asyncio
        
        while True:
            await self.run_health_check()
            await asyncio.sleep(interval)


# Глобальный экземпляр
_health_monitor: Optional[CognitiveHealthMonitor] = None


def get_health_monitor() -> CognitiveHealthMonitor:
    """Возвращает глобальный монитор здоровья"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = CognitiveHealthMonitor()
    return _health_monitor