import pytest
import json
import os
import tempfile
from scripts.impulse import (
    ImpulseCore, ImpulseDimension, ImpulseState,
    ImpulseManager, default_dimensions, IMPULSE_LABELS
)


class TestImpulseDimension:
    def test_default_values(self):
        d = ImpulseDimension(label="test", question="?")
        assert d.weight == 0.0

    def test_to_dict(self):
        d = ImpulseDimension(label="understand", question="?", weight=0.7)
        assert d.to_dict() == {"label": "understand", "question": "?", "weight": 0.7}

    def test_from_dict(self):
        d = ImpulseDimension.from_dict({"label": "create", "question": "?", "weight": 0.5})
        assert d.label == "create"
        assert d.weight == 0.5

    def test_roundtrip(self):
        d = ImpulseDimension(label="protect", question="?", weight=0.3)
        assert ImpulseDimension.from_dict(d.to_dict()) == d


class TestImpulseCore:
    def test_default_has_all_labels(self):
        core = ImpulseCore()
        labels = {d.label for d in core.dimensions}
        assert labels == {"understand", "improve", "protect", "create"}

    def test_default_primary_is_unknown(self):
        core = ImpulseCore()
        assert core.get_primary_label() == "unknown"

    def test_set_single_label(self):
        core = ImpulseCore()
        core.set_from_labels({"understand": 1.0})
        assert core.get_primary_label() == "understand"
        assert core.get_primary_question() == "Что я могу понять?"

    def test_set_multiple_labels(self):
        core = ImpulseCore()
        core.set_from_labels({"understand": 0.6, "create": 0.4})
        assert core.get_primary_label() == "understand"
        assert core.dimensions[0].weight == 0.6  # understand
        assert core.dimensions[3].weight == 0.4  # create

    def test_unset_labels_default_to_zero(self):
        core = ImpulseCore()
        core.set_from_labels({"create": 1.0})
        assert core.dimensions[0].weight == 0.0  # understand
        assert core.dimensions[3].weight == 1.0  # create

    def test_weights_not_normalized(self):
        core = ImpulseCore()
        core.set_from_labels({"understand": 1.0, "create": 1.0, "improve": 1.0})
        total = sum(d.weight for d in core.dimensions)
        assert total == 3.0

    def test_set_from_question_exact(self):
        core = ImpulseCore()
        core.set_from_question("Что я могу понять?")
        assert core.get_primary_label() == "understand"

    def test_set_from_question_partial(self):
        core = ImpulseCore()
        core.set_from_question("понять")
        assert core.get_primary_label() == "understand"

    def test_set_from_question_no_match(self):
        core = ImpulseCore()
        core.set_from_question("неизвестный запрос")
        assert core.dimensions[0].weight == 1.0

    def test_push_increments_depth(self):
        core = ImpulseCore()
        core.set_from_labels({"understand": 0.8})
        assert core.stack_depth() == 0
        core.push()
        assert core.stack_depth() == 1
        core.push()
        assert core.stack_depth() == 2

    def test_pop_restores_state(self):
        core = ImpulseCore()
        core.set_from_labels({"create": 1.0})
        core.push()
        core.set_from_labels({"understand": 1.0})
        core.pop()
        assert core.get_primary_label() == "create"

    def test_pop_empty_returns_false(self):
        core = ImpulseCore()
        assert core.pop() is False
        assert core.stack_depth() == 0

    def test_get_active_questions_threshold(self):
        core = ImpulseCore()
        core.set_from_labels({"understand": 0.1, "create": 0.9})
        active = core.get_active_questions(threshold=0.5)
        assert len(active) == 1
        assert active[0].label == "create"

    def test_prompt_line_single(self):
        core = ImpulseCore()
        core.set_from_labels({"protect": 1.0})
        prompt = core.get_prompt_line()
        assert "защитить" in prompt

    def test_prompt_line_multiple(self):
        core = ImpulseCore()
        core.set_from_labels({"understand": 0.6, "create": 0.4})
        prompt = core.get_prompt_line()
        assert "понять" in prompt
        assert "создать" in prompt

    def test_prompt_line_all_zero(self):
        core = ImpulseCore()
        prompt = core.get_prompt_line()
        assert "познать" in prompt or "познания" in prompt

    def test_to_dict_has_version(self):
        core = ImpulseCore()
        d = core.to_dict()
        assert d["version"] == 2
        assert "primary" in d
        assert "stack" in d

    def test_from_dict_v1_compat(self):
        old = {"question": "Что я могу понять?"}
        core = ImpulseCore.from_dict(old)
        assert core.get_primary_label() == "understand"

    def test_from_dict_v2(self):
        data = {
            "version": 2,
            "primary": {
                "question": "Что я могу создать?",
                "label": "create",
                "dimensions": [
                    {"label": "create", "question": "Что я могу создать?", "weight": 1.0}
                ]
            },
            "stack": [],
            "created_at": "2026-01-01T00:00:00",
            "modified_at": "2026-01-01T00:00:00"
        }
        core = ImpulseCore.from_dict(data)
        assert core.get_primary_label() == "create"

    def test_roundtrip_json(self):
        core = ImpulseCore()
        core.set_from_labels({"improve": 0.7, "create": 0.3})
        core.push()
        restored = ImpulseCore.from_dict(json.loads(core.to_json()))
        assert restored.get_primary_label() == core.get_primary_label()
        assert restored.stack_depth() == core.stack_depth()

    def test_modified_at_updates_on_set(self):
        core = ImpulseCore()
        t1 = core.modified_at
        core.set_from_labels({"understand": 0.5})
        assert core.modified_at != t1


