"""
Тесты для ReflectionLoop — анализ циклов HEALER.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from healing.reflection_loop import reflect


def test_reflection_empty_cycles():
    result = reflect([])
    assert result["learnings"] == []
    assert result["changes"] == []
    assert result["stats"]["total_cycles"] == 0
    assert result["stats"]["success_cycles"] == 0


def test_reflection_with_reports_only():
    cycles = [{
        "status": "ok",
        "reports": [],
        "timestamp": "",
        "duration_ms": 100,
    }]
    result = reflect(cycles)
    assert result["stats"]["total_cycles"] == 1
    assert result["stats"]["success_cycles"] == 1
    assert result["learnings"] == []


def test_reflection_high_failure_rate():
    cycles = [
        {"status": "error", "reports": [], "timestamp": "", "duration_ms": 100},
        {"status": "ok", "reports": [], "timestamp": "", "duration_ms": 100},
        {"status": "error", "reports": [], "timestamp": "", "duration_ms": 100},
    ]
    result = reflect(cycles)
    assert any(l["pattern"] == "repeated_failures" for l in result["learnings"])
    assert result["stats"]["failed_cycles"] == 2
    assert result["stats"]["success_cycles"] == 1


def test_reflection_with_fixed_reports():
    cycles = [{
        "status": "ok",
        "reports": [{
            "status": "fixed",
            "detector": "SlowPhasesDetector",
            "recommendation": "switch_model",
            "old_value": "gpt-4",
            "new_value": "groq/llama-3.1-8b",
        }],
        "timestamp": "2024-01-01T00:00:00",
        "duration_ms": 500,
    }]
    result = reflect(cycles)
    assert len(result["changes"]) == 1
    assert result["changes"][0]["component"] == "SlowPhasesDetector"
    assert result["changes"][0]["old_value"] == "gpt-4"
    assert result["changes"][0]["new_value"] == "groq/llama-3.1-8b"


def test_reflection_multiple_cycles():
    cycles = [
        {
            "status": "ok",
            "reports": [{"status": "fixed", "detector": "D1"}],
            "timestamp": "",
            "duration_ms": 200,
        },
        {
            "status": "ok",
            "reports": [{"status": "fixed", "detector": "D2"}],
            "timestamp": "",
            "duration_ms": 300,
        },
    ]
    result = reflect(cycles)
    assert len(result["changes"]) == 2
    assert result["stats"]["total_reports"] == 2
    assert result["stats"]["avg_duration_ms"] == 250.0


def test_reflection_partial_cycle():
    cycles = [
        {"status": "unknown", "reports": [], "timestamp": "", "duration_ms": 0},
    ]
    result = reflect(cycles)
    assert result["stats"]["partial_cycles"] == 1
    assert result["stats"]["success_cycles"] == 0
    assert result["stats"]["failed_cycles"] == 0


def test_reflection_mixed_status():
    cycles = [
        {"status": "ok", "reports": [], "timestamp": "", "duration_ms": 100},
        {"status": "error", "reports": [], "timestamp": "", "duration_ms": 200},
        {"status": "done", "reports": [], "timestamp": "", "duration_ms": 150},
        {"status": "success", "reports": [], "timestamp": "", "duration_ms": 50},
    ]
    result = reflect(cycles)
    assert result["stats"]["total_cycles"] == 4
    assert result["stats"]["success_cycles"] == 3  # ok + done + success
    assert result["stats"]["failed_cycles"] == 1  # error
