"""
🧠 MetaLearner — Система мета-обучения X-Ray Brain

Анализирует успешность принятых решений и адаптирует стратегию:
- Записывает результаты каждого запроса
- Считает статистику по стратегиям
- Рекомендует смену стратегии при низкой успешности
- Сохраняет/загружает статистику

Архитектура:
    Decision → Execution → Result → MetaLearner.record() → Stats → Brain.decide()
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
import os
import time
import logging

logger = logging.getLogger("padplus.xray.meta")


@dataclass
class StrategyStats:
    """
    Статистика по конкретной стратегии
    
    Отслеживает:
    - success: количество успешных выполнений
    - fail: количество неудач
    - total_confidence: сумма уверенностей
    - count: общее количество использований
    - last_used: время последнего использования
    """
    success: int = 0
    fail: int = 0
    total_confidence: float = 0.0
    count: int = 0
    last_used: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        """Процент успешных выполнений"""
        if self.count == 0:
            return 0.0
        return self.success / self.count
    
    @property
    def avg_confidence(self) -> float:
        """Средняя уверенность"""
        if self.count == 0:
            return 0.0
        return self.total_confidence / self.count
    
    @property
    def fail_rate(self) -> float:
        """Процент неудач"""
        if self.count == 0:
            return 0.0
        return self.fail / self.count
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            "success": self.success,
            "fail": self.fail,
            "count": self.count,
            "success_rate": round(self.success_rate, 3),
            "fail_rate": round(self.fail_rate, 3),
            "avg_confidence": round(self.avg_confidence, 3),
            "last_used": self.last_used
        }


class MetaLearner:
    """
    🧠 MetaLearner — система мета-обучения
    
    Анализирует успешность стратегий и адаптирует решения:
    - Записывает результат каждого запроса
    - Считает success/fail rate по стратегиям
    - Рекомендует смену стратегии при низкой успешности
    - Сохраняет статистику в файл
    
    Пример использования:
        learner = get_meta_learner()
        learner.record_outcome("reasoning", {"success": True, "confidence": 0.8})
        learner.record_outcome("reasoning", {"success": False, "confidence": 0.3})
        
        # После нескольких запросов
        adjustment = learner.should_adjust_strategy("reasoning")
        if adjustment:
            print(f"Рекомендуется сменить стратегию на: {adjustment}")
    """
    
    # Все возможные стратегии
    ALL_STRATEGIES = [
        "simple", "retrieval", "reasoning", 
        "creative", "reflective", "learning"
    ]
    
    # Пороги для принятия решений
    MIN_SAMPLES_FOR_ADJUSTMENT = 5  # Минимум примеров для рекомендации
    LOW_SUCCESS_THRESHOLD = 0.5      # Порог низкой успешности
    HIGH_FAIL_THRESHOLD = 0.7        # Порог высокой неудачи
    
    def __init__(self, data_path: str = None):
        """
        Инициализация MetaLearner
        
        Args:
            data_path: путь к файлу сохранения статистики
        """
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "data", "xray_meta_learner.json"
            )
        self.data_path = data_path
        
        # Статистика по стратегиям
        self.stats: Dict[str, StrategyStats] = {
            strategy: StrategyStats() 
            for strategy in self.ALL_STRATEGIES
        }
        
        # История последних решений (для анализа паттернов)
        self._recent_decisions: List[Dict] = []
        self._max_recent = 50
        
        # Загружаем сохранённую статистику
        self._load()
        
        logger.info("🧠 MetaLearner инициализирован")
    
    def record_outcome(self, strategy: str, result: dict):
        """
        Записывает результат выполнения запроса
        
        Args:
            strategy: использованная стратегия
            result: результат выполнения (PipelineResult.to_dict())
        """
        if strategy not in self.stats:
            logger.warning(f"Unknown strategy: {strategy}")
            return
        
        stats = self.stats[strategy]
        stats.count += 1
        stats.last_used = time.time()
        
        # Записываем успех/неудачу
        if result.get('success', False):
            stats.success += 1
        else:
            stats.fail += 1
        
        # Записываем уверенность
        confidence = result.get('confidence', 0.5)
        stats.total_confidence += confidence
        
        # Сохраняем в историю
        self._recent_decisions.append({
            "strategy": strategy,
            "success": result.get('success', False),
            "confidence": confidence,
            "timestamp": time.time()
        })
        
        # Очищаем старую историю
        if len(self._recent_decisions) > self._max_recent:
            self._recent_decisions = self._recent_decisions[-self._max_recent:]
        
        # Сохраняем статистику
        self._save()
        
        logger.debug(
            f"MetaLearner: strategy={strategy}, success={result.get('success')}, "
            f"confidence={confidence:.2f}, success_rate={stats.success_rate:.2f}"
        )
    
    def get_strategy_stats(self, strategy: str) -> StrategyStats:
        """
        Возвращает статистику по стратегии
        
        Args:
            strategy: название стратегии
        
        Returns:
            StrategyStats с текущей статистикой
        """
        return self.stats.get(strategy, StrategyStats())
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """
        Возвращает статистику по всем стратегиям
        
        Returns:
            dict с названием стратегии → stats dict
        """
        return {
            strategy: stats.to_dict() 
            for strategy, stats in self.stats.items()
        }
    
    def get_best_strategy(self, min_samples: int = None) -> Optional[str]:
        """
        Возвращает лучшую стратегию по success rate
        
        Args:
            min_samples: минимальное количество примеров для учёта
        
        Returns:
            название лучшей стратегии или None
        """
        if min_samples is None:
            min_samples = self.MIN_SAMPLES_FOR_ADJUSTMENT
        
        # Фильтруем стратегии с достаточным количеством примеров
        candidates = {
            strategy: stats 
            for strategy, stats in self.stats.items() 
            if stats.count >= min_samples
        }
        
        if not candidates:
            return None
        
        # Возвращаем стратегию с highest success rate
        best_strategy = max(candidates.items(), key=lambda x: x[1].success_rate)
        return best_strategy[0]
    
    def get_worst_strategy(self, min_samples: int = None) -> Optional[str]:
        """
        Возвращает худшую стратегию по success rate
        
        Args:
            min_samples: минимальное количество примеров для учёта
        
        Returns:
            название худшей стратегии или None
        """
        if min_samples is None:
            min_samples = self.MIN_SAMPLES_FOR_ADJUSTMENT
        
        # Фильтруем стратегии с достаточным количеством примеров
        candidates = {
            strategy: stats 
            for strategy, stats in self.stats.items() 
            if stats.count >= min_samples
        }
        
        if not candidates:
            return None
        
        # Возвращаем стратегию с lowest success rate
        worst_strategy = min(candidates.items(), key=lambda x: x[1].success_rate)
        return worst_strategy[0]
    
    def should_adjust_strategy(self, current: str) -> Optional[str]:
        """
        Рекомендует смену стратегии если текущая плохо работает
        
        Args:
            current: текущая стратегия
        
        Returns:
            рекомендуемая стратегия или None если смена не нужна
        """
        current_stats = self.stats.get(current)
        if not current_stats or current_stats.count < self.MIN_SAMPLES_FOR_ADJUSTMENT:
            return None
        
        # Проверяем, плохая ли текущая стратегия
        if current_stats.success_rate >= self.LOW_SUCCESS_THRESHOLD:
            return None
        
        # Ищем лучшую альтернативу
        best_strategy = self.get_best_strategy()
        if best_strategy and best_strategy != current:
            best_stats = self.stats[best_strategy]
            # Рекомендем только если лучшая значительно лучше
            if best_stats.success_rate > current_stats.success_rate + 0.2:
                logger.info(
                    f"MetaLearner: рекомендуется сменить {current} "
                    f"(success={current_stats.success_rate:.2f}) → "
                    f"{best_strategy} (success={best_stats.success_rate:.2f})"
                )
                return best_strategy
        
        return None
    
    def get_strategy_recommendation(self, context: dict = None) -> Optional[str]:
        """
        Возвращает рекомендацию по стратегии на основе контекста
        
        Args:
            context: дополнительный контекст
        
        Returns:
            рекомендуемая стратегия или None
        """
        # Если система перегружена — рекомендуем простую стратегию
        if context and context.get('system_overloaded', False):
            return "simple"
        
        # Если нужна высокая точность — рекомендуем reasoning
        if context and context.get('need_accuracy', False):
            return "reasoning"
        
        # Иначе возвращаем лучшую по статистике
        return self.get_best_strategy()
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """
        Анализирует паттерны в последних решениях
        
        Returns:
            dict с обнаруженными паттернами
        """
        if not self._recent_decisions or len(self._recent_decisions) < 5:
            return {"patterns": [], "recommendations": [], "recent_success_rate": 0.0}
        
        patterns = []
        recommendations = []
        
        # Анализируем последовательные неудачи
        consecutive_fails = 0
        for decision in reversed(self._recent_decisions):
            if not decision['success']:
                consecutive_fails += 1
            else:
                break
        
        if consecutive_fails >= 3:
            patterns.append(f"{consecutive_fails} последовательных неудач")
            recommendations.append("Рассмотреть смену стратегии")
        
        # Анализируем тренд уверенности
        recent_confidences = [d['confidence'] for d in self._recent_decisions[-10:]]
        if len(recent_confidences) >= 5:
            trend = sum(recent_confidences[-3:]) - sum(recent_confidences[:3])
            if trend < -0.3:
                patterns.append("Уверенность снижается")
                recommendations.append("Проверить качество источников")
        
        recent_decisions_list = self._recent_decisions[-10:] if self._recent_decisions else []
        recent_success_rate = (
            sum(1 for d in recent_decisions_list if d['success']) / max(1, len(recent_decisions_list))
            if recent_decisions_list else 0.0
        )
        
        return {
            "patterns": patterns,
            "recommendations": recommendations,
            "recent_success_rate": recent_success_rate
        }
    
    def _load(self):
        """Загружает статистику из файла"""
        if not os.path.exists(self.data_path):
            return
        
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for strategy, stats_data in data.get('stats', {}).items():
                    if strategy in self.stats:
                        s = self.stats[strategy]
                        s.success = stats_data.get('success', 0)
                        s.fail = stats_data.get('fail', 0)
                        s.total_confidence = stats_data.get('total_confidence', 0.0)
                        s.count = stats_data.get('count', 0)
                        s.last_used = stats_data.get('last_used', time.time())
                
                # Загружаем недавние решения
                self._recent_decisions = data.get('recent_decisions', [])[-self._max_recent:]
                
                logger.debug(f"MetaLearner loaded from {self.data_path}")
                
        except Exception as e:
            logger.warning(f"MetaLearner load error: {e}")
    
    def _save(self):
        """Сохраняет статистику в файл"""
        try:
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            
            data = {
                'updated': time.time(),
                'stats': {
                    strategy: stats.to_dict()
                    for strategy, stats in self.stats.items()
                },
                'recent_decisions': self._recent_decisions[-self._max_recent:]
            }
            
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"MetaLearner save error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает общую статистику MetaLearner"""
        total_decisions = sum(s.count for s in self.stats.values())
        total_success = sum(s.success for s in self.stats.values())
        
        return {
            "total_decisions": total_decisions,
            "total_success": total_success,
            "overall_success_rate": round(total_success / max(1, total_decisions), 3),
            "strategies": self.get_all_stats(),
            "best_strategy": self.get_best_strategy(),
            "worst_strategy": self.get_worst_strategy(),
            "patterns": self.analyze_patterns()
        }
    
    def reset(self):
        """Сбрасывает всю статистику (для тестов)"""
        for stats in self.stats.values():
            stats.success = 0
            stats.fail = 0
            stats.total_confidence = 0.0
            stats.count = 0
        
        self._recent_decisions.clear()
        self._save()
        logger.info("MetaLearner reset")


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_meta_learner: Optional[MetaLearner] = None


def get_meta_learner() -> MetaLearner:
    """
    Возвращает глобальный экземпляр MetaLearner
    
    Returns:
        MetaLearner: единый экземпляр для всей системы
    """
    global _meta_learner
    if _meta_learner is None:
        _meta_learner = MetaLearner()
        logger.info("✅ MetaLearner инициализирован")
    return _meta_learner


def reset_meta_learner():
    """Сбрасывает глобальный экземпляр (для тестов)"""
    global _meta_learner
    _meta_learner = None