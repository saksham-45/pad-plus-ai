"""
Тесты для HealingChangesStore — хранилище изменений и откат.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from healing.changes_store import HealingChangesStore


def test_record_apply():
    store = HealingChangesStore()
    patch_id = store.record_apply(
        component="SlowPhasesDetector",
        file_path="/tmp/test.py",
        old_content=b"old_code",
        new_content=b"new_code",
        report={"recommendation": "switch_model"},
    )
    assert patch_id.startswith("patch_")
    all_changes = store.get_all()
    assert len(all_changes) == 1
    assert all_changes[0]["component"] == "SlowPhasesDetector"
    assert all_changes[0]["status"] == "applied"


def test_get_by_status():
    store = HealingChangesStore()
    store.record_apply("C1", "/tmp/a.py", b"old", b"new", {})
    store.record_apply("C2", "/tmp/b.py", b"old", b"new", {})

    applied = store.get_by_status("applied")
    assert len(applied) == 2

    rolled = store.get_by_status("rolled_back")
    assert len(rolled) == 0


def test_get_by_status_partial():
    store = HealingChangesStore()
    store.record_apply("C1", "/tmp/a.py", b"old", b"new", {})
    all_changes = store.get_all()
    store.rollback(all_changes[0]["patch_id"])

    applied = store.get_by_status("applied")
    assert len(applied) == 0

    rolled = store.get_by_status("rolled_back")
    assert len(rolled) == 1


def test_rollback_unknown_patch_id():
    store = HealingChangesStore()
    result = store.rollback("nonexistent")
    assert result is False


def test_rollback_file_content(tmp_path):
    store = HealingChangesStore()
    test_file = tmp_path / "test.py"
    test_file.write_bytes(b"old_content")

    patch_id = store.record_apply(
        component="Test",
        file_path=str(test_file),
        old_content=b"old_content",
        new_content=b"new_content",
        report={},
    )

    # Маскируем, что применили новое содержимое (как если бы HEALER изменил файл)
    assert test_file.read_bytes() == b"old_content"
    test_file.write_bytes(b"new_content")
    assert test_file.read_bytes() == b"new_content"

    success = store.rollback(patch_id)
    assert success is True
    assert test_file.read_bytes() == b"old_content"


def test_rollback_updates_status():
    store = HealingChangesStore()
    patch_id = store.record_apply("C1", "/tmp/a.py", b"old", b"new", {})
    store.rollback(patch_id)

    all_changes = store.get_all()
    assert all_changes[0]["status"] == "rolled_back"
    assert "rolled_back_at" in all_changes[0]


def test_get_all_returns_copy():
    store = HealingChangesStore()
    store.record_apply("C1", "/tmp/a.py", b"old", b"new", {})
    result = store.get_all()
    result.append({"test": True})
    assert len(store.get_all()) == 1
