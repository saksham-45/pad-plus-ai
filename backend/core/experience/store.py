import logging
from typing import Optional, List, Dict, Any

from .models import ExperienceRecord
from .postgres_store import ExperiencePostgresStore, postgres_available

logger = logging.getLogger("padplus.experience")

_POSTGRES_STORE: Optional[ExperiencePostgresStore] = None


def _get_store() -> ExperiencePostgresStore:
    global _POSTGRES_STORE
    if _POSTGRES_STORE is None:
        _POSTGRES_STORE = ExperiencePostgresStore()
    return _POSTGRES_STORE


class ExperienceStore:
    def save(self, record: ExperienceRecord) -> str:
        if postgres_available:
            return _get_store().save(record)
        logger.warning("PostgreSQL недоступен, опыт не сохранён")
        return ""

    def load_all(self) -> List[Dict[str, Any]]:
        if postgres_available:
            return _get_store().load_all()
        return []

    def count(self) -> int:
        if postgres_available:
            return _get_store().count()
        return 0

    def get_session_records(self, limit: int = 0) -> list[ExperienceRecord]:
        return []

    def clear_session(self):
        pass
