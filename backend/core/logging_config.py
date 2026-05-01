"""
📝 Structured Logging Configuration — JSON формат для production

Особенности:
- JSON формат для всех логов
- Поддержка trace_id для отслеживания запросов
- Разные уровни логирования для dev/prod
- Интеграция с ELK/Loki

Использование:
    from core.logging_config import setup_logging, get_logger
    
    setup_logging(level="INFO", json_format=True)
    logger = get_logger("my_module")
    logger.info("Event occurred", extra={"user_id": 123, "trace_id": "abc-123"})
"""

import json
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from contextvars import ContextVar

# Контекстная переменная для trace_id (уникальный ID запроса)
trace_id_context: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def set_trace_id(trace_id: str):
    """Устанавливает trace_id для текущего запроса"""
    trace_id_context.set(trace_id)


def get_trace_id() -> Optional[str]:
    """Получает текущий trace_id"""
    return trace_id_context.get()


class JSONFormatter(logging.Formatter):
    """JSON форматтер для структурированного логирования"""
    
    # Поля, которые не нужно добавлять в JSON
    EXCLUDED_FIELDS = {
        "msg", "args", "levelname", "levelno", "name", "pathname",
        "filename", "module", "lineno", "funcName", "created",
        "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "exc_info", "exc_text",
        "stack_info", "traceback", "taskName"
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога в JSON"""
        
        # Базовые поля
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Добавляем trace_id если есть
        trace_id = get_trace_id()
        if trace_id:
            log_data["trace_id"] = trace_id
        elif hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        
        # Добавляем extra поля (переданные через extra={})
        for key, value in record.__dict__.items():
            if key not in self.EXCLUDED_FIELDS:
                log_data[key] = value
        
        # Добавляем exception если есть
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }
        
        # Добавляем stack_info если есть
        if record.stack_info:
            log_data["stack_info"] = record.stack_info
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для разработки (консоль)"""
    
    # Цвета для уровней
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога с цветами"""
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Добавляем trace_id если есть
        trace_id = get_trace_id()
        trace_info = f" [{trace_id}]" if trace_id else ""
        
        return (
            f"{color}{self.formatTime(record)}{self.RESET} - "
            f"{color}{record.levelname:<8}{self.RESET} - "
            f"{record.name}: {record.getMessage()}"
            f"{trace_info}"
        )


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
    log_to_console: bool = True,
):
    """
    Настраивает логирование
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Использовать JSON формат (True для production)
        log_file: Путь к файлу для записи логов (опционально)
        log_to_console: Выводить логи в консоль
    """
    
    # Определяем, production ли это
    is_production = os.getenv("PRODUCTION", "false").lower() == "true"
    
    # В production всегда используем JSON
    if is_production:
        json_format = True
    
    # Создаем корневой logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Очищаем существующие handlers
    root_logger.handlers.clear()
    
    # Создаем formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter(
            fmt="%(asctime)s - %(levelname)-8s - %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler (если указан файл)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Настройка для uvicorn (если используется)
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access = logging.getLogger("uvicorn.access")
    
    for logger in [uvicorn_logger, uvicorn_access]:
        logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level.upper()))
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Получает logger с указанным именем
    
    Args:
        name: Имя logger (обычно __name__ модуля)
    
    Returns:
        Настроенный logger
    """
    return logging.getLogger(name)


class TracedLogger:
    """Logger с автоматической установкой trace_id"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _log(self, level: int, msg: str, *args, **kwargs):
        """Внутренний метод логирования"""
        # Добавляем trace_id из контекста
        trace_id = get_trace_id()
        if trace_id:
            kwargs.setdefault("extra", {})["trace_id"] = trace_id
        
        self.logger.log(level, msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        kwargs["exc_info"] = True
        self._log(logging.ERROR, msg, *args, **kwargs)


def get_traced_logger(name: str) -> TracedLogger:
    """Получает logger с автоматической установкой trace_id"""
    return TracedLogger(name)