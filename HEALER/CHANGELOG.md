# Changelog

## 1.0.0 (2026-06-09)

### Added
- X-RAY kernel: Trace/Span, persistence, causal validator, schema versioning
- 7 detectors: SpanAnalyzer, SlowImport, ErrorPath, DeadCode, ResourceLeak, CausalViolation, LatencyAnomaly
- BaseDetector ABC — contract for all detectors, streaming events via `event_callback`
- AST Patch Engine: 5 patterns (lazy_import, try_finally, add_timeout, remove_dead, close_resource)
- BasePattern ABC — contract for all patterns, `can_apply()` + `apply()` with `diff_lines` metadata
- PythonPatcher + JSPatcher, PatchResult with apply/rollback/diff
- Verification: TestRunner, LintChecker, MetricComparator, RollbackEngine
- Orchestrator: 3 modes (monitor/suggest/auto), graceful shutdown, restart notification
- HTTP API v1: 9 endpoints, `X-API-Version` header, SSE events
- MetaLearner with adaptive strategies, retention (`max_age_days`, `max_records`)
- CLI runner with 3 output formats: `--format json|html|table`, `--watch` mode
- HEALER Viewer: web dashboard with live feed, span tree, self-diagnostics
- TraceStoreRegistry — per-project store isolation, thread-safe (RLock)
- CLI `healer`, `healer-api`, `healer-viewer` entry points
- Zero external dependencies — pure Python stdlib

### Documentation
- README.md (Russian), README.en.md (English)
- FOR_HUMANS.md — plain-language overview
- USE_CASES.md — 5 production scenarios
- HEALER_PROJECT.md — full technical report (14 sections)
- ADDING_DETECTOR.md, ADDING_PATTERN.md — developer guides
- Viewer docs: ARCHITECTURE.md, API.md, DEVELOPER.md, HEALER_INTEGRATION.md

### Testing
- 121 unit tests, smoke test, CI pipeline (pytest + mypy + ruff)
- Integration test for all 7 detectors
- Self-test: HEALER diagnosed healer-viewer (30+ real issues found)
