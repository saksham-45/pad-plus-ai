"""
🛡️ InputSanitizer — Модуль санитизации входных данных

Защита от:
- XSS (Cross-Site Scripting) атак
- SQL Injection
- Command Injection
- Path Traversal
- Чрезмерно длинных запросов
- Специальных символов и управляющих последовательностей

Использование:
    from core.input_sanitizer import sanitize_input, validate_input
    
    # Санитизация строки
    clean_text = sanitize_input(user_input)
    
    # Валидация с проверкой
    is_valid, sanitized, errors = validate_input(user_input, max_length=1000)
"""

import re
import html
import logging
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("padplus.sanitizer")


class SanitizerSeverity(Enum):
    """Уровень серьезности обнаруженной угрозы"""
    INFO = "info"           # Информационное
    LOW = "low"             # Низкий риск
    MEDIUM = "medium"       # Средний риск
    HIGH = "high"           # Высокий риск
    CRITICAL = "critical"   # Критический риск
    
    @property
    def level(self) -> int:
        """Числовой уровень для сравнения"""
        levels = {
            "info": 0,
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }
        return levels.get(self.value, 0)
    
    def __lt__(self, other):
        if isinstance(other, SanitizerSeverity):
            return self.level < other.level
        return NotImplemented
    
    def __le__(self, other):
        if isinstance(other, SanitizerSeverity):
            return self.level <= other.level
        return NotImplemented
    
    def __gt__(self, other):
        if isinstance(other, SanitizerSeverity):
            return self.level > other.level
        return NotImplemented
    
    def __ge__(self, other):
        if isinstance(other, SanitizerSeverity):
            return self.level >= other.level
        return NotImplemented


@dataclass
class SanitizationResult:
    """Результат санитизации"""
    original: str
    sanitized: str
    is_safe: bool
    threats_detected: List[Dict[str, Any]] = field(default_factory=list)
    severity: SanitizerSeverity = SanitizerSeverity.INFO
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "original_length": len(self.original),
            "sanitized_length": len(self.sanitized),
            "is_safe": self.is_safe,
            "threats_detected": len(self.threats_detected),
            "severity": self.severity.value,
            "warnings": self.warnings,
            "threats": self.threats_detected
        }


