import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import ExperienceRecord

logger = logging.getLogger("padplus.experience")

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # backend/core/experience/ → project root


class ExperienceStore:
    def __init__(self, data_dir: Optional[str] = None):
        path = data_dir or (PROJECT_ROOT / "data" / "experiences")
        self.data_dir = Path(path)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._session_records: list[ExperienceRecord] = []

    def save(self, record: ExperienceRecord) -> str:
        filename = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        path = self.data_dir / filename
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
            self._session_records.append(record)
            logger.debug("Experience saved: %s | type=%s sig=%.3f", filename, record.interaction_type.value, record.significance)
            return str(path)
        except Exception as e:
            logger.error("Failed to save experience: %s", e)
            return ""

    def get_session_records(self, limit: int = 0) -> list[ExperienceRecord]:
        if limit > 0:
            return self._session_records[-limit:]
        return list(self._session_records)

    def clear_session(self):
        self._session_records.clear()

    def count(self) -> int:
        return len(self._session_records)

    def load_all(self) -> list[dict]:
        records = []
        for path in sorted(self.data_dir.glob("exp_*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    records.append(json.load(f))
            except Exception as e:
                logger.warning("Cannot load %s: %s", path.name, e)
        return records
