# Makefile для тестирования PAD+ AI

.PHONY: test test-unit test-integration test-coverage test-clean help

# Все тесты
test:
	pytest -v

# Только unit тесты
test-unit:
	pytest tests/unit/ -v

# Только интеграционные тесты
test-integration:
	pytest tests/integration/ -v

# Тесты с покрытием
test-coverage:
	pytest --cov=backend --cov-report=html --cov-report=term-missing

# Быстрые тесты (без медленных)
test-fast:
	pytest -m "not slow" -v

# Тесты памяти
test-memory:
	pytest -m memory -v

# Тесты LLM
test-llm:
	pytest -m llm -v

# Тесты эмоций
test-emotion:
	pytest -m emotion -v

# Тесты знаний
test-knowledge:
	pytest -m knowledge -v

# Тесты автономии
test-autonomy:
	pytest -m autonomy -v

# API тесты (требуют запущенный сервер)
test-api:
	pytest -m api -v

# Очистка кэша тестов
test-clean:
	rm -rf .pytest_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Установка зависимостей
install:
	pip install -r requirements.txt

# Запуск сервера для API тестов
run-server:
	python backend/main.py

# Полная проверка (установка + тесты)
check: install test

# Помощь
help:
	@echo "Доступные команды:"
	@echo "  test          - Запустить все тесты"
	@echo "  test-unit     - Запустить только unit тесты"
	@echo "  test-integration - Запустить только интеграционные тесты"
	@echo "  test-coverage - Запустить тесты с покрытием"
	@echo "  test-fast     - Запустить быстрые тесты (без медленных)"
	@echo "  test-memory   - Запустить тесты памяти"
	@echo "  test-llm      - Запустить тесты LLM"
	@echo "  test-emotion  - Запустить тесты эмоций"
	@echo "  test-knowledge - Запустить тесты знаний"
	@echo "  test-autonomy - Запустить тесты автономии"
	@echo "  test-api      - Запустить API тесты (требует сервер)"
	@echo "  test-clean    - Очистить кэш тестов"
	@echo "  install       - Установить зависимости"
	@echo "  run-server    - Запустить сервер"
	@echo "  check         - Установить зависимости + запустить тесты"
	@echo "  help          - Показать эту справку"
