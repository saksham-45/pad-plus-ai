"""
🔬 Trace Context — Контекст трассировки с иерархией

Реализует распределённую трассировку по образцу OpenTelemetry:
- trace_id: глобальный ID сессии
- span_id: локальный ID операции
- parent_span_id: связь с родительской операцией
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger("padplus.xray")


class SpanStatus(Enum):
    """Статус спана"""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Контекст отдельного спана"""
    trace_id: str           # Глобальный ID трассировki
    span_id: str            # Локальный ID спана
    parent_span_id: Optional[str]  # ID родителя (None для корневого)
    name: str               # Имя спана (стадия пайплайна)
    kind: str               # Тип: "internal", "server", "client"
    start_time: float       # Время начала (timestamp)
    end_time: Optional[float] = None  # Время окончания
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Длительность в миллисекундах"""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": self.events
        }
    
    def add_event(self, name: str, attributes: Dict = None):
        """Добавляет событие в спан"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        })
    
    def set_attribute(self, key: str, value: Any):
        """Устанавливает атрибут"""
        self.attributes[key] = value
    
    def set_status(self, status: SpanStatus, description: str = None):
        """Устанавливает статус"""
        self.status = status
        if description:
            self.attributes["status_description"] = description
    
    def end(self):
        """Завершает спан"""
        self.end_time = time.time()
        if self.status == SpanStatus.UNSET:
            self.status = SpanStatus.OK


@dataclass
class Trace:
    """Трассировка — коллекция связанных спанов"""
    trace_id: str
    root_span_id: str
    start_time: float
    user_message: str
    spans: Dict[str, SpanContext] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed: bool = False
    
    def add_span(self, span: SpanContext):
        """Добавляет спан в трассировку"""
        self.spans[span.span_id] = span
    
    def get_span(self, span_id: str) -> Optional[SpanContext]:
        """Получает спан by ID"""
        return self.spans.get(span_id)
    
    def get_children(self, parent_span_id: str) -> List[SpanContext]:
        """Получает дочерние спаны"""
        return [
            span for span in self.spans.values()
            if span.parent_span_id == parent_span_id
        ]
    
    def get_span_tree(self) -> Dict:
        """Строит дерево спанов"""
        root = None
        children_map = {}
        
        for span in self.spans.values():
            if span.parent_span_id is None:
                root = span
            else:
                if span.parent_span_id not in children_map:
                    children_map[span.parent_span_id] = []
                children_map[span.parent_span_id].append(span)
        
        def build_tree(span: SpanContext) -> Dict:
            node = span.to_dict()
            node["children"] = [
                build_tree(child) 
                for child in children_map.get(span.span_id, [])
            ]
            return node
        
        return build_tree(root) if root else {}
    
    def get_total_duration_ms(self) -> Optional[float]:
        """Общая длительность трассировки"""
        if not self.spans:
            return None
        
        min_start = min(s.start_time for s in self.spans.values())
        max_end = max(
            s.end_time for s in self.spans.values() 
            if s.end_time is not None
        )
        
        return (max_end - min_start) * 1000
    
    def get_critical_path(self) -> List[SpanContext]:
        """Находит критический путь (самая длинная цепочка)"""
        def find_longest_path(span_id: str) -> List[SpanContext]:
            span = self.spans.get(span_id)
            if not span:
                return []
            
            children = self.get_children(span_id)
            if not children:
                return [span]
            
            # Находим ребёнка с самой длинной цепочкой
            longest_child_path = max(
                [find_longest_path(c.span_id) for c in children],
                key=lambda path: sum(
                    s.duration_ms or 0 for s in path
                ),
                default=[]
            )
            
            return [span] + longest_child_path
        
        # Начинаем с корневого спана
        root = next(
            (s for s in self.spans.values() if s.parent_span_id is None),
            None
        )
        
        return find_longest_path(root.span_id) if root else []
    
    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "start_time": self.start_time,
            "user_message": self.user_message,
            "spans": {k: v.to_dict() for k, v in self.spans.items()},
            "span_tree": self.get_span_tree(),
            "total_duration_ms": self.get_total_duration_ms(),
            "critical_path": [s.span_id for s in self.get_critical_path()],
            "metadata": self.metadata,
            "completed": self.completed
        }


