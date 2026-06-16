from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from healer.verifier.result import VerificationResult, Verdict


class RollbackEngine:
    """Откатывает изменения, сделанные PatchResult.apply().

    Ищет файлы *.healer.bak рядом с изменёнными файлами.
    """

    BACKUP_SUFFIX = ".healer.bak"

    def __init__(self, project_path: str = ""):
        self.project_path = Path(project_path).resolve() if project_path else None

    def rollback_all(self, source_paths: list[str]) -> VerificationResult:
        """Откатывает все изменения по списку файлов."""
        restored: list[str] = []
        not_found: list[str] = []
        failed: list[str] = []

        for path in source_paths:
            result = self._restore_backup(path)
            if result == "restored":
                restored.append(path)
            elif result == "not_found":
                not_found.append(path)
            else:
                failed.append(path)

        total = len(source_paths)
        if failed:
            return VerificationResult(
                phase="rollback",
                verdict=Verdict.ERROR,
                name="rollback_engine",
                message=f"Откат {len(restored)}/{total}: {len(failed)} ошибок",
                details={
                    "restored": restored,
                    "not_found": not_found,
                    "failed": failed,
                    "total": total,
                },
                error="rollback_failed",
            )
        if not_found:
            return VerificationResult(
                phase="rollback",
                verdict=Verdict.PASSED,
                name="rollback_engine",
                message=f"Откат {len(restored)}/{total}: {len(not_found)} бэкапов не найдено",
                details={
                    "restored": restored,
                    "not_found": not_found,
                    "failed": failed,
                    "total": total,
                },
            )
        return VerificationResult(
            phase="rollback",
            verdict=Verdict.PASSED,
            name="rollback_engine",
            message=f"Откат {len(restored)}/{total} файлов",
            details={
                "restored": restored,
                "not_found": not_found,
                "failed": failed,
                "total": total,
            },
        )

    def rollback(self, source_path: str) -> VerificationResult:
        """Откатывает один файл."""
        result = self._restore_backup(source_path)
        if result == "restored":
            return VerificationResult(
                phase="rollback",
                verdict=Verdict.PASSED,
                name="rollback_engine",
                message=f"Восстановлен: {source_path}",
                details={"source_path": source_path},
            )
        elif result == "not_found":
            return VerificationResult(
                phase="rollback",
                verdict=Verdict.PASSED,
                name="rollback_engine",
                message=f"Бэкап не найден: {source_path}",
                details={"source_path": source_path},
            )
        else:
            return VerificationResult(
                phase="rollback",
                verdict=Verdict.ERROR,
                name="rollback_engine",
                message=f"Не удалось восстановить: {source_path}",
                details={"source_path": source_path},
                error="restore_failed",
            )

    def _restore_backup(self, source_path: str) -> str:
        backup_path = str(Path(source_path)) + self.BACKUP_SUFFIX
        if not os.path.isfile(backup_path):
            return "not_found"
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                original = f.read()
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(original)
            os.remove(backup_path)
            return "restored"
        except Exception:
            return "failed"

    def list_backups(self, project_path: str | None = None) -> list[dict[str, Any]]:
        """Список всех бэкапов в проекте."""
        search_path = Path(project_path).resolve() if project_path else self.project_path
        if not search_path or not search_path.is_dir():
            return []
        backups = []
        for f in search_path.rglob(f"*{self.BACKUP_SUFFIX}"):
            original = str(f)[: -len(self.BACKUP_SUFFIX)]
            backups.append({
                "backup": str(f),
                "original": original,
                "exists": os.path.isfile(original),
                "size_kb": round(f.stat().st_size / 1024, 1),
            })
        return backups

    def cleanup_backups(self, project_path: str | None = None) -> int:
        """Удаляет все бэкапы в проекте."""
        backups = self.list_backups(project_path)
        count = 0
        for b in backups:
            try:
                os.remove(b["backup"])
                count += 1
            except OSError:
                pass
        return count
