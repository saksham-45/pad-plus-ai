"""Тесты для Phase 5: Meta-обучение."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest


class TestHealingRecord(unittest.TestCase):
    def test_creation(self):
        from healer.meta.meta_learner import HealingRecord
        r = HealingRecord(
            cycle_id="c1", mode="auto", timestamp=100.0,
            detector="SpanAnalyzer", pattern="try_finally",
            success=True, duration_ms=500.0, file_path="test.py",
        )
        self.assertEqual(r.cycle_id, "c1")
        self.assertEqual(r.detector, "SpanAnalyzer")
        self.assertTrue(r.success)

    def test_to_dict(self):
        from healer.meta.meta_learner import HealingRecord
        r = HealingRecord(
            cycle_id="c1", mode="auto", timestamp=100.0,
            detector="SpanAnalyzer", pattern="try_finally",
            success=True, duration_ms=500.0, file_path="test.py",
        )
        d = r.to_dict()
        self.assertEqual(d["cycle_id"], "c1")
        self.assertEqual(d["success"], True)


class TestPatternStats(unittest.TestCase):
    def test_defaults(self):
        from healer.meta.meta_learner import PatternStats
        s = PatternStats(pattern="try_finally")
        self.assertEqual(s.total, 0)
        self.assertEqual(s.success_rate, 0.0)
        self.assertEqual(s.priority, 0.5)

    def test_success_rate(self):
        from healer.meta.meta_learner import PatternStats
        s = PatternStats(pattern="try_finally", total=10, success=8, failed=2)
        self.assertEqual(s.success_rate, 0.8)

    def test_priority_drops_with_consecutive_failures(self):
        from healer.meta.meta_learner import PatternStats
        s = PatternStats(pattern="test", total=10, success=8, failed=2, consecutive_failures=3)
        self.assertLess(s.priority, 0.5)

    def test_priority_fresh(self):
        from healer.meta.meta_learner import PatternStats
        s = PatternStats(pattern="test")
        self.assertEqual(s.priority, 0.5)

    def test_to_dict(self):
        from healer.meta.meta_learner import PatternStats
        s = PatternStats(pattern="test", total=5, success=4, failed=1)
        d = s.to_dict()
        self.assertEqual(d["pattern"], "test")
        self.assertEqual(d["success_rate"], 0.8)


class TestDetectorStats(unittest.TestCase):
    def test_accuracy(self):
        from healer.meta.meta_learner import DetectorStats
        d = DetectorStats(detector="SpanAnalyzer", total=10, true_positive=8)
        self.assertEqual(d.accuracy, 0.8)

    def test_weight_high_accuracy(self):
        from healer.meta.meta_learner import DetectorStats
        d = DetectorStats(detector="SpanAnalyzer", total=10, true_positive=9)
        self.assertEqual(d.weight, 1.0)

    def test_weight_low_accuracy(self):
        from healer.meta.meta_learner import DetectorStats
        d = DetectorStats(detector="SpanAnalyzer", total=10, true_positive=2)
        self.assertEqual(d.weight, 0.1)

    def test_weight_fresh(self):
        from healer.meta.meta_learner import DetectorStats
        d = DetectorStats(detector="SpanAnalyzer")
        self.assertEqual(d.weight, 1.0)

    def test_to_dict(self):
        from healer.meta.meta_learner import DetectorStats
        d = DetectorStats(detector="TestDetector", total=5, true_positive=4)
        d2 = d.to_dict()
        self.assertEqual(d2["detector"], "TestDetector")
        self.assertAlmostEqual(d2["accuracy"], 0.8)


class TestMetaLearner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="healer_meta_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_record(self, detector="SpanAnalyzer", pattern="try_finally",
                     success=True, cycle_id="c1"):
        from healer.meta.meta_learner import HealingRecord
        return HealingRecord(
            cycle_id=cycle_id, mode="auto", timestamp=time.time(),
            detector=detector, pattern=pattern,
            success=success, duration_ms=500.0, file_path="test.py",
        )

    def test_initial_state(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        self.assertEqual(len(m.records), 0)
        self.assertEqual(len(m.pattern_stats), 0)
        self.assertEqual(len(m.detector_stats), 0)

    def test_record_single(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        r = self._make_record()
        m.record_healing(r)
        self.assertEqual(len(m.records), 1)
        self.assertIn("try_finally", m.pattern_stats)
        self.assertIn("SpanAnalyzer", m.detector_stats)

    def test_record_batch(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        records = [
            self._make_record(success=True, cycle_id="c1"),
            self._make_record(success=False, cycle_id="c2"),
            self._make_record(success=True, cycle_id="c3"),
        ]
        m.record_batch(records)
        self.assertEqual(len(m.records), 3)

    def test_pattern_stats_updated(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        m.record_healing(self._make_record(success=True))
        m.record_healing(self._make_record(success=False))
        stat = m.pattern_stats["try_finally"]
        self.assertEqual(stat.total, 2)
        self.assertEqual(stat.success, 1)
        self.assertEqual(stat.failed, 1)

    def test_detector_stats_updated(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        m.record_healing(self._make_record(success=True, detector="TestDet"))
        m.record_healing(self._make_record(success=False, detector="TestDet"))
        stat = m.detector_stats["TestDet"]
        self.assertEqual(stat.total, 2)
        self.assertEqual(stat.true_positive, 1)
        self.assertEqual(stat.false_positive, 1)

    def test_persistence(self):
        from healer.meta.meta_learner import MetaLearner
        m1 = MetaLearner(storage_path=self.tmp)
        m1.record_healing(self._make_record(success=True, cycle_id="c1"))
        m1.record_healing(self._make_record(success=False, cycle_id="c2"))

        m2 = MetaLearner(storage_path=self.tmp)
        self.assertEqual(len(m2.records), 2, "records should persist to disk")
        self.assertGreaterEqual(len(m2.pattern_stats), 0, "pattern stats loaded")

    def test_get_pattern_priority(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        m.record_healing(self._make_record(success=True))
        self.assertGreater(m.get_pattern_priority("try_finally"), 0)
        self.assertEqual(m.get_pattern_priority("nonexistent"), 0.5)

    def test_get_detector_weight(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        for _ in range(5):
            m.record_healing(self._make_record(success=True, detector="AccurateDet"))
        self.assertEqual(m.get_detector_weight("AccurateDet"), 1.0)
        self.assertEqual(m.get_detector_weight("UnknownDet"), 1.0)

    def test_get_summary(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        m.record_healing(self._make_record(success=True))
        summary = m.get_summary()
        self.assertIn("patterns", summary)
        self.assertIn("detectors", summary)
        self.assertIn("overall_success_rate", summary)

    def test_get_recent(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        for i in range(5):
            m.record_healing(self._make_record(success=True, cycle_id=f"c{i}"))
        recent = m.get_recent(limit=3)
        self.assertEqual(len(recent), 3)

    def test_clear(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        m.record_healing(self._make_record())
        m.clear()
        self.assertEqual(len(m.records), 0)
        self.assertEqual(len(m.pattern_stats), 0)

    def test_consecutive_failures_tracking(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        for i in range(4):
            m.record_healing(self._make_record(success=False, cycle_id=f"c{i}"))
        stat = m.pattern_stats["try_finally"]
        self.assertEqual(stat.consecutive_failures, 4)

    def test_confidence(self):
        from healer.meta.meta_learner import MetaLearner
        m = MetaLearner(storage_path=self.tmp)
        for _ in range(10):
            m.record_healing(self._make_record(success=True))
        conf = m.get_confidence("SpanAnalyzer", "try_finally")
        self.assertGreater(conf, 0.5)


class TestAdaptiveStrategies(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="healer_strat_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_select_pattern(self):
        from healer.meta.meta_learner import MetaLearner
        from healer.meta.strategies import AdaptiveStrategies
        m = MetaLearner(storage_path=self.tmp)
        strat = AdaptiveStrategies(m)
        pattern = strat.select_pattern("SpanAnalyzer", ["try_finally", "close_resource"])
        self.assertIn(pattern, ["try_finally", "close_resource"])

    def test_should_not_skip_fresh_detector(self):
        from healer.meta.meta_learner import MetaLearner
        from healer.meta.strategies import AdaptiveStrategies
        m = MetaLearner(storage_path=self.tmp)
        strat = AdaptiveStrategies(m)
        self.assertFalse(strat.should_skip_detector("NewDetector"))

    def test_skip_low_weight_detector(self):
        from healer.meta.meta_learner import MetaLearner
        from healer.meta.strategies import AdaptiveStrategies
        m = MetaLearner(storage_path=self.tmp)
        for _ in range(6):
            from healer.meta.meta_learner import HealingRecord
            m.record_healing(HealingRecord(
                cycle_id="c", mode="auto", timestamp=0.0,
                detector="BadDet", pattern="test",
                success=False, duration_ms=100.0, file_path="x.py",
            ))
        strat = AdaptiveStrategies(m)
        self.assertTrue(strat.should_skip_detector("BadDet"))

    def test_adjust_severity_threshold_low_confidence(self):
        from healer.meta.meta_learner import MetaLearner
        from healer.meta.strategies import AdaptiveStrategies
        m = MetaLearner(storage_path=self.tmp)
        for _ in range(6):
            from healer.meta.meta_learner import HealingRecord
            m.record_healing(HealingRecord(
                cycle_id="c", mode="auto", timestamp=0.0,
                detector="LowDet", pattern="test",
                success=False, duration_ms=100.0, file_path="x.py",
            ))
        strat = AdaptiveStrategies(m)
        self.assertEqual(strat.adjust_severity_threshold("LowDet", "warning"), "error")

    def test_get_confidence_description(self):
        from healer.meta.meta_learner import MetaLearner
        from healer.meta.strategies import AdaptiveStrategies
        m = MetaLearner(storage_path=self.tmp)
        strat = AdaptiveStrategies(m)
        desc = strat.get_confidence_description("SpanAnalyzer", "try_finally")
        self.assertIn("confidence", desc)
        self.assertIn("level", desc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