class TraceContextManager:
    """
    Менеджер контекста трассировки
    
    Управляет созданием и жизненным циклом trace/span
    """
    
    def __init__(self):
        self._active_traces: Dict[str, Trace] = {}
        self._current_span_stack: List[SpanContext] = []
        self._subscribers: List[callable] = []
    
    def start_trace(
        self, 
        user_message: str,
        metadata: Dict = None
    ) -> Trace:
        """Начинает новую трассировку"""
        trace_id = str(uuid.uuid4())
        
        # Корневой спан
        root_span_id = str(uuid.uuid4())
        root_span = SpanContext(
            trace_id=trace_id,
            span_id=root_span_id,
            parent_span_id=None,
            name="pipeline_execution",
            kind="internal",
            start_time=time.time()
        )
        
        trace = Trace(
            trace_id=trace_id,
            root_span_id=root_span_id,
            start_time=time.time(),
            user_message=user_message,
            metadata=metadata or {}
        )
        
        trace.add_span(root_span)
        self._active_traces[trace_id] = trace
        
        # Устанавливаем корневой спан как текущий
        self._current_span_stack = [root_span]
        
        logger.debug(f"🔬 Trace started: {trace_id}")
        return trace
    
    def start_span(
        self,
        name: str,
        kind: str = "internal",
        attributes: Dict = None
    ) -> SpanContext:
        """Создаёт новый спан в текущей трассировке"""
        if not self._current_span_stack:
            raise RuntimeError("No active trace. Call start_trace first.")
        
        parent_span = self._current_span_stack[-1]
        
        span = SpanContext(
            trace_id=parent_span.trace_id,
            span_id=str(uuid.uuid4()),
            parent_span_id=parent_span.span_id,
            name=name,
            kind=kind,
            start_time=time.time()
        )
        
        if attributes:
            span.attributes.update(attributes)
        
        # Добавляем в трассировку
        trace = self._active_traces.get(parent_span.trace_id)
        if trace:
            trace.add_span(span)
        
        # Делаем текущим
        self._current_span_stack.append(span)
        
        logger.debug(f"🔬 Span started: {span.span_id} ({name})")
        return span
    
    def end_span(
        self, 
        span: SpanContext = None,
        status: SpanStatus = None
    ):
        """Завершает текущий или указанный спан"""
        if span is None:
            if not self._current_span_stack:
                return
            span = self._current_span_stack.pop()
        else:
            if span in self._current_span_stack:
                self._current_span_stack.remove(span)
        
        if status:
            span.set_status(status)
        
        span.end()
        
        logger.debug(f"🔬 Span ended: {span.span_id}")
    
    def end_trace(
        self, 
        trace_id: str = None,
        status: SpanStatus = None
    ):
        """Завершает трассировку"""
        if trace_id is None:
            if not self._current_span_stack:
                return
            trace_id = self._current_span_stack[0].trace_id
        
        trace = self._active_traces.get(trace_id)
        if not trace:
            return
        
        # Собираем все спаны этой трассировки из стека
        spans_to_end = [span for span in list(self._current_span_stack) 
                        if span.trace_id == trace_id]
        
        # Завершаем все спаны (end_span удаляет из стека)
        for span in spans_to_end:
            if status:
                span.set_status(status)
            span.end()
            if span in self._current_span_stack:
                self._current_span_stack.remove(span)
        
        # Завершаем корневой спан
        root_span = trace.spans.get(trace.root_span_id)
        if root_span and root_span.end_time is None:
            if status:
                root_span.set_status(status)
            root_span.end()
        
        trace.completed = True
        
        # Удаляем из активных трассировок
        del self._active_traces[trace_id]
        
        # Уведомляем подписчиков
        self._notify_subscribers("trace_completed", trace.to_dict())
        
        logger.debug(f"🔬 Trace completed: {trace_id}")
    
    def get_current_trace(self) -> Optional[Trace]:
        """Получает текущую активную трассировку"""
        if not self._current_span_stack:
            return None
        return self._active_traces.get(
            self._current_span_stack[0].trace_id
        )
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Получает трассировку by ID"""
        return self._active_traces.get(trace_id)
    
    def subscribe(self, callback: callable):
        """Подписывает обработчик на события"""
        self._subscribers.append(callback)
    
    def _notify_subscribers(self, event: str, data: Dict):
        """Уведомляет подписчиков"""
        for callback in self._subscribers:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Trace subscriber error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика менеджера"""
        return {
            "active_traces": len(self._active_traces),
            "current_span_depth": len(self._current_span_stack)
        }


# Глобальный экземпляр
_trace_context_manager: Optional[TraceContextManager] = None


def get_trace_context_manager() -> TraceContextManager:
    """Возвращает глобальный менеджер контекста"""
    global _trace_context_manager
    if _trace_context_manager is None:
        _trace_context_manager = TraceContextManager()
    return _trace_context_manager