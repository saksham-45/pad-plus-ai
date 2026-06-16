"""CacheCleanerPatcher — очищает кэш L1 при высоком потреблении памяти.

Срабатывает на detector="high_memory". Не модифицирует исходный код,
а выполняет runtime-очистку in-memory кэша.
"""

from __future__ import annotations

import logging

from healer.diagnostics.report import DiagnosticReport
from healer.patcher.base import BasePatcher
from healer.patcher.result import PatchResult

logger = logging.getLogger("healer.patcher.cache_cleaner")


class CacheCleanerPatcher(BasePatcher):
    language = "runtime"

    def patch(self, source_code: str, report: DiagnosticReport,
              source_path: str = "") -> PatchResult:
        return self._clear_cache(source_path)

    def patch_file(self, filepath: str, report: DiagnosticReport) -> PatchResult:
        return self._clear_cache(filepath)

    def _clear_cache(self, source_path: str) -> PatchResult:
        try:
            from backend.core.cache_manager import get_cache_manager
            cm = get_cache_manager()
            cm.memory_cache.clear()
            cm.stats["deletes"] += cm.stats["memory_hits"]
            cm.stats["memory_hits"] = 0
            cm.stats["memory_misses"] = 0
            logger.info("Кэш L1 очищен (высокое потребление памяти)")
            return PatchResult(
                patcher="cache_cleaner",
                pattern="clear_cache",
                source_path=source_path,
                original_code="",
                success=True,
                metadata={"cleared": True, "message": "L1 cache cleared"},
            )
        except ImportError:
            logger.warning("CacheManager не найден — очистка кэша недоступна")
            return PatchResult(
                patcher="cache_cleaner",
                pattern="clear_cache",
                source_path=source_path,
                original_code="",
                success=False,
                error="CacheManager not available",
            )
        except Exception as e:
            logger.error("Ошибка очистки кэша: %s", e)
            return PatchResult(
                patcher="cache_cleaner",
                pattern="clear_cache",
                source_path=source_path,
                original_code="",
                success=False,
                error=str(e),
            )

    def get_supported_patterns(self) -> list[str]:
        return ["clear_cache"]

    def get_supported_detectors(self) -> list[str]:
        return ["high_memory", "HighMemoryDetector"]
