# HEALER — Self-Healing Module

**Status:** ✅ All 7 phases complete · 121 tests · 0 dependencies (Python stdlib)

---

**Full project report:** `docs/HEALER_PROJECT.md`

---

## What it does

1. **Observe** — X-RAY kernel traces every request, call, and span
2. **Diagnose** — 7 detectors find problems: slow imports, unhandled errors, dead code, resource leaks, causality violations, latency anomalies, unended spans
3. **Fix** — AST transformer generates patches (lazy import, try/finally, timeout, remove dead code, close resource)
4. **Verify** — PatchResult with apply + rollback, test runner, lint checker
5. **Learn** — MetaLearner remembers results, adapts thresholds and weights

## Quick start

```bash
git clone <repo>
cd HEALER

# Demo: generate traces + run diagnostics
python main.py

# CLI diagnostics (with live streaming events)
python -m healer.diagnostics.runner

# JSON output (for CI/CD)
python -m healer.diagnostics.runner --quiet --fail-on error

# HTML report
python -m healer.diagnostics.runner --format html --output report.html

# Continuous monitoring
python -m healer.diagnostics.runner --watch --interval 30

# Run tests (121)
python -m pytest tests/

# Smoke test
python scripts/smoke_test.py

# Orchestrator API
python -m healer.api --port 8090
# → http://127.0.0.1:8090/api/v1/status

# Web dashboard
python -m healer.viewer
# → http://127.0.0.1:8085
```

## 3 operating modes

| Mode | What it does |
|------|--------------|
| **monitor** | Read-only. Finds problems and shows a report. Does not modify code. |
| **suggest** | Finds problems and shows how to fix them. Does not apply patches. |
| **auto** | Finds → fixes → runs tests. Full automation. |

## API endpoints (v1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/status` | Orchestrator status |
| GET | `/api/v1/history` | Healing cycle history |
| GET | `/api/v1/diagnostics` | List of detectors |
| GET | `/api/v1/patchers` | List of patchers |
| GET | `/api/v1/live` | Live status |
| GET | `/api/v1/events` | SSE (real-time events) |
| GET | `/api/v1/restart-required` | Restart flag |
| POST | `/api/v1/run` | Run healing cycle |
| POST | `/api/v1/mode` | Change mode |

All responses include `X-API-Version: 1.0.0`.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│ Layer 5: Meta-Learning ✅                            │
│ MetaLearner · AdaptiveStrategies · retention         │
├──────────────────────────────────────────────────────┤
│ Layer 4: Orchestrator ✅                             │
│ monitor / suggest / auto + API v1 + SSE + graceful   │
│ shutdown + restart notification                      │
├──────────────────────────────────────────────────────┤
│ Layer 3: Verification ✅                             │
│ TestRunner · LintChecker · MetricComparator · Rollback│
├──────────────────────────────────────────────────────┤
│ Layer 2: Patch Engine ✅                             │
│ PythonPatcher (AST) · JSPatcher · 5 patterns         │
├──────────────────────────────────────────────────────┤
│ Layer 1: Diagnostics ✅                             │
│ 7 detectors (BaseDetector ABC) · streaming events    │
├──────────────────────────────────────────────────────┤
│ Layer 0: X-RAY Kernel ✅                             │
│ 17 modules · Trace/Span · persistence · schema v1    │
│ TraceStoreRegistry · thread-safe (RLock)             │
└──────────────────────────────────────────────────────┘
```

## Key features

- **Zero external dependencies** — pure Python stdlib. No pip install required.
- **Runtime diagnostics** — works on execution traces, not static analysis. Finds problems invisible to linters.
- **AST patching** — syntactically valid code transformations. Not regex, not LLM.
- **Meta-learning** — remembers which patches work, adapts over time.
- **Per-project isolation** — `TraceStoreRegistry` prevents data races between projects.
- **Streaming events** — `run_diagnostics(event_callback=...)` feeds real-time events.
- **3 output formats** — table (console), JSON (machines), HTML (browser).

## Tech

- **Python 3.12+** — only requirement
- **Zero external dependencies** — all stdlib
- **AST** — syntax trees for Python patching
- **JSON on disk** — trace storage with schema versioning
- **threading.RLock** — thread-safe store
- **HTTP.server** — built-in HTTP server (stdlib)

## Installation

```bash
git clone <repo>
cd HEALER
python main.py
```

Or via pip (once published):
```bash
pip install healer-autofix
healer --help
```

## Progress

| Phase | Status | Hours |
|-------|--------|-------|
| 0. X-RAY Kernel | ✅ | 12 |
| 1. Diagnostics | ✅ | 14 |
| 2. Patch Engine | ✅ | 20 |
| 3. Verification | ✅ | 8 |
| 4. Orchestrator | ✅ | 14 |
| 5. Meta-learning | ✅ | 10 |
| 6. Docs/CI | ✅ | 8 |
| 7. Architectural fixes | ✅ | + |
| **Total** | **100%** | **86+** |

## License

MIT
