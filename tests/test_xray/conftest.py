"""
X-Ray тесты: конфигурация окружения.

Переопределяем parent mock_env_vars — подавляем DB connection,
чтобы RAG/Supabase не пытались коннектиться при импорте.
"""
import os
import pytest


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Переопределяет parent fixture — без БД для X-Ray тестов"""
    monkeypatch.setenv("TEST_MODE", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("RAG_DATABASE_URL", "")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_KEY", "")
