"""
🧠 ReflectionLoop — Контур рефлексии X-Ray Brain

Анализирует результат выполнения запроса и обновляет систему:
- Сравнивает ожидаемую и фактическую уверенность
- Извлекает уроки из результата
- Обновляет MetaLearner
- Рекомендует корректировки стратегий

Архитектура:
    Decision → Execution → Result → Reflection.reflect() → MetaLearner → Brain
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import time
import logging

logger = logging.getLogger("padplus.xray.reflection")


@dataclass
class ReflectionResult:
    """
    Результат рефлексии
    
    Содержит:
    - confidence_gap: разница между ожидаемой и фактической уверенностью
    - success: был ли запрос успешным
    - lessons: извлечённые уроки
    - should_adjust: нужно ли корректировать стратегию
    - metrics: дополнительные метрики
    """
    confidence_gap: float        # разница между ожидаемой и фактической
    success: bool
    lessons: List[str]           # извлечённые уроки
    should_adjust: bool          # нужно ли корректировать стратегию
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            "confidence_gap": round(self.confidence_gap, 3),
            "success": self.success,
            "lessons": self.lessons,
            "should_adjust": self.should_adjust,
            "metrics": self.metrics,
            "timestamp": self.timestamp
        }


class ReflectionLoop:
    """
    🧠 ReflectionLoop — контур рефлексии
    
    После каждого ответа:
    1. Анализирует result
    2. Сравнивает с expected (из decision)
    3. Извлекает уроки
    4. Обновляет MetaLearner
    5. Рекомендует корректировки
    
    Пример использования:
        reflection = get_reflection_loop()
        decision = {"strategy": "reasoning", "confidence": 0.8}
        result = {"success": True, "confidence": 0.6, "execution_time_ms": 1500}
        
        reflection_result = reflection.reflect(decision, result)
        print(reflection_result.lessons)  # ["Уверенность ниже ожидаемой"]
    """
    
    # Пороги для анализа
    LOW_CONFIDENCE_THRESHOLD = 0.5
    HIGH_LOAD_THRESHOLD = 0.8
    SLOW_EXECUTION_THRESHOLD_MS = 5000
    
    def __init__(self):
        """Инициализация ReflectionLoop"""
        self._reflection_count = 0
        self._adjustment_count = 0
        logger.info("🧠 ReflectionLoop инициализирован")
    
    def reflect(self, decision: Dict[str, Any], result: Dict[str, Any]) -> ReflectionResult:
        """
        Анализирует результат и обновляет систему
        
        Args:
            decision: решение Brain (Decision.to_dict())
            result: результат выполнения (PipelineResult.to_dict())
        
        Returns:
            ReflectionResult с анализом и рекомендациями
        """
        self._reflection_count += 1
        
        # 1. Оцениваем результат
        confidence_gap = self._analyze_confidence_gap(decision, result)
        success = result.get('success', False)
        
        # 2. Извлекаем уроки
        lessons = self._extract_lessons(decision, result)
        
        # 3. Обновляем MetaLearner
        strategy = decision.get('strategy', 'simple')
        self._update_meta_learner(strategy, result)
        
        # 4. Проверяем, нужно ли корректировать
        should_adjust = self._check_adjustment_needed(strategy, result)
        if should_adjust:
            self._adjustment_count += 1
        
        # 5. Собираем метрики
        metrics = self._collect_metrics(decision, result, confidence_gap)
        
        reflection = ReflectionResult(
            confidence_gap=confidence_gap,
            success=success,
            lessons=lessons,
            should_adjust=should_adjust,
            metrics=metrics
        )
        
        # 6. Логируем
        logger.info(
            f"🧠 Reflection: strategy={strategy}, "
            f"success={success}, confidence_gap={confidence_gap:.2f}, "
            f"should_adjust={should_adjust}, lessons={len(lessons)}"
        )
        
        return reflection
    
    def _analyze_confidence_gap(self, decision: Dict, result: Dict) -> float:
        """
        Анализирует разрыв между ожидаемой и фактической уверенностью
        
        Args:
            decision: решение Brain
            result: результат выполнения
        
        Returns:
            разница (actual - expected), отрицательная = хуже ожидаемого
        """
        expected = decision.get('confidence', 0.5)
        actual = result.get('confidence', 0.5)
        return round(actual - expected, 3)
    
    def _extract_lessons(self, decision: Dict, result: Dict) -> List[str]:
        """
        Извлекает уроки из результата
        
        Args:
            decision: решение Brain
            result: результат выполнения
        
        Returns:
            список извлечённых уроков
        """
        lessons = []
        
        confidence = result.get('confidence', 0.5)
        success = result.get('success', False)
        execution_time = result.get('execution_time_ms', 0)
        use_memory = decision.get('use_memory', False)
        strategy = decision.get('strategy', 'simple')
        
        # Урок 1: низкая уверенность
        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            lessons.append("Низкая уверенность в ответе")
            if not use_memory:
                lessons.append("Возможно, стоило использовать память")
        
        # Урок 2: ошибка выполнения
        if not success:
            lessons.append("Ошибка выполнения запроса")
            if strategy != "simple":
                lessons.append("Рассмотреть упрощение стратегии")
        
        # Урок 3: высокая когнитивная нагрузка
        cognitive_load = result.get('cognitive_load', 0)
        if cognitive_load > self.HIGH_LOAD_THRESHOLD:
            lessons.append("Высокая когнитивная нагрузка")
            lessons.append("Стоит упростить обработку")
        
        # Урок 4: медленное выполнение
        if execution_time > self.SLOW_EXECUTION_THRESHOLD_MS:
            lessons.append(f"Медленное выполнение ({execution_time:.0f}ms)")
            lessons.append("Рассмотреть более лёгкую модель")
        
        # Урок 5: уверенность ниже ожидаемой
        expected_conf = decision.get('confidence', 0.5)
        if confidence < expected_conf - 0.2:
            lessons.append(f"Уверенность ниже ожидаемой (ожидалось {expected_conf:.2f})")
        
        # Урок 6: верификация не помогла
        use_verification = decision.get('use_verification', False)
        truth_confidence = result.get('truth_confidence', 0.5)
        if use_verification and truth_confidence < self.LOW_CONFIDENCE_THRESHOLD:
            lessons.append("Верификация не повысила уверенность")
        
        return lessons
    
    def _update_meta_learner(self, strategy: str, result: Dict):
        """
        Обновляет MetaLearner результатом
        
        Args:
            strategy: использованная стратегия
            result: результат выполнения
        """
        try:
            from core.xray.meta_learner import get_meta_learner
            meta = get_meta_learner()
            meta.record_outcome(strategy, result)
        except Exception as e:
            logger.debug(f"MetaLearner update error: {e}")
    
    def _check_adjustment_needed(self, strategy: str, result: Dict) -> bool:
        """
        Проверяет, нужно ли корректировать стратегию
        
        Args:
            strategy: текущая стратегия
            result: результат выполнения
        
        Returns:
            True если нужна корректировка
        """
        try:
            from core.xray.meta_learner import get_meta_learner
            meta = get_meta_learner()
            adjustment = meta.should_adjust_strategy(strategy)
            return adjustment is not None
        except Exception as e:
            logger.debug(f"Adjustment check error: {e}")
            return False
    
    def _collect_metrics(self, decision: Dict, result: Dict, confidence_gap: float) -> Dict[str, Any]:
        """
        Собирает метрики рефлексии
        
        Args:
            decision: решение Brain
            result: результат выполнения
            confidence_gap: разрыв уверенности
        
        Returns:
            dict с метриками
        """
        return {
            "expected_confidence": decision.get('confidence', 0.5),
            "actual_confidence": result.get('confidence', 0.5),
            "execution_time_ms": result.get('execution_time_ms', 0),
            "cognitive_load": result.get('cognitive_load', 0),
            "truth_confidence": result.get('truth_confidence', 0.5),
            "memory_used": result.get('rag_used', False) or result.get('facts_used', 0) > 0,
            "verification_used": decision.get('use_verification', False),
            "strategy": decision.get('strategy', 'simple'),
            "model": decision.get('model', 'unknown')
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику ReflectionLoop"""
        return {
            "reflection_count": self._reflection_count,
            "adjustment_count": self._adjustment_count,
            "adjustment_rate": round(self._adjustment_count / max(1, self._reflection_count), 3)
        }
    
    def reset(self):
        """Сбрасывает статистику (для тестов)"""
        self._reflection_count = 0
        self._adjustment_count = 0
        logger.info("ReflectionLoop reset")


# ============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================================

_reflection: Optional[ReflectionLoop] = None


def get_reflection_loop() -> ReflectionLoop:
    """
    Возвращает глобальный экземпляр ReflectionLoop
    
    Returns:
        ReflectionLoop: единый экземпляр для всей системы
    """
    global _reflection
    if _reflection is None:
        _reflection = ReflectionLoop()
        logger.info("✅ ReflectionLoop инициализирован")
    return _reflection


def reset_reflection_loop():
    """Сбрасывает глобальный экземпляр (для тестов)"""
    global _reflection
    _reflection = None