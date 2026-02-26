# Тестирование PAD+ AI

## Обзор

Проект использует pytest для тестирования с четким разделением на unit и integration тесты.

## Структура тестов

```
tests/
├── conftest.py              # Общие фикстуры
├── test_all_components.py   # Интеграционный тест всех компонентов
├── unit/                    # Unit тесты
│   ├── test_memory.py       # Тесты памяти
│   ├── test_emotion.py      # Тесты эмоций
│   ├── test_llm.py          # Тесты LLM
│   └── test_knowledge.py    # Тесты знаний
├── integration/             # Интеграционные тесты
│   ├── test_autonomy.py     # Тесты автономии
│   ├── test_rag.py          # Тесты RAG
│   └── test_rag_v3.py       # Тесты RAG v3
└── fixtures/                # Фикстуры и данные для тестов
```

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск тестов

### Все тесты
```bash
pytest
```

### Только unit тесты
```bash
pytest tests/unit/
```

### Только интеграционные тесты
```bash
pytest tests/integration/
```

### Тесты с определенными маркерами
```bash
# Тесты памяти
pytest -m memory

# Тесты LLM
pytest -m llm

# Тесты эмоций
pytest -m emotion

# Медленные тесты
pytest -m slow

# API тесты
pytest -m api
```

### Тесты с выводом покрытия
```bash
pytest --cov=backend --cov-report=html
```

### Тесты с детальным выводом
```bash
pytest -v -s
```

## Маркеры тестов

- `@pytest.mark.unit` - Unit тесты
- `@pytest.mark.integration` - Интеграционные тесты
- `@pytest.mark.memory` - Тесты памяти
- `@pytest.mark.llm` - Тесты LLM
- `@pytest.mark.emotion` - Тесты эмоций
- `@pytest.mark.knowledge` - Тесты знаний
- `@pytest.mark.autonomy` - Тесты автономии
- `@pytest.mark.rag` - Тесты RAG
- `@pytest.mark.persona` - Тесты персоны
- `@pytest.mark.pipeline` - Тесты пайплайна
- `@pytest.mark.hygiene` - Тесты гигиены
- `@pytest.mark.websocket` - Тесты WebSocket
- `@pytest.mark.api` - API тесты
- `@pytest.mark.slow` - Медленные тесты

## Написание новых тестов

### Unit тесты

Unit тесты должны находиться в `tests/unit/` и использовать моки:

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
@pytest.mark.memory
def test_memory_function():
    with patch('memory.module.get_function') as mock_get:
        mock_get.return_value = Mock()
        # Ваш тест
```

### Интеграционные тесты

Интеграционные тесты должны находиться в `tests/integration/` и тестировать реальные API:

```python
import pytest
import requests

@pytest.mark.integration
@pytest.mark.api
def test_api_endpoint():
    response = requests.get("http://localhost:8000/api/v1/status")
    assert response.status_code == 200
```

### Фикстуры

Используйте фикстуры из `conftest.py`:

```python
def test_with_fixture(mock_llm_response):
    assert "response" in mock_llm_response
```

## CI/CD

Для GitHub Actions используйте:

```yaml
- name: Run tests
  run: |
    pytest tests/unit/ -v
    pytest tests/integration/ -v
```

## Отладка тестов

### Запуск конкретного теста
```bash
pytest tests/unit/test_memory.py::test_memory_function -v
```

### Остановка при первом падении
```bash
pytest -x
```

### Запуск с отладчиком
```bash
pytest --pdb
```

## Покрытие кода

Установка coverage:
```bash
pip install pytest-cov
```

Запуск с покрытием:
```bash
pytest --cov=backend --cov-report=term-missing
```

HTML отчет:
```bash
pytest --cov=backend --cov-report=html
# Открыть htmlcov/index.html
```

## Проблемы и решения

### ImportError: No module named 'backend'
Убедитесь что вы находитесь в корневой директории проекта.

### Тесты не находят модули
Проверьте что в `conftest.py` правильно настроен `sys.path`.

### Медленные тесты
Используйте маркер `@pytest.mark.slow` и запускайте их отдельно:
```bash
pytest -m "not slow"
```
