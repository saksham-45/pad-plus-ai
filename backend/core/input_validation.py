"""
🔍 Input Validation для PAD+ AI

Обеспечивает валидацию и санитизацию входных данных:
- Pydantic модели для API
- Санитизация строк
- Проверка на инъекции
- Валидация файлов
"""

import re
import html
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator, Field, HttpUrl
from pydantic.config import ConfigDict

logger = logging.getLogger("padplus.validation")

# Список опасных паттернов для инъекций
DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # XSS
    r'javascript:',               # JavaScript URL
    r'on\w+\s*=',                # Event handlers
    r'expression\s*\(',          # CSS expression
    r'@import',                  # CSS import
    r'union\s+select',           # SQL injection
    r'drop\s+table',             # SQL injection
    r'insert\s+into',            # SQL injection
    r'delete\s+from',            # SQL injection
    r'exec\s*\(',                # Code execution
    r'eval\s*\(',                # Code execution
    r'system\s*\(',              # Code execution
]

class SecurityValidator:
    """Валидатор безопасности входных данных"""
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 10000) -> str:
        """Санитизация строки"""
        if not text:
            return ""
        
        # Ограничиваем длину
        text = text[:max_length]
        
        # HTML escaping
        text = html.escape(text)
        
        # Удаляем опасные паттерны
        for pattern in DANGEROUS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Удаляем null bytes
        text = text.replace('\x00', '')
        
        return text.strip()
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Валидация API ключа"""
        if not api_key:
            return False
        
        # Базовая проверка формата
        if len(api_key) < 10 or len(api_key) > 500:
            return False
        
        # Проверка на опасные символы
        dangerous_chars = ['<', '>', '&', '"', "'", '\x00']
        if any(char in api_key for char in dangerous_chars):
            return False
        
        return True
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Валидация email"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Валидация URL"""
        if not url:
            return False
        
        # Базовая проверка
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Проверка на dangerous протоколы
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:']
        if any(protocol in url.lower() for protocol in dangerous_protocols):
            return False
        
        return True

# Pydantic модели для API

class APIKeyCreate(BaseModel):
    """Модель для создания API ключа"""
    provider: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=10, max_length=500)
    model_preference: Optional[str] = Field(None, max_length=100)
    is_default: bool = False
    
    @validator('provider')
    def validate_provider(cls, v):
        allowed_providers = ['openrouter', 'gigachat']
        if v.lower() not in allowed_providers:
            raise ValueError(f'Provider must be one of: {", ".join(allowed_providers)}')
        return v.lower()
    
    @validator('name')
    def validate_name(cls, v):
        return SecurityValidator.sanitize_string(v, max_length=100)
    
    @validator('api_key')
    def validate_api_key_field(cls, v):
        if not SecurityValidator.validate_api_key(v):
            raise ValueError('Invalid API key format')
        return v

class APIKeyUpdate(BaseModel):
    """Модель для обновления API ключа"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    model_preference: Optional[str] = Field(None, max_length=100)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            return SecurityValidator.sanitize_string(v, max_length=100)
        return v

class ChatMessage(BaseModel):
    """Модель для сообщения в чате"""
    content: str = Field(..., min_length=1, max_length=10000)
    role: str = Field("user", pattern="^(user|assistant|system)$")
    
    @validator('content')
    def validate_content(cls, v):
        return SecurityValidator.sanitize_string(v, max_length=10000)

class ChatRequest(BaseModel):
    """Модель для запроса чата"""
    messages: List[ChatMessage] = Field(..., min_items=1, max_items=50)
    model: Optional[str] = Field(None, max_length=100)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    stream: bool = False
    key_id: Optional[str] = None
    provider: Optional[str] = None
    auto_mode: bool = False
    explain: bool = False  # === COGNITIVE UX: Возвращать полные мета-данные ===
    
    @property
    def text(self) -> str:
        """Возвращает текст первого сообщения"""
        return self.messages[0].content if self.messages else ""
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError('At least one message is required')
        return v

class UserRegister(BaseModel):
    """Модель для регистрации пользователя"""
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)
    
    @validator('email')
    def validate_email(cls, v):
        if not SecurityValidator.validate_email(v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if v is not None:
            return SecurityValidator.sanitize_string(v, max_length=100)
        return v

class UserLogin(BaseModel):
    """Модель для входа пользователя"""
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    
    @validator('email')
    def validate_email(cls, v):
        if not SecurityValidator.validate_email(v):
            raise ValueError('Invalid email format')
        return v.lower()

class DocumentUpload(BaseModel):
    """Модель для загрузки документа"""
    filename: str = Field(..., max_length=255)
    content_type: str = Field(..., max_length=100)
    size: int = Field(..., ge=1, le=50 * 1024 * 1024)  # 50MB max
    
    @validator('filename')
    def validate_filename(cls, v):
        # Проверка на опасные символы в имени файла
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in v for char in dangerous_chars):
            raise ValueError('Filename contains dangerous characters')
        return SecurityValidator.sanitize_string(v, max_length=255)
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = [
            'text/plain', 'text/html', 'text/css', 'text/javascript',
            'application/json', 'application/xml',
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        if v not in allowed_types:
            raise ValueError(f'Content type not allowed. Allowed types: {", ".join(allowed_types)}')
        return v

class SearchQuery(BaseModel):
    """Модель для поискового запроса"""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)
    
    @validator('query')
    def validate_query(cls, v):
        return SecurityValidator.sanitize_string(v, max_length=500)

class ProviderConfig(BaseModel):
    """Модель для конфигурации провайдера"""
    provider_id: str = Field(..., max_length=50)
    config: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('provider_id')
    def validate_provider_id(cls, v):
        allowed_providers = ['openrouter', 'gigachat']
        if v.lower() not in allowed_providers:
            raise ValueError(f'Provider must be one of: {", ".join(allowed_providers)}')
        return v.lower()

# Утилиты для валидации

def validate_and_sanitize_input(data: Any, model_class: BaseModel) -> Any:
    """
    Валидирует и санитизирует входные данные
    
    Args:
        data: Входные данные
        model_class: Pydantic модель для валидации
        
    Returns:
        Валидированные данные
        
    Raises:
        ValueError: Если данные невалидны
    """
    try:
        if isinstance(data, dict):
            return model_class(**data)
        else:
            return model_class.model_validate(data)
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise ValueError(f"Invalid input data: {str(e)}")

def check_for_injection_attempt(input_string: str) -> bool:
    """
    Проверяет строку на попытку инъекции
    
    Args:
        input_string: Входная строка
        
    Returns:
        True если обнаружена попытка инъекции
    """
    if not input_string:
        return False
    
    input_lower = input_string.lower()
    
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, input_lower):
            logger.warning(f"Potential injection detected: {pattern}")
            return True
    
    return False

def sanitize_filename(filename: str) -> str:
    """
    Санитизирует имя файла
    
    Args:
        filename: Имя файла
        
    Returns:
        Санитизированное имя файла
    """
    if not filename:
        return "unnamed"
    
    # Удаляем путь
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Удаляем опасные символы
    dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Ограничиваем длину
    filename = filename[:255]
    
    return filename or "unnamed"
