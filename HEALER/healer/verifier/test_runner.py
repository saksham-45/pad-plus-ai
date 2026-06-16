from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from healer.verifier.result import VerificationResult, Verdict


class TestRunner:
    """Запускает тесты проекта (pytest, npm test, unittest).

    Автоопределяет фреймворк по файлам в проекте.
    """

    def __init__(self, project_path: str, timeout_s: int = 120):
        self.project_path = Path(project_path).resolve()
        self.timeout_s = timeout_s

    def run(self) -> VerificationResult:
        if not self.project_path.is_dir():
            return VerificationResult(
                phase="test",
                verdict=Verdict.ERROR,
                name="test_runner",
                message=f"Проект не найден: {self.project_path}",
                error="directory_not_found",
            )

        framework = self._detect_framework()
        if framework is None:
            return VerificationResult(
                phase="test",
                verdict=Verdict.ERROR,
                name="test_runner",
                message="Не удалось определить тестовый фреймворк",
                error="unknown_framework",
            )

        try:
            result = subprocess.run(
                framework["cmd"],
                capture_output=True, text=True, timeout=self.timeout_s,
                cwd=str(self.project_path),
                shell=sys.platform == "win32",
            )

            passed = result.returncode == 0

            summary = self._parse_output(result.stdout, framework["name"])
            failed_count = summary.get("failed", 0)
            error_count = summary.get("errors", 0)

            return VerificationResult(
                phase="test",
                verdict=Verdict.PASSED if passed else Verdict.FAILED,
                name=framework["name"],
                message=f"{framework['name']}: {summary.get('passed', 0)} passed, "
                        f"{failed_count} failed, {error_count} errors",
                details={
                    "framework": framework["name"],
                    "returncode": result.returncode,
                    "stdout": result.stdout[-2000:] if result.stdout else "",
                    "stderr": result.stderr[-1000:] if result.stderr else "",
                    "timeout_s": self.timeout_s,
                    "project": str(self.project_path),
                },
            )
        except subprocess.TimeoutExpired:
            return VerificationResult(
                phase="test",
                verdict=Verdict.FAILED,
                name="test_runner",
                message=f"Таймаут {self.timeout_s}с при запуске тестов",
                details={"framework": framework["name"], "timeout_s": self.timeout_s},
                error="timeout",
            )
        except Exception as e:
            return VerificationResult(
                phase="test",
                verdict=Verdict.ERROR,
                name="test_runner",
                message=f"Ошибка запуска тестов: {e}",
                error=str(e),
            )

    def _detect_framework(self) -> dict[str, Any] | None:
        has_pyproject = (self.project_path / "pyproject.toml").exists()
        has_pytest_ini = (self.project_path / "pytest.ini").exists()
        has_setup_cfg = (self.project_path / "setup.cfg").exists()
        has_package_json = (self.project_path / "package.json").exists()
        has_test_dir = (self.project_path / "tests").is_dir()

        if has_pyproject or has_pytest_ini or has_setup_cfg or has_test_dir:
            return {
                "name": "pytest",
                "cmd": [sys.executable, "-m", "pytest", "tests/", "-x", "--tb=short"],
            }

        if (self.project_path / "manage.py").exists():
            return {
                "name": "django",
                "cmd": [sys.executable, "manage.py", "test"],
            }

        if has_package_json:
            return {
                "name": "npm test",
                "cmd": ["npm", "test"],
            }

        return None

    @staticmethod
    def _parse_output(output: str, framework: str) -> dict[str, int]:
        result: dict[str, int] = {"passed": 0, "failed": 0, "errors": 0}
        if framework == "pytest":
            import re
            for line in output.splitlines():
                m = re.search(r'=\s*(\d+)\s+passed', line)
                if m:
                    result["passed"] = int(m.group(1))
                m = re.search(r'(\d+)\s+failed', line)
                if m:
                    result["failed"] = int(m.group(1))
                m = re.search(r'(\d+)\s+errors', line)
                if m:
                    result["errors"] = int(m.group(1))
        return result
