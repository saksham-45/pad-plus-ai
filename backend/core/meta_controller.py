"""
🧠 MetaCognitiveController — Центр мета-познания

Координирует все мета-познавательные процессы:
- Оценка когнитивной нагрузки
- Принятие решений о стратегиях
- Управление подсистемами
- Координация обучения и адаптации
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
import json
import os


class ProcessingStrategy(Enum):
    """Стратегии обработки запросов"""
    SIMPLE = "simple"           # Быстрый ответ без глубокой обработки
    DEEP = "deep"               # Глубокий анализ с RAG и памятью
    CREATIVE = "creative"       # Творческий режим с высокой температурой
    REFLECTIVE = "reflective"   # Режим саморефлексии
    SAFETY = "safety"           # Режим безопасности (проверка угроз)
    LEARNING = "learning"       # Режим активного обучения


class CognitiveState(Enum):
    """Состояния когнитивной системы"""
    IDLE = "idle"               # Простой
    PROCESSING = "processing"   # Обработка запроса
    REFLECTING = "reflecting"   # Рефлексия
    LEARNING = "learning"       # Обучение
    RECOVERING = "recovering"   # Восстановление после ошибки
    OVERLOADED = "overloaded"   # Перегрузка


@dataclass
class CognitiveLoad:
    """Оценка когнитивной нагрузки"""
    current: float = 0.0        # 0.0 - 1.0
    memory_usage: float = 0.0
    processing_queue: int = 0
    recent_errors: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "current": self.current,
            "memory_usage": self.memory_usage,
            "processing_queue": self.processing_queue,
            "recent_errors": self.recent_errors,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class StrategyDecision:
    """Решение о стратегии"""
    strategy: ProcessingStrategy
    reason: str
    confidence: float
    estimated_time: float  # секунды
    resources_needed: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "estimated_time": self.estimated_time,
            "resources_needed": self.resources_needed,
            "timestamp": self.timestamp.isoformat()
        }


class MetaCognitiveController:
    """
    🧠 Мета-когнитивный контроллер
    
    Центральный узел управления мета-познанием:
    - Координирует все мета-познавательные процессы
    - Принимает мета-решения о стратегиях обработки
    - Управляет когнитивной нагрузкой
    - Взаимодействует со всеми мета-компонентами
    """
    
    # Пороги когнитивной нагрузки
    LOAD_THRESHOLDS = {
        "low": 0.3,
        "medium": 0.6,
        "high": 0.8,
        "critical": 0.95
    }
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "meta_cognitive.json"
            )
        self.data_path = data_path
        
        self._state = CognitiveState.IDLE
        self._load = CognitiveLoad()
        self._decision_history: List[StrategyDecision] = []
        self._subsystems: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        
        # Счётчики
        self._total_requests = 0
        self._strategy_counts: Dict[str, int] = {}
        self._successful_adaptations = 0
        
        self._load_state()
    
    def _load_state(self):
        """Загружает состояние из файла"""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._total_requests = data.get('total_requests', 0)
                    self._strategy_counts = data.get('strategy_counts', {})
                    self._successful_adaptations = data.get(
                        'successful_adaptations', 0
                    )
            except Exception as e:
                print(f"Ошибка загрузки мета-состояния: {e}")
    
    def _save_state(self):
        """Сохраняет состояние в файл"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        
        data = {
            "updated": datetime.now().isoformat(),
            "state": self._state.value,
            "total_requests": self._total_requests,
            "strategy_counts": self._strategy_counts,
            "successful_adaptations": self._successful_adaptations,
            "decision_history": [d.to_dict() for d in self._decision_history[-100:]]
        }
        
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def register_subsystem(self, name: str, subsystem: Any):
        """Регистрирует подсистему"""
        self._subsystems[name] = subsystem
    
    def register_hook(self, event: str, callback: Callable):
        """Регистрирует хук для событий"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
    
    def _emit(self, event: str, data: Any = None):
        """Вызывает хуки события"""
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Ошибка в хуке {event}: {e}")
    
    # === Оценка когнитивной нагрузки ===
    
    def evaluate_cognitive_load(self) -> CognitiveLoad:
        """Оценивает текущую когнитивную нагрузку"""
        load = 0.0
        
        # Факторы нагрузки
        factors = []
        
        # 1. Размер очереди обработки
        queue_size = self._load.processing_queue
        queue_factor = min(1.0, queue_size / 10)
        factors.append(("queue", queue_factor, 0.3))
        
        # 2. Недавние ошибки
        error_factor = min(1.0, self._load.recent_errors / 5)
        factors.append(("errors", error_factor, 0.2))
        
        # 3. Использование памяти
        memory_factor = self._load.memory_usage
        factors.append(("memory", memory_factor, 0.3))
        
        # 4. Текущее состояние
        state_factor = {
            CognitiveState.IDLE: 0.1,
            CognitiveState.PROCESSING: 0.5,
            CognitiveState.REFLECTING: 0.7,
            CognitiveState.LEARNING: 0.6,
            CognitiveState.RECOVERING: 0.8,
            CognitiveState.OVERLOADED: 1.0
        }.get(self._state, 0.5)
        factors.append(("state", state_factor, 0.2))
        
        # Взвешенная сумма
        total_weight = sum(f[2] for f in factors)
        load = sum(f[1] * f[2] for f in factors) / total_weight
        
        self._load.current = load
        self._load.last_updated = datetime.now()
        
        return self._load
    
    def update_load_metrics(self, memory_usage: float = None,
                            queue_size: int = None,
                            errors: int = None):
        """Обновляет метрики нагрузки"""
        if memory_usage is not None:
            self._load.memory_usage = memory_usage
        if queue_size is not None:
            self._load.processing_queue = queue_size
        if errors is not None:
            self._load.recent_errors = errors
    
    # === Принятие решений о стратегии ===
    
    def decide_strategy(self, query: str, context: Dict = None) -> StrategyDecision:
        """Принимает решение о стратегии обработки"""
        self._total_requests += 1
        load = self.evaluate_cognitive_load()
        
        # Анализируем запрос
        query_lower = query.lower()
        
        # Определяем стратегию на основе множества факторов
        strategy = ProcessingStrategy.SIMPLE
        reason = "По умолчанию"
        confidence = 0.5
        estimated_time = 1.0
        resources = []
        
        # 1. Проверка на угрозы безопасности
        safety_keywords = ['взлом', 'exploit', 'инъекция', 'атака', 
                          'обойти', 'игнорировать']
        if any(kw in query_lower for kw in safety_keywords):
            strategy = ProcessingStrategy.SAFETY
            reason = "Обнаружены потенциально опасные ключевые слова"
            confidence = 0.9
            estimated_time = 2.0
            resources = ["safety_layer", "anti_directive"]
        
        # 2. Проверка на рефлексивный запрос
        elif any(kw in query_lower for kw in 
                 ['почему ты', 'как ты', 'что ты думаешь о себе',
                  'проанализируй себя', 'саморефлексия']):
            strategy = ProcessingStrategy.REFLECTIVE
            reason = "Запрос требует саморефлексии"
            confidence = 0.85
            estimated_time = 5.0
            resources = ["self_reflection", "memory_all", "truth_loop"]
        
        # 3. Проверка на творческий запрос
        elif any(kw in query_lower for kw in 
                 ['придумай', 'сочини', 'придумай историю', 'креативно',
                  'оригинально', 'необычно']):
            strategy = ProcessingStrategy.CREATIVE
            reason = "Запрос требует творческого подхода"
            confidence = 0.8
            estimated_time = 3.0
            resources = ["persona", "emotion"]
        
        # 4. Проверка на обучающий запрос
        elif any(kw in query_lower for kw in 
                 ['запомни', 'выучи', 'новый факт', 'добавь в память']):
            strategy = ProcessingStrategy.LEARNING
            reason = "Запрос содержит указание на обучение"
            confidence = 0.85
            estimated_time = 2.0
            resources = ["memory", "knowledge_graph", "persona"]
        
        # 5. Сложный вопрос — глубокая обработка
        elif any(kw in query_lower for kw in 
                 ['объясни', 'подробно', 'проанализируй', 'сравни',
                  'почему', 'как работает']):
            strategy = ProcessingStrategy.DEEP
            reason = "Запрос требует глубокого анализа"
            confidence = 0.75
            estimated_time = 4.0
            resources = ["rag", "knowledge_graph", "facts", "truth_loop"]
        
        # 6. Корректировка на основе нагрузки
        if load.current > self.LOAD_THRESHOLDS["high"]:
            if strategy in [ProcessingStrategy.DEEP, ProcessingStrategy.REFLECTIVE]:
                # Снижаем сложность при высокой нагрузке
                strategy = ProcessingStrategy.SIMPLE
                reason = f"Упрощено из-за нагрузки ({load.current:.2f})"
                confidence *= 0.7
                estimated_time = 1.0
                resources = ["rag"]
        
        # Записываем решение
        decision = StrategyDecision(
            strategy=strategy,
            reason=reason,
            confidence=confidence,
            estimated_time=estimated_time,
            resources_needed=resources
        )
        
        self._decision_history.append(decision)
        self._strategy_counts[strategy.value] = \
            self._strategy_counts.get(strategy.value, 0) + 1
        
        self._save_state()
        self._emit("strategy_decided", decision)
        
        return decision
    
    # === Управление подсистемами ===
    
    def coordinate_subsystems(self, decision: StrategyDecision) -> Dict[str, bool]:
        """Координирует подсистемы для выполнения решения"""
        results = {}
        
        # Определяем какие подсистемы нужны
        for resource in decision.resources_needed:
            if resource in self._subsystems:
                try:
                    # Активируем подсистему
                    subsystem = self._subsystems[resource]
                    if hasattr(subsystem, 'activate'):
                        subsystem.activate()
                    results[resource] = True
                except Exception as e:
                    print(f"Ошибка активации {resource}: {e}")
                    results[resource] = False
            else:
                results[resource] = False
        
        return results
    
    def get_subsystem_status(self) -> Dict[str, Any]:
        """Возвращает статус всех подсистем"""
        status = {}
        
        for name, subsystem in self._subsystems.items():
            try:
                if hasattr(subsystem, 'get_status'):
                    status[name] = subsystem.get_status()
                elif hasattr(subsystem, 'is_active'):
                    status[name] = {"active": subsystem.is_active()}
                else:
                    status[name] = {"registered": True}
            except Exception as e:
                status[name] = {"error": str(e)}
        
        return status
    
    # === Адаптация ===
    
    def adapt(self, feedback: Dict[str, Any]):
        """Адаптируется на основе обратной связи"""
        # Анализируем обратную связь
        success = feedback.get('success', True)
        strategy_used = feedback.get('strategy')
        response_time = feedback.get('response_time', 0)
        
        if not success:
            # Неудача — увеличиваем счётчик ошибок
            self._load.recent_errors += 1
            
            # Анализируем причину
            if feedback.get('reason') == 'timeout':
                # Таймаут — возможно, стратегия была слишком сложной
                if strategy_used in ['deep', 'reflective']:
                    self._emit("adaptation_needed", {
                        "type": "simplify_strategy",
                        "reason": "timeout"
                    })
        
        else:
            # Успех — уменьшаем ошибки
            if self._load.recent_errors > 0:
                self._load.recent_errors -= 1
            self._successful_adaptations += 1
        
        self._save_state()
    
    # === Состояние ===
    
    def set_state(self, state: CognitiveState):
        """Устанавливает состояние системы"""
        old_state = self._state
        self._state = state
        self._emit("state_changed", {
            "from": old_state.value,
            "to": state.value
        })
    
    def get_state(self) -> CognitiveState:
        """Возвращает текущее состояние"""
        return self._state
    
    # === Отчёты ===
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику работы"""
        load = self.evaluate_cognitive_load()
        
        return {
            "state": self._state.value,
            "total_requests": self._total_requests,
            "strategy_distribution": self._strategy_counts,
            "successful_adaptations": self._successful_adaptations,
            "cognitive_load": load.to_dict(),
            "subsystems": len(self._subsystems),
            "recent_decisions": len(self._decision_history[-10:])
        }
    
    def get_meta_report(self) -> str:
        """Генерирует мета-отчёт"""
        stats = self.get_stats()
        
        lines = [
            "# 🧠 Мета-когнитивный отчёт",
            "",
            f"**Состояние:** {stats['state']}",
            f"**Всего запросов:** {stats['total_requests']}",
            f"**Успешных адаптаций:** {stats['successful_adaptations']}",
            f"**Когнитивная нагрузка:** {stats['cognitive_load']['current']:.2f}",
            "",
            "## Распределение стратегий:",
            ""
        ]
        
        for strategy, count in stats['strategy_distribution'].items():
            pct = count / max(1, stats['total_requests']) * 100
            lines.append(f"- {strategy}: {count} ({pct:.1f}%)")
        
        return "\n".join(lines)


# Глобальный экземпляр
_meta_controller: Optional[MetaCognitiveController] = None


def get_meta_controller() -> MetaCognitiveController:
    """Возвращает глобальный мета-контроллер"""
    global _meta_controller
    if _meta_controller is None:
        _meta_controller = MetaCognitiveController()
    return _meta_controller