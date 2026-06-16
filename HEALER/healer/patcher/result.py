from __future__ import annotations

import difflib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


HEALER_INTERNAL_PREFIXES = ("healer", "aethon")


def _check_restart_required(source_path: str) -> bool:
    """True if patched file is inside HEALER itself (needs restart)."""
    parts = Path(source_path).parts
    return any(p in HEALER_INTERNAL_PREFIXES for p in parts)


@dataclass
class PatchResult:
    patcher: str
    pattern: str
    source_path: str
    original_code: str
    patched_code: str | None = None
    success: bool = False
    error: str | None = None
    restart_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.restart_required:
            self.restart_required = _check_restart_required(self.source_path)

    @property
    def diff(self) -> str:
        if self.patched_code is None:
            return ""
        return "".join(difflib.unified_diff(
            self.original_code.splitlines(keepends=True),
            self.patched_code.splitlines(keepends=True),
            fromfile=self.source_path,
            tofile=self.source_path + " (patched)",
        ))

    @property
    def diff_lines(self) -> int:
        """Количество добавленных строк в diff (для метрик MetaLearner)."""
        if self.patched_code is None:
            return 0
        return sum(
            1 for l in self.diff.splitlines()
            if l.startswith('+') and not l.startswith('+++')
        )

    def apply(self, backup: bool = True) -> bool:
        if not self.success or self.patched_code is None:
            return False
        if not os.path.isfile(self.source_path):
            return False
        if backup:
            backup_path = self.source_path + ".healer.bak"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(self.original_code)
        with open(self.source_path, "w", encoding="utf-8") as f:
            f.write(self.patched_code)
        return True

    def rollback(self) -> bool:
        backup_path = self.source_path + ".healer.bak"
        if not os.path.isfile(backup_path):
            return False
        with open(backup_path, "r", encoding="utf-8") as f:
            original = f.read()
        with open(self.source_path, "w", encoding="utf-8") as f:
            f.write(original)
        os.remove(backup_path)
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "patcher": self.patcher,
            "pattern": self.pattern,
            "source_path": self.source_path,
            "success": self.success,
            "error": self.error,
            "diff": self.diff,
            "metadata": self.metadata,
        }

    @staticmethod
    def make_diff(original: str, patched: str, source_path: str = "") -> str:
        return "".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=source_path,
            tofile=source_path + " (patched)",
        ))
