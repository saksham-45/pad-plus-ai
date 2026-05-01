"""
Tests for Custom Exceptions module

Проверка иерархии исключений:
- Базовые исключения
- Специфичные типы
- Метод to_dict()
- Helper функции
"""

import pytest
import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.exceptions import (
    PADException,
    SecurityException,
    CSRFValidationException,
    InputValidationException,
    AuthenticationException,
    AuthorizationException,
    EncryptionException,
    DatabaseException,
    ConnectionException,
    QueryException,
    CircuitBreakerException,
    LLMException,
    LLMConfigurationException,
    LLMRateLimitException,
    LLMTimeoutException,
    LLMAuthenticationException,
    MemoryException,
    MemoryStorageException,
    MemoryRetrievalException,
    PipelineException,
    PipelineStageException,
    PipelineTimeoutException,
    ValidationException,
    ConfigurationException,
    MissingRequiredFieldException,
    InvalidValueException,
    ResourceException,
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    handle_exception,
    raise_for_condition,
)


class TestBaseException:
    """Тесты для базового исключения"""
    
    def test_pad_exception_creation(self):
        """Создание базового исключения"""
        exc = PADException("Test error")
        assert exc.message == "Test error"
        assert exc.code == "unknown_error"
        assert exc.details == {}
    
    def test_pad_exception_with_code(self):
        """Создание исключения с кодом"""
        exc = PADException("Test error", code="test_code")
        assert exc.code == "test_code"
    
    def test_pad_exception_with_details(self):
        """Создание исключения с деталями"""
        exc = PADException("Test error", details={"key": "value"})
        assert exc.details == {"key": "value"}
    
    def test_pad_exception_to_dict(self):
        """Конвертация в словарь"""
        exc = PADException("Test error", code="test_code", details={"key": "value"})
        result = exc.to_dict()
        
        assert result["error"] == "PADException"
        assert result["code"] == "test_code"
        assert result["message"] == "Test error"
        assert result["details"] == {"key": "value"}
    
    def test_pad_exception_string(self):
        """Строковое представление"""
        exc = PADException("Test error")
        assert str(exc) == "Test error"


class TestSecurityExceptions:
    """Тесты для исключений безопасности"""
    
    def test_csrf_validation_exception(self):
        """CSRFValidationException"""
        exc = CSRFValidationException()
        assert exc.code == "csrf_validation_failed"
        assert isinstance(exc, SecurityException)
        assert isinstance(exc, PADException)
    
    def test_input_validation_exception(self):
        """InputValidationException"""
        exc = InputValidationException()
        assert exc.code == "input_validation_failed"
    
    def test_authentication_exception(self):
        """AuthenticationException"""
        exc = AuthenticationException()
        assert exc.code == "authentication_failed"
    
    def test_authorization_exception(self):
        """AuthorizationException"""
        exc = AuthorizationException()
        assert exc.code == "authorization_failed"
    
    def test_encryption_exception(self):
        """EncryptionException"""
        exc = EncryptionException()
        assert exc.code == "encryption_failed"


class TestDatabaseExceptions:
    """Тесты для исключений БД"""
    
    def test_connection_exception(self):
        """ConnectionException"""
        exc = ConnectionException()
        assert exc.code == "connection_failed"
        assert isinstance(exc, DatabaseException)
    
    def test_query_exception(self):
        """QueryException"""
        exc = QueryException()
        assert exc.code == "query_failed"
    
    def test_circuit_breaker_exception(self):
        """CircuitBreakerException"""
        exc = CircuitBreakerException()
        assert exc.code == "circuit_breaker_open"


class TestLLMExceptions:
    """Тесты для исключений LLM"""
    
    def test_llm_configuration_exception(self):
        """LLMConfigurationException"""
        exc = LLMConfigurationException()
        assert exc.code == "llm_configuration_error"
        assert isinstance(exc, LLMException)
    
    def test_llm_rate_limit_exception(self):
        """LLMRateLimitException"""
        exc = LLMRateLimitException()
        assert exc.code == "llm_rate_limit_exceeded"
    
    def test_llm_timeout_exception(self):
        """LLMTimeoutException"""
        exc = LLMTimeoutException()
        assert exc.code == "llm_timeout"
    
    def test_llm_authentication_exception(self):
        """LLMAuthenticationException"""
        exc = LLMAuthenticationException()
        assert exc.code == "llm_authentication_failed"


class TestMemoryExceptions:
    """Тесты для исключений памяти"""
    
    def test_memory_storage_exception(self):
        """MemoryStorageException"""
        exc = MemoryStorageException()
        assert exc.code == "memory_storage_failed"
        assert isinstance(exc, MemoryException)
    
    def test_memory_retrieval_exception(self):
        """MemoryRetrievalException"""
        exc = MemoryRetrievalException()
        assert exc.code == "memory_retrieval_failed"


