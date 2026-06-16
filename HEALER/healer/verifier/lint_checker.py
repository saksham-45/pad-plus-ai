from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from healer.verifier.result import VerificationResult, Verdict


class LintChecker:
    """Запускает линтеры и typecheckers (ruff, mypy, eslint).

    Автоопределяет доступные инструменты.
    """

    LINTERS: dict[str, dict[str, Any]] = {
        "ruff": {
            "check_cmd": lambda: shutil.which("ruff") is not None,
            "cmd": ["ruff", "check", "."],
            "name": "ruff",
        },
        "mypy": {
            "check_cmd": lambda: shutil.which("mypy") is not None,
            "cmd": ["mypy", "."],
            "name": "mypy",
        },
        "eslint": {
            "check_cmd": lambda: shutil.which("eslint") is not None or shutil.which("npx") is not None,
            "cmd": ["npx", "eslint", "."],
            "name": "eslint",
        },
    }

    def __init__(self, project_path: str, timeout_s: int = 60):
        self.project_path = Path(project_path).resolve()
        self.timeout_s = timeout_s

    def run_all(self) -> list[VerificationResult]:
        results: list[VerificationResult] = []
        for _name, cfg in self.LINTERS.items():
            result = self._run_linter(cfg)
            results.append(result)
        return results

    def run(self) -> VerificationResult:
        results = self.run_all()
        from healer.verifier.result import PhaseVerdict
        pv = PhaseVerdict()
        for r in results:
            pv.add(r)
        return VerificationResult(
            phase="lint",
            verdict=pv.verdict,
            name="lint_checker",
            message=f"Линтеры: {pv.summary}",
            details={"individual": [r.to_dict() for r in results]},
        )

    def _run_linter(self, cfg: dict[str, Any]) -> VerificationResult:
        name = cfg["name"]
        try:
            if not cfg["check_cmd"]():
                return VerificationResult(
                    phase="lint",
                    verdict=Verdict.PASSED,
                    name=name,
                    message=f"{name}: не найден, пропущен",
                    details={"status": "skipped"},
                )

            result = subprocess.run(
                cfg["cmd"],
                capture_output=True, text=True, timeout=self.timeout_s,
                cwd=str(self.project_path),
                shell=sys.platform == "win32",
            )

            passed = result.returncode == 0
            output = (result.stdout + result.stderr)[:2000]

            return VerificationResult(
                phase="lint",
                verdict=Verdict.PASSED if passed else Verdict.FAILED,
                name=name,
                message=f"{name}: {'чисто' if passed else 'найдены проблемы'}",
                details={
                    "returncode": result.returncode,
                    "output": output,
                },
            )
        except FileNotFoundError:
            return VerificationResult(
                phase="lint",
                verdict=Verdict.PASSED,
                name=name,
                message=f"{name}: не найден, пропущен",
                details={"status": "not_installed"},
            )
        except subprocess.TimeoutExpired:
            return VerificationResult(
                phase="lint",
                verdict=Verdict.FAILED,
                name=name,
                message=f"{name}: таймаут {self.timeout_s}с",
                error="timeout",
            )
        except Exception as e:
            return VerificationResult(
                phase="lint",
                verdict=Verdict.ERROR,
                name=name,
                message=f"{name}: ошибка — {e}",
                error=str(e),
            )
