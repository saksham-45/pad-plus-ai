# RULES.md — Правила кодирования
## Стандарты разработки 

---

## 🐍 Python Code Style

### Именование
- **Переменные:** `snake_case` — `user_name`, `task_count`
- **Классы:** `PascalCase` — `CognitivePipeline`, `MemoryManager`
- **Константы:** `UPPER_SNAKE_CASE` — `MAX_RETRIES`, `DEFAULT_TIMEOUT`
- **Функции:** `snake_case` — `process_request()`, `analyze_data()`
- **Приватные:** `_prefix` — `_internal_method()`, `_cache`

### Type Hints (обязательно)
```python
from typing import Optional, Dict, Any, List

def process_data(
    input_data: Dict[str, Any],
    max_items: int = 10
) -> List[str]:
    """Обрабатывает данные и возвращает список строк."""
    pass
```

### Комментарии (обязательно на русском)
```python
class DataProcessor:
    """
    Обработчик данных с поддержкой кэширования.
    
    Attributes:
        cache: LRU кэш для хранения результатов
        max_size: Максимальный размер кэша
    """
    
    def process(self, data: dict) -> str:
        """
        Обрабатывает входные данные.
        
        Args:
            data: Входные данные для обработки
            
        Returns:
            Результат обработки в виде строки
            
        Raises:
            ValueError: Если данные некорректны
        """
        # Проверяем входные данные
        if not data:
            raise ValueError("Данные не могут быть пустыми")
        
        # Обрабатываем
        result = self._transform(data)
        
        return result
```

---

## 🏗️ Архитектурные правила

### Структура модулей
```
module_name/
├── __init__.py       # Экспорты
├── module.py         # Основная логика
├── types.py          # Type definitions
└── utils.py          # Вспомогательные функции
```

### Импорты
```python
# 1. Стандартная библиотека

```

### Обработка ошибок
```python
import logging

logger = logging.getLogger(__name__)

def risky_operation():
    try:
        result = dangerous_call()
        return result
    except SpecificException as e:
        # Ожидаемая ошибка — логируем и обрабатываем
        logger.warning(f"Ожидаемая ошибка: {e}")
        return fallback_value
    except Exception as e:
        # Неожиданная ошибка — логируем полностью
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        raise
```

---

## 🧪 Тестирование

### Структура тестов
```python
# tests/test_module.py
import pytest
from neurocore.module import MyClass

class TestMyClass:
    """Тесты для класса MyClass."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.instance = MyClass()
    
    def test_success_case(self):
        """Тест успешного сценария."""
        result = self.instance.process(valid_input)
        assert result == expected_output
    
    def test_error_case(self):
        """Тест обработки ошибок."""
        with pytest.raises(ValueError):
            self.instance.process(invalid_input)
```

### Именование тестов
- Файл: `test_*.py`
- Класс: `Test*` 
- Метод: `test_*`

---

## 📝 Документация

### Docstrings (Google style)
```python
def complex_function(param1: int, param2: str) -> dict:
    """
    Выполняет сложную операцию.
    
    Args:
        param1: Числовой параметр
        param2: Строковый параметр
        
    Returns:
        Словарь с результатами
        
    Raises:
        ValueError: При неверных параметрах
        RuntimeError: При сбое операции
    """
```

### README для модулей
Каждый значимый модуль должен иметь документацию:
- Назначение
- Основные классы/функции
- Примеры использования

---

## 🔒 Безопасность

### Валидация входных данных
```python
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    name: str
    age: int
    
    @validator('age')
    def age_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Возраст должен быть положительным')
        return v
```

### Логирование чувствительных данных
```python
# ❌ Неправильно
logger.info(f"User password: {password}")

# ✅ Правильно
logger.info(f"User login attempt: {username}")
```

---

## 🚀 Производительность

### Асинхронный код
```python
# ✅ Правильно
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# ❌ Неправильно (блокирует event loop)
def fetch_data():
    return requests.get(url).json()
```

### Кэширование
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(param: str) -> str:
    """Операция с кэшированием результатов."""
    pass
```

---

## 📊 Логирование

### Уровни логирования
- **DEBUG** — детальная информация для отладки
- **INFO** — общая информация о работе
- **WARNING** — предупреждения, не критичные
- **ERROR** — ошибки, требующие внимания
- **CRITICAL** — критические ошибки, система не работает

### Формат сообщений
```python
logger.info(f"✅ Компонент {name} инициализирован")
logger.warning(f"⚠️ Предупреждение: {message}")
logger.error(f"❌ Ошибка в {function}: {error}")
```

---

## 🔄 Git и версионирование

### Коммиты (на английском)
```
feat: добавить Cognitive Pipeline
fix: исправить ошибку в MemoryManager
docs: обновить документацию
test: добавить тесты для AnalysisAgent
refactor: оптимизировать алгоритм поиска
```

### Версионирование
- Следуем Semantic Versioning: `MAJOR.MINOR.PATCH`
- Текущая версия проекта: `2.0.0`

---

**Следование этим правилам обязательно для всех новых файлов.**