class TestPipelineExceptions:
    """Тесты для исключений пайплайна"""
    
    def test_pipeline_stage_exception(self):
        """PipelineStageException"""
        exc = PipelineStageException(stage="safety", message="Safety check failed")
        assert exc.code == "pipeline_stage_failed"
        assert exc.details["stage"] == "safety"
        assert isinstance(exc, PipelineException)
    
    def test_pipeline_timeout_exception(self):
        """PipelineTimeoutException"""
        exc = PipelineTimeoutException()
        assert exc.code == "pipeline_timeout"


class TestValidationExceptions:
    """Тесты для исключений валидации"""
    
    def test_configuration_exception(self):
        """ConfigurationException"""
        exc = ConfigurationException()
        assert exc.code == "configuration_error"
        assert isinstance(exc, ValidationException)
    
    def test_missing_required_field_exception(self):
        """MissingRequiredFieldException"""
        exc = MissingRequiredFieldException(field="email")
        assert exc.code == "required_field_missing"
        assert exc.details["field"] == "email"
    
    def test_invalid_value_exception(self):
        """InvalidValueException"""
        exc = InvalidValueException(field="age", value=-5)
        assert exc.code == "invalid_value"
        assert exc.details["field"] == "age"
        assert exc.details["value"] == "-5"


class TestResourceExceptions:
    """Тесты для исключений ресурсов"""
    
    def test_resource_not_found_exception(self):
        """ResourceNotFoundException"""
        exc = ResourceNotFoundException(resource_type="User", resource_id="123")
        assert exc.code == "resource_not_found"
        assert exc.details["resource_type"] == "User"
        assert exc.details["resource_id"] == "123"
        assert "not found" in exc.message.lower()
        assert isinstance(exc, ResourceException)
    
    def test_resource_already_exists_exception(self):
        """ResourceAlreadyExistsException"""
        exc = ResourceAlreadyExistsException(resource_type="User", resource_id="123")
        assert exc.code == "resource_already_exists"
        assert exc.details["resource_type"] == "User"
        assert exc.details["resource_id"] == "123"
        assert "already exists" in exc.message.lower()


class TestHelperFunctions:
    """Тесты для вспомогательных функций"""
    
    def test_handle_exception_with_pad_exception(self):
        """handle_exception с PADException"""
        exc = CSRFValidationException("CSRF failed")
        result = handle_exception(exc)
        
        assert result["error"] == "CSRFValidationException"
        assert result["code"] == "csrf_validation_failed"
        assert result["message"] == "CSRF failed"
    
    def test_handle_exception_with_standard_exception(self):
        """handle_exception со стандартным исключением"""
        exc = ValueError("Invalid value")
        result = handle_exception(exc)
        
        assert result["error"] == "ValueError"
        assert result["code"] == "internal_error"
        assert result["message"] == "Invalid value"
    
    def test_raise_for_condition_true(self):
        """raise_for_condition с истинным условием"""
        # Не должно выбрасывать исключение
        raise_for_condition(True, ValueError, "Should not raise")
    
    def test_raise_for_condition_false(self):
        """raise_for_condition с ложным условием"""
        with pytest.raises(AuthenticationException):
            raise_for_condition(False, AuthenticationException, "Not authenticated")
    
    def test_raise_for_condition_with_details(self):
        """raise_for_condition с деталями"""
        # Используем DatabaseException который принимает только message
        with pytest.raises(DatabaseException) as exc_info:
            raise_for_condition(
                False,
                DatabaseException,
                "Database error",
                details={"db": "postgres", "operation": "query"}
            )
        assert exc_info.value.details["db"] == "postgres"
        assert exc_info.value.details["operation"] == "query"


class TestExceptionHierarchy:
    """Тесты иерархии исключений"""
    
    def test_all_exceptions_inherit_from_pad_exception(self):
        """Все исключения наследуются от PADException"""
        exceptions = [
            SecurityException,
            CSRFValidationException,
            DatabaseException,
            ConnectionException,
            LLMException,
            MemoryException,
            PipelineException,
            ValidationException,
            ResourceException,
        ]
        
        for exc_class in exceptions:
            exc = exc_class("Test")
            assert isinstance(exc, PADException)
    
    def test_catch_by_base_class(self):
        """Можно ловить по базовому классу"""
        try:
            raise CSRFValidationException("CSRF failed")
        except SecurityException as e:
            assert isinstance(e, CSRFValidationException)
            assert e.code == "csrf_validation_failed"
    
    def test_catch_by_specific_class(self):
        """Можно ловить по специфичному классу"""
        try:
            raise ConnectionException("DB failed")
        except ConnectionException as e:
            assert e.code == "connection_failed"
    
    def test_catch_database_exceptions(self):
        """Можно ловить все DatabaseException"""
        database_exceptions = [
            ConnectionException,
            QueryException,
            CircuitBreakerException,
        ]
        
        for exc_class in database_exceptions:
            try:
                raise exc_class("Test")
            except DatabaseException as e:
                assert isinstance(e, exc_class)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])