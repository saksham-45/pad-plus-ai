"""MetaLearner — система обучения на результатах healing-циклов.

Запоминает каждый результат, ведёт статистику по паттернам и детекторам,
адаптивно меняет пороги и веса.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HealingRecord:
    cycle_id: str
    mode: str
    timestamp: float
    detector: str
    pattern: str
    success: bool
    duration_ms: float
    file_path: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "mode": self.mode,
            "timestamp": self.timestamp,
            "detector": self.detector,
            "pattern": self.pattern,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "file_path": self.file_path,
            "error": self.error,
        }


@dataclass
class PatternStats:
    pattern: str
    total: int = 0
    success: int = 0
    failed: int = 0
    total_duration_ms: float = 0.0
    last_used: float = 0.0
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.success / self.total

    @property
    def avg_duration_ms(self) -> float:
        if self.total == 0:
            return 0.0
        return self.total_duration_ms / self.total

    @property
    def priority(self) -> float:
        """Приоритет паттерна: от 0.0 (не использовать) до 1.0 (макс приоритет)."""
        if self.total < 3:
            return 0.5
        rate = self.success_rate
        if self.consecutive_failures >= 3:
            rate *= 0.3
        return min(1.0, max(0.0, rate))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_ms": round(self.avg_duration_ms, 1),
            "priority": round(self.priority, 3),
            "consecutive_failures": self.consecutive_failures,
        }


@dataclass
class DetectorStats:
    detector: str
    total: int = 0
    true_positive: int = 0
    false_positive: int = 0
    patched: int = 0
    last_used: float = 0.0

    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return self.true_positive / self.total

    @property
    def weight(self) -> float:
        """Вес диагноста: от 0.0 (не доверять) до 1.0 (макс доверие)."""
        if self.total < 5:
            return 1.0
        acc = self.accuracy
        if acc < 0.3:
            return 0.1
        if acc < 0.5:
            return 0.3
        if acc < 0.7:
            return 0.6
        return 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector": self.detector,
            "total": self.total,
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "patched": self.patched,
            "accuracy": round(self.accuracy, 3),
            "weight": round(self.weight, 3),
        }


class MetaLearner:
    """Обучается на результатах healing-циклов.

    Хранит историю в JSON на диске.
    """

    def __init__(self, storage_path: str | None = None,
                 max_records: int = 2000, max_age_days: int = 180):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path(__file__).parent.parent / "data" / "meta"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.max_records = max_records
        self.max_age_days = max_age_days
        self.records: list[HealingRecord] = []
        self.pattern_stats: dict[str, PatternStats] = {}
        self.detector_stats: dict[str, DetectorStats] = {}

        self._load()

    def _prune(self) -> None:
        """Remove old records beyond retention limits.
        Placeholder timestamps (< 1.0) are kept but capped to max_records/2.
        """
        if not self.records:
            return
        cutoff = time.time() - self.max_age_days * 86400
        before = len(self.records)
        placeholders = [r for r in self.records if r.timestamp < 1.0]
        normal = [r for r in self.records if r.timestamp >= 1.0 and r.timestamp >= cutoff]
        half = max(1, self.max_records // 2)
        if len(placeholders) > half:
            placeholders = placeholders[-half:]
        if len(normal) > self.max_records - half:
            normal = normal[-(self.max_records - half):]
        self.records = normal + placeholders
        if len(self.records) != before:
            self._recompute_stats()

    def _recompute_stats(self) -> None:
        """Rebuild pattern_stats and detector_stats from remaining records."""
        self.pattern_stats.clear()
        self.detector_stats.clear()
        for r in self.records:
            stat = self.pattern_stats.setdefault(r.pattern, PatternStats(pattern=r.pattern))
            stat.total += 1
            stat.total_duration_ms += r.duration_ms
            stat.last_used = r.timestamp
            if r.success:
                stat.success += 1
                stat.consecutive_failures = 0
            else:
                stat.failed += 1
                stat.consecutive_failures += 1

            det = self.detector_stats.setdefault(r.detector, DetectorStats(detector=r.detector))
            det.total += 1
            det.last_used = r.timestamp
            if r.success:
                det.true_positive += 1
                det.patched += 1
            else:
                det.false_positive += 1

    def record_healing(self, record: HealingRecord) -> None:
        """Записать результат одного healing-цикла."""
        self.records.append(record)

        stat = self.pattern_stats.setdefault(record.pattern, PatternStats(pattern=record.pattern))
        stat.total += 1
        stat.total_duration_ms += record.duration_ms
        stat.last_used = record.timestamp

        if record.success:
            stat.success += 1
            stat.consecutive_failures = 0
        else:
            stat.failed += 1
            stat.consecutive_failures += 1

        det = self.detector_stats.setdefault(record.detector, DetectorStats(detector=record.detector))
        det.total += 1
        det.last_used = record.timestamp
        if record.success:
            det.true_positive += 1
            det.patched += 1
        else:
            det.false_positive += 1

        self._prune()
        self._save()

    def record_batch(self, records: list[HealingRecord]) -> None:
        for r in records:
            self.record_healing(r)

    def get_pattern_priority(self, pattern: str) -> float:
        stat = self.pattern_stats.get(pattern)
        if stat is None:
            return 0.5
        return stat.priority

    def get_detector_weight(self, detector: str) -> float:
        stat = self.detector_stats.get(detector)
        if stat is None:
            return 1.0
        return stat.weight

    def get_best_pattern(self, detector: str) -> str | None:
        patterns_map = {
            "SpanAnalyzer": "try_finally",
            "ErrorPathDetector": "try_finally",
            "SlowImportDetector": "lazy_import",
            "LatencyAnomalyDetector": "add_timeout",
            "DeadCodeDetector": "remove_dead",
            "ResourceLeakDetector": "close_resource",
        }
        default = patterns_map.get(detector)
        if not default:
            return None

        candidates = [default]
        for p, stat in self.pattern_stats.items():
            if p not in candidates:
                continue
            candidates.append(p)

        candidates.sort(key=lambda p: self.get_pattern_priority(p), reverse=True)
        return candidates[0] if candidates else default

    def get_confidence(self, detector: str, pattern: str) -> float:
        dw = self.get_detector_weight(detector)
        pp = self.get_pattern_priority(pattern)
        return dw * pp

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_cycles": len(self.records),
            "patterns": {k: v.to_dict() for k, v in sorted(self.pattern_stats.items())},
            "detectors": {k: v.to_dict() for k, v in sorted(self.detector_stats.items())},
            "overall_success_rate": round(
                sum(1 for r in self.records if r.success) / len(self.records), 3
            ) if self.records else 0.0,
        }

    def get_recent(self, limit: int = 20) -> list[dict]:
        return [r.to_dict() for r in self.records[-limit:]]

    def _save(self) -> None:
        data = {
            "records": [r.to_dict() for r in self.records],
            "patterns": {k: v.to_dict() for k, v in self.pattern_stats.items()},
            "detectors": {k: v.to_dict() for k, v in self.detector_stats.items()},
            "updated_at": time.time(),
        }
        path = self.storage_path / "meta.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self) -> None:
        path = self.storage_path / "meta.json"
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for r in data.get("records", []):
                self.records.append(HealingRecord(**r))
            import dataclasses
            ps_fields = {f.name for f in dataclasses.fields(PatternStats)}
            for name, s in data.get("patterns", {}).items():
                filtered = {k: v for k, v in s.items() if k in ps_fields}
                self.pattern_stats[name] = PatternStats(**filtered)
            ds_fields = {f.name for f in dataclasses.fields(DetectorStats)}
            for name, s in data.get("detectors", {}).items():
                filtered = {k: v for k, v in s.items() if k in ds_fields}
                self.detector_stats[name] = DetectorStats(**filtered)
        except Exception:
            pass

    def clear(self) -> None:
        self.records.clear()
        self.pattern_stats.clear()
        self.detector_stats.clear()
        self._save()
