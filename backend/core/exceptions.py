"""
🛡️ Custom Exceptions — Иерархия исключений PAD+ AI

Централизованное управление ошибками:
- Четкая иерархия исключений
- Специфичные типы ошибок
- Информативные сообщения
- Легкая обработка в коде

Использование:
    from core.exceptions import (
        PADException,
        SecurityException,
        ValidationException,
    )
    
    try:
        # some code
    except ValidationException as e:
        logger.error(f"Validation error: {e}")
"""

from typing import Any, Dict, Optional


class PADException(Exception):
    """Базовое исключение для всех исключений PAD+ AI"""
    
    def __init__(
        self, 
        message: str, 
        code: str = "unknown_error",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для логирования/API"""
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


# ============================================================================
# SECURITY EXCEPTIONS
# ============================================================================

class SecurityException(PADException):
    """Базовое исключение для ошибок безопасности"""
    pass


class CSRFValidationException(SecurityException):
    """CSRF токен не прошел валидацию"""
    def __init__(self, message: str = "CSRF validation failed", **kwargs):
        super().__init__(message, code="csrf_validation_failed", **kwargs)


class InputValidationException(SecurityException):
    """Входные данные не прошли валидацию"""
    def __init__(self, message: str = "Input validation failed", **kwargs):
        super().__init__(message, code="input_validation_failed", **kwargs)


class AuthenticationException(SecurityException):
    """Ошибка аутентификации"""
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, code="authentication_failed", **kwargs)


class AuthorizationException(SecurityException):
    """Ошибка авторизации (нет прав)"""
    def __init__(self, message: str = "Authorization failed", **kwargs):
        super().__init__(message, code="authorization_failed", **kwargs)


class EncryptionException(SecurityException):
    """Ошибка шифрования/дешифрования"""
    def __init__(self, message: str = "Encryption operation failed", **kwargs):
        super().__init__(message, code="encryption_failed", **kwargs)


# ============================================================================
# DATABASE EXCEPTIONS
# ============================================================================

class DatabaseException(PADException):
    """Базовое исключение для ошибок БД"""
    pass


class ConnectionException(DatabaseException):
    """Ошибка подключения к БД"""
    def __init__(self, message: str = "Database connection failed", **kwargs):
        super().__init__(message, code="connection_failed", **kwargs)


class QueryException(DatabaseException):
    """Ошибка выполнения запроса"""
    def __init__(self, message: str = "Database query failed", **kwargs):
        super().__init__(message, code="query_failed", **kwargs)


class CircuitBreakerException(DatabaseException):
    """Circuit Breaker открыт"""
    def __init__(self, message: str = "Circuit breaker is open", **kwargs):
        super().__init__(message, code="circuit_breaker_open", **kwargs)


# ============================================================================
# LLM EXCEPTIONS
# ============================================================================

class LLMException(PADException):
    """Базовое исключение для ошибок LLM"""
    pass


class LLMConfigurationException(LLMException):
    """Ошибка конфигурации LLM"""
    def __init__(self, message: str = "LLM configuration error", **kwargs):
        super().__init__(message, code="llm_configuration_error", **kwargs)


class LLMRateLimitException(LLMException):
    """Превышен лимит запросов к LLM"""
    def __init__(self, message: str = "LLM rate limit exceeded", **kwargs):
        super().__init__(message, code="llm_rate_limit_exceeded", **kwargs)


class LLMTimeoutException(LLMException):
    """Истекло время ожидания ответа от LLM"""
    def __init__(self, message: str = "LLM request timeout", **kwargs):
        super().__init__(message, code="llm_timeout", **kwargs)


class LLMAuthenticationException(LLMException):
    """Ошибка аутентификации LLM API"""
    def __init__(self, message: str = "LLM API authentication failed", **kwargs):
        super().__init__(message, code="llm_authentication_failed", **kwargs)


# ============================================================================
# MEMORY EXCEPTIONS
# ============================================================================

class MemoryException(PADException):
    """Базовое исключение для ошибок памяти"""
    pass


class MemoryStorageException(MemoryException):
    """Ошибка хранения данных в памяти"""
    def __init__(self, message: str = "Memory storage operation failed", **kwargs):
        super().__init__(message, code="memory_storage_failed", **kwargs)


class MemoryRetrievalException(MemoryException):
    """Ошибка получения данных из памяти"""
    def __init__(self, message: str = "Memory retrieval failed", **kwargs):
        super().__init__(message, code="memory_retrieval_failed", **kwargs)


# ============================================================================
# PIPELINE EXCEPTIONS
# ============================================================================

class PipelineException(PADException):
    """Базовое исключение for ошибок пайплайна"""
    pass


class PipelineStageException(PipelineException):
    """Ошибка выполнения стадии пайплайна"""
    def __init__(self, stage: str, message: str = "Pipeline stage failed", **kwargs):
        kwargs.setdefault("details", {})["stage"] = stage
        super().__init__(message, code="pipeline_stage_failed", **kwargs)


class PipelineTimeoutException(PipelineException):
    """Истекло время выполнения пайплайна"""
    def __init__(self, message: str = "Pipeline execution timeout", **kwargs):
        super().__init__(message, code="pipeline_timeout", **kwargs)


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class ValidationException(PADException):
    """Базовое исключение для ошибок валидации"""
    pass


class ConfigurationException(ValidationException):
    """Ошибка конфигурации"""
    def __init__(self, message: str = "Configuration error", **kwargs):
        super().__init__(message, code="configuration_error", **kwargs)


class MissingRequiredFieldException(ValidationException):
    """Отсутствует обязательное поле"""
    def __init__(self, field: str, message: str = "Required field missing", **kwargs):
        kwargs.setdefault("details", {})["field"] = field
        super().__init__(message, code="required_field_missing", **kwargs)


class InvalidValueException(ValidationException):
    """Неверное значение"""
    def __init__(self, field: str, value: Any, message: str = "Invalid value", **kwargs):
        kwargs.setdefault("details", {})["field"] = field
        kwargs.setdefault("details", {})["value"] = str(value)
        super().__init__(message, code="invalid_value", **kwargs)


# ============================================================================
# RESOURCE EXCEPTIONS
# ============================================================================

class ResourceException(PADException):
    """Базовое исключение для ошибок ресурсов"""
    pass


class ResourceNotFoundException(ResourceException):
    """Ресурс не найден"""
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        message = f"{resource_type} with id '{resource_id}' not found"
        kwargs.setdefault("details", {})["resource_type"] = resource_type
        kwargs.setdefault("details", {})["resource_id"] = resource_id
        super().__init__(message, code="resource_not_found", **kwargs)


class ResourceAlreadyExistsException(ResourceException):
    """Ресурс уже существует"""
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        message = f"{resource_type} with id '{resource_id}' already exists"
        kwargs.setdefault("details", {})["resource_type"] = resource_type
        kwargs.setdefault("details", {})["resource_id"] = resource_id
        super().__init__(message, code="resource_already_exists", **kwargs)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def handle_exception(exc: Exception) -> Dict[str, Any]:
    """
    Универсальная обработка исключений
    
    Args:
        exc: Исключение для обработки
    
    Returns:
        Словарь с информацией об ошибке
    """
    if isinstance(exc, PADException):
        return exc.to_dict()
    
    # Для стандартных исключений
    return {
        "error": type(exc).__name__,
        "code": "internal_error",
        "message": str(exc),
        "details": {}
    }


def raise_for_condition(
    condition: bool,
    exception_class: type,
    message: str,
    **kwargs
):
    """
    Выбрасывает исключение если условие не выполнено
    
    Usage:
        raise_for_condition(
            user is not None,
            AuthenticationException,
            "User not authenticated"
        )
    """
    if not condition:
        raise exception_class(message, **kwargs)