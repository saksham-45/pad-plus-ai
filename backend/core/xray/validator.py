"""
🔍 Trace Validator — Система верификации инвариантов

Проверяет:
- Структуру трассировки
- Инварианты пайплайна
- Когнитивную консистентность
- Silent failures
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger("padplus.xray")


class ValidationSeverity(Enum):
    """Серьёзность ошибки валидации"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationError:
    """Ошибка валидации"""
    code: str
    message: str
    severity: ValidationSeverity
    component: str  # "trace", "pipeline", "cognitive", "silent_failure"
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "component": self.component,
            "details": self.details
        }


# === ИНВАРИАНТЫ ===

REQUIRED_PIPELINE_STAGES = ["intent", "retrieve", "generate", "emit"]

VALID_SPAN_KINDS = ["internal", "server", "client", "producer", "consumer"]

VALID_COGNITIVE_METRICS_RANGE = (0.0, 1.0)


class TraceValidator:
    """
    🔍 Валидатор трассировок
    
    Проверяет инварианты системы и обнаруживает silent failures
    """
    
    def __init__(self):
        self._custom_validators: List[Callable] = []
        self._error_counts: Dict[str, int] = {}
        
        logger.info("✅ TraceValidator инициализирован")
    
    def validate(
        self, 
        trace_data: Dict[str, Any],
        cognitive_state: Dict[str, Any] = None
    ) -> List[ValidationError]:
        """
        Полная валидация трассировки
        
        Returns:
            Список ошибок валидации
        """
        errors = []
        
        # 1. Валидация структуры трассировки
        errors.extend(self._validate_trace_structure(trace_data))
        
        # 2. Валидация пайплайна
        errors.extend(self._validate_pipeline(trace_data))
        
        # 3. Валидация когнитивного состояния
        if cognitive_state:
            errors.extend(self._validate_cognitive_state(cognitive_state))
        
        # 4. Детекция silent failures
        errors.extend(self._detect_silent_failures(trace_data, cognitive_state))
        
        # 5. Кастомные валидаторы
        for validator in self._custom_validators:
            try:
                custom_errors = validator(trace_data, cognitive_state)
                errors.extend(custom_errors)
            except Exception as e:
                logger.error(f"Custom validator error: {e}")
        
        # Подсчёт ошибок
        for error in errors:
            self._error_counts[error.code] = \
                self._error_counts.get(error.code, 0) + 1
        
        return errors
    
    def _validate_trace_structure(
        self, 
        trace_data: Dict[str, Any]
    ) -> List[ValidationError]:
        """Валидация структуры трассировки"""
        errors = []
        
        # Проверка trace_id
        trace_id = trace_data.get("trace_id")
        if not trace_id:
            errors.append(ValidationError(
                code="missing_trace_id",
                message="Trace ID отсутствует",
                severity=ValidationSeverity.CRITICAL,
                component="trace"
            ))
        
        # Проверка спанов
        spans = trace_data.get("spans") or {}
        
        if not spans:
            errors.append(ValidationError(
                code="no_spans",
                message="Трассировка не содержит спанов",
                severity=ValidationSeverity.ERROR,
                component="trace"
            ))
        
        for span_id, span_data in spans.items():
            # Проверка span_id
            if not span_data.get("span_id"):
                errors.append(ValidationError(
                    code="missing_span_id",
                    message=f"Span {span_id} не имеет ID",
                    severity=ValidationSeverity.ERROR,
                    component="trace",
                    details={"span_id": span_id}
                ))
            
            # Проверка parent_span_id (если есть)
            parent_id = span_data.get("parent_span_id")
            if parent_id and parent_id not in spans:
                errors.append(ValidationError(
                    code="orphan_span",
                    message=f"Span {span_id} ссылается на несуществующий parent {parent_id}",
                    severity=ValidationSeverity.ERROR,
                    component="trace",
                    details={"span_id": span_id, "parent_id": parent_id}
                ))
            
            # Проверка kind
            kind = span_data.get("kind")
            if kind and kind not in VALID_SPAN_KINDS:
                errors.append(ValidationError(
                    code="invalid_span_kind",
                    message=f"Невалидный kind '{kind}' для span {span_id}",
                    severity=ValidationSeverity.WARNING,
                    component="trace",
                    details={"span_id": span_id, "kind": kind}
                ))
            
            # Проверка duration
            duration = span_data.get("duration_ms")
            if duration is not None and duration < 0:
                errors.append(ValidationError(
                    code="negative_duration",
                    message=f"Отрицательная длительность для span {span_id}",
                    severity=ValidationSeverity.ERROR,
                    component="trace",
                    details={"span_id": span_id, "duration": duration}
                ))
            
            # Проверка очень длинных спанов
            if duration and duration > 60000:  # > 1 минуты
                errors.append(ValidationError(
                    code="very_long_span",
                    message=f"Очень длинный span {span_id}: {duration:.0f}ms",
                    severity=ValidationSeverity.WARNING,
                    component="trace",
                    details={"span_id": span_id, "duration": duration}
                ))
        
        return errors
    
    def _validate_pipeline(
        self, 
        trace_data: Dict[str, Any]
    ) -> List[ValidationError]:
        """Валидация пайплайна"""
        errors = []
        
        spans = trace_data.get("spans") or {}
        stages = [s.get("name") for s in spans.values()]
        
        # Проверка обязательных стадий
        for stage in REQUIRED_PIPELINE_STAGES:
            if stage not in stages:
                errors.append(ValidationError(
                    code="missing_required_stage",
                    message=f"Отсутствует обязательная стадия '{stage}'",
                    severity=ValidationSeverity.ERROR,
                    component="pipeline",
                    details={"missing_stage": stage, "stages": stages}
                ))
        
        # Проверка порядка стадий (если есть)
        expected_order = ["safety", "intent", "retrieve", "persona", 
                          "generate", "verify", "remember", "emit"]
        
        last_index = -1
        for stage in stages:
            if stage in expected_order:
                idx = expected_order.index(stage)
                if idx < last_index:
                    errors.append(ValidationError(
                        code="out_of_order_stage",
                        message=f"Стадия '{stage}' вне порядка",
                        severity=ValidationSeverity.WARNING,
                        component="pipeline",
                        details={"stage": stage, "expected_after": expected_order[last_index]}
                    ))
                last_index = idx
        
        # Проверка на слишком мало стадий
        if len(stages) < 3:
            errors.append(ValidationError(
                code="too_few_stages",
                message=f"Слишком мало стадий: {len(stages)}",
                severity=ValidationSeverity.WARNING,
                component="pipeline",
                details={"stage_count": len(stages)}
            ))
        
        return errors
    
    def _validate_cognitive_state(
        self, 
        cognitive_state: Dict[str, Any]
    ) -> List[ValidationError]:
        """Валидация когнитивного состояния"""
        errors = []
        
        metrics = cognitive_state.get("metrics", {})
        
        # Проверка диапазонов метрик
        for metric_name in ["uncertainty", "cognitive_load", "confidence", "complexity"]:
            value = metrics.get(metric_name)
            if value is not None:
                if not (VALID_COGNITIVE_METRICS_RANGE[0] <= value <= VALID_COGNITIVE_METRICS_RANGE[1]):
                    errors.append(ValidationError(
                        code=f"metric_out_of_range",
                        message=f"{metric_name}={value} вне диапазона [0, 1]",
                        severity=ValidationSeverity.ERROR,
                        component="cognitive",
                        details={"metric": metric_name, "value": value}
                    ))
        
        # Проверка на противоречивые состояния
        confidence = metrics.get("confidence", 0)
        uncertainty = metrics.get("uncertainty", 0)
        
        if confidence > 0.9 and uncertainty > 0.7:
            errors.append(ValidationError(
                code="contradictory_state",
                message="Высокая уверенность при высокой неопределённости",
                severity=ValidationSeverity.WARNING,
                component="cognitive",
                details={"confidence": confidence, "uncertainty": uncertainty}
            ))
        
        # Проверка source_weights
        source_weights = cognitive_state.get("source_weights", {})
        if not source_weights:
            errors.append(ValidationError(
                code="no_sources_used",
                message="Источники информации не использованы",
                severity=ValidationSeverity.INFO,
                component="cognitive"
            ))
        
        # Проверка decision_path
        decision_path = cognitive_state.get("decision_path", [])
        if not decision_path and confidence > 0.8:
            errors.append(ValidationError(
                code="high_confidence_without_reason",
                message="Высокая уверенность без записанных решений",
                severity=ValidationSeverity.WARNING,
                component="cognitive",
                details={"confidence": confidence, "decisions": len(decision_path)}
            ))
        
        return errors
    
    def _detect_silent_failures(
        self, 
        trace_data: Dict[str, Any],
        cognitive_state: Dict[str, Any] = None
    ) -> List[ValidationError]:
        """Детекция silent failures"""
        errors = []
        
        spans = trace_data.get("spans") or {}
        stages = [s.get("name") for s in spans.values()]
        
        # Проверка: нет retrieval стадии
        if "retrieve" not in stages and "generate" in stages:
            errors.append(ValidationError(
                code="no_retrieval_before_generate",
                message="Генерация без retrieval — возможен hallucination",
                severity=ValidationSeverity.WARNING,
                component="silent_failure"
            ))
        
        # Проверка: все спаны успешные, но ответ пустой
        all_ok = all(s.get("status") == "ok" for s in spans.values())
        total_duration = trace_data.get("total_duration_ms", 0)
        
        if all_ok and total_duration < 10:  # < 10ms — подозрительно быстро
            errors.append(ValidationError(
                code="suspiciously_fast",
                message=f"Подозрительно быстрое выполнение: {total_duration:.0f}ms",
                severity=ValidationSeverity.WARNING,
                component="silent_failure",
                details={"duration_ms": total_duration}
            ))
        
        # Проверка: нет verify стадии при низкой уверенности
        if cognitive_state:
            metrics = cognitive_state.get("metrics", {})
            confidence = metrics.get("confidence", 1.0)
            
            if confidence < 0.5 and "verify" not in stages:
                errors.append(ValidationError(
                    code="low_confidence_without_verify",
                    message="Низкая уверенность без верификации",
                    severity=ValidationSeverity.WARNING,
                    component="silent_failure",
                    details={"confidence": confidence}
                ))
        
        # Проверка: слишком много стадий (возможно зацикливание)
        if len(stages) > 20:
            errors.append(ValidationError(
                code="too_many_stages",
                message=f"Подозрительно много стадий: {len(stages)}",
                severity=ValidationSeverity.WARNING,
                component="silent_failure",
                details={"stage_count": len(stages)}
            ))
        
        return errors
    
    def register_validator(self, validator: Callable):
        """Регистрирует кастомный валидатор"""
        self._custom_validators.append(validator)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Статистика ошибок валидации"""
        return {
            "total_errors": sum(self._error_counts.values()),
            "by_code": dict(self._error_counts),
            "by_severity": self._count_by_severity()
        }
    
    def _count_by_severity(self) -> Dict[str, int]:
        """Подсчёт по серьёзности"""
        counts = {}
        # Упрощённо — по кодам ошибок
        for code, count in self._error_counts.items():
            if "critical" in code.lower():
                severity = "critical"
            elif "missing" in code or "invalid" in code:
                severity = "error"
            else:
                severity = "warning"
            counts[severity] = counts.get(severity, 0) + count
        return counts


# Глобальный экземпляр
_validator: Optional[TraceValidator] = None


def get_trace_validator() -> TraceValidator:
    """Возвращает глобальный валидатор"""
    global _validator
    if _validator is None:
        _validator = TraceValidator()
    return _validator