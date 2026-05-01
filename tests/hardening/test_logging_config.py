"""
🧪 Тесты для Structured Logging

Проверяет:
- JSON формат
- Colored формат
- Trace ID
- TracedLogger
"""

import pytest
import json
import logging
import sys
from pathlib import Path
from io import StringIO

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.logging_config import (
    setup_logging,
    get_logger,
    get_traced_logger,
    set_trace_id,
    get_trace_id,
    JSONFormatter,
    ColoredFormatter,
)


@pytest.fixture(autouse=True)
def reset_logging():
    """Сбрасывает логирование после каждого теста"""
    yield
    # Сброс trace_id
    set_trace_id(None)
    # Сброс logging
    logging.getLogger().handlers.clear()


class TestJSONFormatter:
    """Тесты JSON форматтера"""
    
    def test_json_format_basic(self):
        """Базовый JSON формат"""
        formatter = JSONFormatter()
        
        # Создаем запись лога
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data
        assert "module" in data
    
    def test_json_format_with_extra_fields(self):
        """JSON формат с дополнительными полями"""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.user_id = 123
        record.request_id = "abc-123"
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["user_id"] == 123
        assert data["request_id"] == "abc-123"
    
    def test_json_format_with_exception(self):
        """JSON формат с исключением"""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "Test error"
        assert "traceback" in data["exception"]


class TestColoredFormatter:
    """Тесты цветного форматтера"""
    
    def test_colored_format(self):
        """Цветной формат"""
        formatter = ColoredFormatter()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        
        # Проверяем наличие ANSI цветов
        assert "\033[" in output
        assert "INFO" in output
        assert "Test message" in output


class TestTraceId:
    """Тесты trace_id"""
    
    def test_set_and_get_trace_id(self):
        """Установка и получение trace_id"""
        set_trace_id("test-trace-123")
        assert get_trace_id() == "test-trace-123"
    
    def test_trace_id_in_json_log(self):
        """Trace_id в JSON логе"""
        set_trace_id("test-trace-456")
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["trace_id"] == "test-trace-456"
    
    def test_no_trace_id_when_not_set(self):
        """Нет trace_id когда не установлен"""
        set_trace_id(None)
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "trace_id" not in data


class TestSetupLogging:
    """Тесты настройки логирования"""
    
    def test_setup_logging_console(self):
        """Настройка логирования в консоль"""
        setup_logging(level="INFO", json_format=False, log_to_console=True)
        
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) >= 1
    
    def test_setup_logging_json(self):
        """Настройка JSON логирования"""
        setup_logging(level="INFO", json_format=True, log_to_console=True)
        
        root_logger = logging.getLogger()
        # Проверяем, что handler использует JSONFormatter
        for handler in root_logger.handlers:
            assert isinstance(handler.formatter, JSONFormatter)


class TestTracedLogger:
    """Тесты TracedLogger"""
    
    def test_traced_logger_basic(self):
        """Базовое логирование через TracedLogger"""
        setup_logging(level="INFO", json_format=True, log_to_console=False)
        
        logger = get_traced_logger("test_module")
        
        # Логируем в StringIO для проверки
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logging.getLogger("test_module").addHandler(handler)
        
        logger.info("Test message")
        
        output = stream.getvalue()
        data = json.loads(output)
        
        assert data["message"] == "Test message"
        assert data["logger"] == "test_module"
    
    def test_traced_logger_with_trace_id(self):
        """TracedLogger с trace_id"""
        setup_logging(level="INFO", json_format=True, log_to_console=False)
        set_trace_id("my-trace-id")
        
        logger = get_traced_logger("test_module")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logging.getLogger("test_module").addHandler(handler)
        
        logger.info("Test message")
        
        output = stream.getvalue()
        data = json.loads(output)
        
        assert data["trace_id"] == "my-trace-id"
    
    def test_traced_logger_exception(self):
        """TracedLogger с исключением"""
        setup_logging(level="INFO", json_format=True, log_to_console=False)
        
        logger = get_traced_logger("test_module")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logging.getLogger("test_module").addHandler(handler)
        
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("Error occurred")
        
        output = stream.getvalue()
        data = json.loads(output)
        
        assert "exception" in data


class TestGetLogger:
    """Тесты get_logger"""
    
    def test_get_logger(self):
        """Получение logger"""
        logger = get_logger("my_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "my_module"