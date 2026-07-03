"""
📦 HealingChangesStore — хранилище применённых изменений для отката.

Позволяет:
- Записать применение патча (с backup-копией файла)
- Получить список всех изменений
- Фильтровать по статусу (applied/rolled_back)
- Откатить изменение по patch_id
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("padplus.healing.changes_store")


class HealingChangesStore:
    """Хранилище применённых изменений с возможностью отката."""

    def __init__(self) -> None:
        self._applied: list[dict[str, Any]] = []
        self._backups: dict[str, tuple[str, bytes]] = {}
        self._lock = threading.Lock()

    def record_apply(
        self,
        component: str,
        file_path: str,
        old_content: bytes,
        new_content: bytes,
        report: dict[str, Any],
    ) -> str:
        """Записать применение патча. Возвращает patch_id."""
        patch_id = f"patch_{int(datetime.now().timestamp() * 1000)}"

        with self._lock:
            self._applied.append({
                "patch_id": patch_id,
                "component": component,
                "file_path": file_path,
                "old_value": old_content.decode("utf-8", errors="replace")[:500],
                "new_value": new_content.decode("utf-8", errors="replace")[:500],
                "status": "applied",
                "reason": report.get("recommendation", ""),
                "timestamp": datetime.now().isoformat(),
            })
            self._backups[patch_id] = (file_path, old_content)

        logger.info("Изменение записано: patch_id=%s, component=%s", patch_id, component)
        return patch_id

    def get_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._applied)

    def get_by_status(self, status: str) -> list[dict[str, Any]]:
        with self._lock:
            return [c for c in self._applied if c.get("status") == status]

    def rollback(self, patch_id: str) -> bool:
        """Откатить изменение по patch_id. Возвращает True при успехе."""
        with self._lock:
            backup = self._backups.get(patch_id)
            if not backup:
                logger.warning("patch_id не найден для отката: %s", patch_id)
                return False

            file_path, old_content = backup

        try:
            Path(file_path).write_bytes(old_content)
            with self._lock:
                for c in self._applied:
                    if c["patch_id"] == patch_id:
                        c["status"] = "rolled_back"
                        c["rolled_back_at"] = datetime.now().isoformat()
            logger.info("Патч откачен: patch_id=%s, file=%s", patch_id, file_path)
            return True
        except Exception as e:
            logger.error("Ошибка отката патча %s: %s", patch_id, e)
            return False


# Глобальный экземпляр
_changes_store: Optional[HealingChangesStore] = None


def get_changes_store() -> HealingChangesStore:
    global _changes_store
    if _changes_store is None:
        _changes_store = HealingChangesStore()
    return _changes_store