class TestImpulseManager:
    @pytest.fixture
    def tmp_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ImpulseManager(base_path=tmp)
            yield mgr

    def test_save_and_load(self, tmp_manager):
        core = ImpulseCore()
        core.set_from_labels({"create": 0.9})
        tmp_manager.save(core)
        loaded = tmp_manager.load()
        assert loaded.get_primary_label() == "create"

    def test_creates_data_dir(self, tmp_manager):
        assert os.path.exists(tmp_manager.data_dir)

    def test_exists_false_when_no_file(self, tmp_manager):
        assert not tmp_manager.exists()

    def test_exists_true_after_save(self, tmp_manager):
        tmp_manager.save(ImpulseCore())
        assert tmp_manager.exists()

    def test_start_creates_default(self, tmp_manager):
        result = tmp_manager.start()
        assert "primary" in result
        assert result["primary"]["label"] == "unknown"

    def test_start_restores_existing(self, tmp_manager):
        core = ImpulseCore()
        core.set_from_labels({"protect": 1.0})
        tmp_manager.save(core)
        result = tmp_manager.start()
        assert result["primary"]["label"] == "protect"

    def test_cache_after_save(self, tmp_manager):
        core = ImpulseCore()
        core.set_from_labels({"create": 1.0})
        tmp_manager.save(core)
        assert tmp_manager.core.get_primary_label() == "create"

    def test_cache_after_load(self, tmp_manager):
        core = ImpulseCore()
        core.set_from_labels({"improve": 1.0})
        tmp_manager.save(core)
        loaded = tmp_manager.load()
        assert loaded.get_primary_label() == "improve"
        assert tmp_manager.core.get_primary_label() == "improve"

    def test_property_setter(self, tmp_manager):
        core = ImpulseCore()
        core.set_from_labels({"understand": 0.8})
        tmp_manager.core = core
        loaded = tmp_manager.load()
        assert loaded.get_primary_label() == "understand"

    def test_sync_prompt_file(self, tmp_manager):
        core = ImpulseCore()
        core.set_from_labels({"understand": 0.6, "create": 0.4})
        tmp_manager.save(core)
        prompt_path = os.path.join(tmp_manager.data_dir, "current_impulse.txt")
        assert os.path.exists(prompt_path)
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "понять" in content


class TestModuleFunctions:
    def test_default_dimensions(self):
        dims = default_dimensions()
        assert len(dims) == 4
        assert all(d.weight == 0.0 for d in dims)

    def test_impulse_labels(self):
        assert len(IMPULSE_LABELS) == 4
        assert "understand" in IMPULSE_LABELS
        assert "Что я могу понять?" in IMPULSE_LABELS.values()