class InputSanitizer:
    """
    🛡️ InputSanitizer — комплексная санитизация входных данных
    
    Функции:
    - HTML-экранирование для защиты от XSS
    - Удаление опасных скриптов и тегов
    - Проверка на SQL injection паттерны
    - Проверка на command injection
    - Ограничение длины ввода
    - Нормализация Unicode символов
    """
    
    # Максимальная длина ввода по умолчанию
    DEFAULT_MAX_LENGTH = 10000
    
    # Опасные HTML теги (полный список)
    DANGEROUS_TAGS = [
        'script', 'iframe', 'object', 'embed', 'applet',
        'form', 'input', 'button', 'textarea', 'select',
        'link', 'meta', 'base', 'style',
        'svg', 'math', 'xml',
        'img[onerror]', 'body[onload]', 'div[onclick]',
    ]
    
    # Паттерны XSS атак
    XSS_PATTERNS = [
        # Script теги и варианты
        r'<\s*script[^>]*>.*?<\s*/\s*script\s*>',
        r'<\s*script[^>]*>',
        r'javascript\s*:',
        r'vbscript\s*:',
        r'data\s*:\s*text/html',
        
        # События (event handlers)
        r'\bon\w+\s*=',  # onclick=, onerror=, onload= и т.д.
        r'\bon\w+\s*\(',  # onclick(, onerror(
        
        # Выражения
        r'expression\s*\(',
        r'eval\s*\(',
        r'alert\s*\(',
        r'document\.cookie',
        r'document\.write',
        r'window\.location',
        
        # SVG/Math XSS
        r'<\s*svg[^>]*on\w+\s*=',
        r'<\s*math[^>]*on\w+\s*=',
        
        # URL с javascript
        r'href\s*=\s*["\']?\s*javascript\s*:',
        r'src\s*=\s*["\']?\s*javascript\s*:',
        r'action\s*=\s*["\']?\s*javascript\s*:',
        
        # Кодированные варианты
        r'&#\d+;\s*c\s*r\s*i\s*p\s*t',
        r'&#x[a-f0-9]+;\s*script',
    ]
    
    # Паттерны SQL Injection
    # ВНИМАНИЕ: Паттерны оптимизированы для уменьшения false positives
    # Они нацелены на реальные атаки, а не на образовательный контент
    SQL_INJECTION_PATTERNS = [
        # Классические SQL инъекции с кавычками (более специфичные)
        r"'\s*OR\s+'[^']*'\s*=\s*'",  # ' OR 'x'='x
        r"'\s*OR\s+\d+\s*=\s*\d+",  # ' OR 1=1
        r'"\s*OR\s+"[^"]*"\s*=\s*"',  # " OR "x"="x
        r'"\s*OR\s+\d+\s*=\s*\d+',  # " OR 1=1
        
        # UNION-based инъекции (только с кавычками или в контексте атаки)
        r"'\s*UNION\s+(ALL\s+)?SELECT\b",
        r'"\s*UNION\s+(ALL\s+)?SELECT\b',
        r";\s*UNION\s+(ALL\s+)?SELECT\b",
        
        # SQL комментарии в конце строки (после других команд)
        r";\s*--\s*$",  # ;-- в конце
        r"'\s*--\s*$",  # '-- в конце (после кавычки)
        
        # Опасные команды с точкой с запятой (разделение команд)
        r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|EXEC|EXECUTE)\b",
        
        # Blind SQL injection с задержками
        r";\s*WAITFOR\s+DELAY\b",
        r";\s*BENCHMARK\s*\(",
        r";\s*SLEEP\s*\(",
        
        # Опасные функции для чтения файлов
        r"\bLOAD_FILE\s*\(",
        r"\bINTO\s+OUTFILE\b",
        r"\bINTO\s+DUMPFILE\b",
        
        # Попытки обхода через CONCAT
        r";\s*CONCAT\s*\(",
        r";\s*CHAR\s*\(",
        r";\s*HEX\s*\(",
    ]
    
    # Паттерны Command Injection
    # Исключаем HTML теги из проверки (они обрабатываются отдельно)
    COMMAND_INJECTION_PATTERNS = [
        r';\s*\w+',         # Semicolon (команды через ;)
        r'&&\s*\w+',        # AND (&&)
        r'\|\|\s*\w+',      # OR (||)
        r'\|\s*\w+',        # Pipe (|)
        r'\$\(',            # Subshell $()
        r'`[^`]+`',         # Backticks
        r'>>\s*[A-Za-z]:',  # Append redirect в диск (Windows)
        r'>\s*[A-Za-z]:',   # Redirect в диск (Windows)
        r'<\s*[A-Za-z]:',   # Input redirect с диска (Windows)
        r'(?<!&)\b(wget|curl|nc|ncat|bash|sh|cmd|powershell)\b',  # Команды (не после &)
        r'\b(rm|del|format|mkfs)\b\s+[-/]',  # Опасные команды
    ]
    
    # Паттерны Path Traversal
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',          # ../
        r'\.\.\\',         # ..\
        r'%2e%2e[/%5c]',   # URL-encoded
        r'\.\.%2f',        # Смешанное
        r'%2e%2e%2f',      # Полностью URL-encoded
        r'/etc/passwd',
        r'/etc/shadow',
        r'\\windows\\',
        r'\\winnt\\',
    ]
    
    # Паттерны для email валидации
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def __init__(
        self,
        max_length: int = DEFAULT_MAX_LENGTH,
        allow_html: bool = False,
        strict_mode: bool = False
    ):
        """
        Инициализация санитизатора
        
        Args:
            max_length: Максимальная длина ввода
            allow_html: Разрешить ли HTML теги (безопасные)
            strict_mode: Строгий режим (блокирует больше паттернов)
        """
        self.max_length = max_length
        self.allow_html = allow_html
        self.strict_mode = strict_mode
        
        # Компилируем паттерны для производительности
        self._xss_regex = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.XSS_PATTERNS]
        self._sql_regex = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self._cmd_regex = [re.compile(p, re.IGNORECASE) for p in self.COMMAND_INJECTION_PATTERNS]
        self._path_regex = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]
        
        # Безопасные HTML теги (если allow_html=True)
        self.safe_tags = ['b', 'i', 'u', 'strong', 'em', 'p', 'br', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        
        logger.info(f"🛡️ InputSanitizer initialized: max_length={max_length}, allow_html={allow_html}, strict={strict_mode}")
    
    def sanitize(self, text: str, context: str = "general") -> SanitizationResult:
        """
        Комплексная санитизация входных данных
        
        Args:
            text: Входной текст
            context: Контекст использования (general, email, url, sql, html)
        
        Returns:
            SanitizationResult с очищенным текстом и информацией об угрозах
        """
        if not text:
            return SanitizationResult(
                original="",
                sanitized="",
                is_safe=True
            )
        
        original = text
        threats = []
        warnings = []
        severity = SanitizerSeverity.INFO
        
        # 1. Проверка длины
        if len(text) > self.max_length:
            text = text[:self.max_length]
            warnings.append(f"Текст обрезан до {self.max_length} символов")
            severity = SanitizerSeverity.LOW
        
        # 2. Нормализация Unicode
        text = self._normalize_unicode(text)
        
        # 3. Проверка на XSS
        xss_threats = self._check_xss(text)
        if xss_threats:
            threats.extend(xss_threats)
            severity = max(severity, SanitizerSeverity.HIGH)
        
        # 4. Проверка на SQL Injection (если контекст подходит)
        if context in ("sql", "general", "api"):
            sql_threats = self._check_sql_injection(text)
            if sql_threats:
                threats.extend(sql_threats)
                severity = max(severity, SanitizerSeverity.CRITICAL)
        
        # 5. Проверка на Command Injection
        cmd_threats = self._check_command_injection(text)
        if cmd_threats:
            threats.extend(cmd_threats)
            severity = max(severity, SanitizerSeverity.CRITICAL)
        
        # 6. Проверка на Path Traversal
        path_threats = self._check_path_traversal(text)
        if path_threats:
            threats.extend(path_threats)
            severity = max(severity, SanitizerSeverity.HIGH)
        
        # 7. HTML-экранирование
        if not self.allow_html:
            text = html.escape(text, quote=True)
        else:
            # Удаляем только опасные теги
            text = self._remove_dangerous_tags(text)
        
        # 8. Удаление нулевых символов
        text = text.replace('\x00', '')
        
        # 9. Удаление управляющих символов (кроме стандартных)
        text = self._remove_control_chars(text)
        
        # 10. Окончательная очистка
        text = text.strip()
        
        is_safe = severity not in (SanitizerSeverity.HIGH, SanitizerSeverity.CRITICAL)
        
        result = SanitizationResult(
            original=original,
            sanitized=text,
            is_safe=is_safe,
            threats_detected=threats,
            severity=severity,
            warnings=warnings
        )
        
        if not is_safe:
            logger.warning(
                f"🛡️ Sanitizer: Обнаружены угрозы ({severity.value}) - "
                f"угроз: {len(threats)}, текст: {original[:100]}..."
            )
        
        return result
    
    def sanitize_email(self, email: str) -> Tuple[bool, str]:
        """
        Валидация и санитизация email
        
        Returns:
            (is_valid, sanitized_email)
        """
        if not email:
            return False, ""
        
        # Удаляем пробелы
        email = email.strip()
        
        # Проверяем длину
        if len(email) > 254:
            return False, ""
        
        # HTML-экранирование не нужно для email, просто проверяем паттерн
        if re.match(self.EMAIL_PATTERN, email):
            return True, email.lower()
        
        return False, ""
    
    def sanitize_for_sql(self, value: Any) -> str:
        """
        Санитизация значения для использования в SQL
        
        Примечание: Это дополнительная защита. Основные запросы должны
        использовать параметризованные запросы (query parameters).
        """
        if value is None:
            return ""
        
        text = str(value)
        
        # Экранируем специальные символы SQL
        text = text.replace("'", "''")
        text = text.replace("\\", "\\\\")
        text = text.replace('"', '\\"')
        text = text.replace("\x00", "")
        
        return text
    
    def _normalize_unicode(self, text: str) -> str:
        """Нормализация Unicode символов"""
        import unicodedata
        
        # Нормализуем к форме NFKC (совместимость + каноническая композиция)
        text = unicodedata.normalize('NFKC', text)
        
        return text
    
    def _check_xss(self, text: str) -> List[Dict[str, Any]]:
        """Проверка на XSS паттерны"""
        threats = []
        
        for i, pattern in enumerate(self._xss_regex):
            matches = pattern.findall(text)
            if matches:
                threats.append({
                    "type": "xss",
                    "pattern": self.XSS_PATTERNS[i][:50],
                    "matches": len(matches),
                    "severity": "high"
                })
        
        return threats
    
    def _check_sql_injection(self, text: str) -> List[Dict[str, Any]]:
        """Проверка на SQL Injection паттерны"""
        threats = []
        
        for i, pattern in enumerate(self._sql_regex):
            matches = pattern.findall(text)
            if matches:
                threats.append({
                    "type": "sql_injection",
                    "pattern": self.SQL_INJECTION_PATTERNS[i][:50],
                    "matches": len(matches),
                    "severity": "critical"
                })
        
        return threats
    
    def _check_command_injection(self, text: str) -> List[Dict[str, Any]]:
        """Проверка на Command Injection паттерны"""
        threats = []
        
        for i, pattern in enumerate(self._cmd_regex):
            matches = pattern.findall(text)
            if matches:
                threats.append({
                    "type": "command_injection",
                    "pattern": self.COMMAND_INJECTION_PATTERNS[i][:50],
                    "matches": len(matches),
                    "severity": "critical"
                })
        
        return threats
    
    def _check_path_traversal(self, text: str) -> List[Dict[str, Any]]:
        """Проверка на Path Traversal паттерны"""
        threats = []
        
        for i, pattern in enumerate(self._path_regex):
            matches = pattern.findall(text)
            if matches:
                threats.append({
                    "type": "path_traversal",
                    "pattern": self.PATH_TRAVERSAL_PATTERNS[i][:50],
                    "matches": len(matches),
                    "severity": "high"
                })
        
        return threats
    
    def _remove_dangerous_tags(self, text: str) -> str:
        """Удаление опасных HTML тегов"""
        # Удаляем все теги кроме безопасных
        if self.allow_html:
            # Простая реализация - удаляем все теги script, style и т.д.
            for tag in ['script', 'style', 'iframe', 'object', 'embed']:
                text = re.sub(
                    f'<{tag}[^>]*>.*?</{tag}>',
                    '',
                    text,
                    flags=re.IGNORECASE | re.DOTALL
                )
                text = re.sub(f'<{tag}[^>]*>', '', text, flags=re.IGNORECASE)
        
        return text
    
    def _remove_control_chars(self, text: str) -> str:
        """Удаление управляющих символов"""
        # Разрешаем только стандартные: \n, \r, \t
        control_chars = [
            chr(i) for i in range(32)
            if chr(i) not in ('\n', '\r', '\t')
        ]
        
        for char in control_chars:
            text = text.replace(char, '')
        
        return text


# Глобальный экземпляр
_sanitizer: Optional[InputSanitizer] = None


def get_sanitizer() -> InputSanitizer:
    """Возвращает глобальный санитизатор"""
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = InputSanitizer()
    return _sanitizer


def sanitize_input(
    text: str,
    context: str = "general",
    max_length: Optional[int] = None
) -> str:
    """
    Быстрая санитизация входных данных
    
    Args:
        text: Входной текст
        context: Контекст (general, email, url, sql, html)
        max_length: Максимальная длина (переопределяет настройку по умолчанию)
    
    Returns:
        Очищенный текст
    """
    sanitizer = get_sanitizer()
    if max_length is not None:
        # Временное переопределение
        original_max = sanitizer.max_length
        sanitizer.max_length = max_length
        result = sanitizer.sanitize(text, context)
        sanitizer.max_length = original_max
        return result.sanitized
    
    return sanitizer.sanitize(text, context).sanitized


def validate_input(
    text: str,
    max_length: Optional[int] = None,
    context: str = "general"
) -> Tuple[bool, str, List[str]]:
    """
    Валидация входных данных
    
    Args:
        text: Входной текст
        max_length: Максимальная длина
        context: Контекст
    
    Returns:
        (is_safe, sanitized_text, warnings)
    """
    sanitizer = get_sanitizer()
    if max_length is not None:
        original_max = sanitizer.max_length
        sanitizer.max_length = max_length
        result = sanitizer.sanitize(text, context)
        sanitizer.max_length = original_max
    else:
        result = sanitizer.sanitize(text, context)
    
    return result.is_safe, result.sanitized, result.warnings


def reset_sanitizer():
    """Сбрасывает глобальный санитизатор (для тестов)"""
    global _sanitizer
    _sanitizer = None