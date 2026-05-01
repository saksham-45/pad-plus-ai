"""
🔍 X-Ray Tracer — Трассировка каждого шага мышления AI
"""

import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("padplus.xray")


@dataclass
class Span:
    """Отдельный этап обработки"""
    name: str
    start_ms: float = 0.0
    end_ms: float = 0.0
    status: str = "ok"  # ok, error, skipped
    details: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms if self.end_ms > 0 else 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_ms": round(self.start_ms, 1),
            "end_ms": round(self.end_ms, 1),
            "duration_ms": round(self.duration_ms, 1),
            "status": self.status,
            "details": self.details,
            "error": self.error,
        }


@dataclass
class Trace:
    """Полный трейс запроса"""
    id: str
    user_message: str
    timestamp: str
    spans: list = field(default_factory=list)
    response: str = ""
    model: str = ""
    provider: str = ""
    thinking_mode: str = ""
    total_ms: float = 0.0
    success: bool = False

    def add_span(self, name: str, **details) -> Span:
        span = Span(
            name=name,
            start_ms=(time.monotonic() - self._start_time) * 1000 if hasattr(self, '_start_time') else 0,
            details=details,
        )
        self.spans.append(span)
        return span

    def finish_span(self, name: str, status: str = "ok", error: str = None):
        for span in reversed(self.spans):
            if span.name == name and span.end_ms == 0:
                span.end_ms = (time.monotonic() - self._start_time) * 1000 if hasattr(self, '_start_time') else 0
                span.status = status
                span.error = error
                break

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_message": self.user_message[:200],
            "response": self.response[:200],
            "model": self.model,
            "provider": self.provider,
            "thinking_mode": self.thinking_mode,
            "total_ms": round(self.total_ms, 1),
            "success": self.success,
            "timestamp": self.timestamp,
            "spans": [s.to_dict() for s in self.spans],
        }


class XRayTracer:
    """
    Трассировщик запросов

    Usage:
        tracer = get_xray_tracer()
        trace = tracer.start_trace("Привет!")
        with trace.span("RAG"):
            ...
        tracer.finish_trace(trace, response="Ответ")
    """

    def start_trace(self, user_message: str) -> Trace:
        trace = Trace(
            id=str(uuid.uuid4())[:8],
            user_message=user_message,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        trace._start_time = time.monotonic()
        logger.info(f"🔍 X-Ray trace started: {trace.id}")
        return trace

    def finish_trace(self, trace: Trace, response: str = "", success: bool = True,
                     model: str = "", provider: str = "", thinking_mode: str = ""):
        trace.response = response
        trace.success = success
        trace.model = model
        trace.provider = provider
        trace.thinking_mode = thinking_mode
        trace.total_ms = (time.monotonic() - trace._start_time) * 1000

        # Завершаем все незавершённые спаны
        for span in trace.spans:
            if span.end_ms == 0:
                span.end_ms = trace.total_ms

        logger.info(f"🔍 X-Ray trace finished: {trace.id} ({trace.total_ms:.0f}ms, {trace.model})")
        return trace


# Глобальный экземпляр
_tracer = None


def get_xray_tracer() -> XRayTracer:
    global _tracer
    if _tracer is None:
        _tracer = XRayTracer()
    return _tracer
