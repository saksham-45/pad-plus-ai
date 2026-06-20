"""HEALER Viewer — веб-интерфейс для наблюдения за HEALER и самонаблюдения.

Приложение инструментировано X-RAY: каждый запрос пишет trace на диск.
HEALER может анализировать эти трейсы и находить проблемы в самом viewer.

Запуск:
    python -m healer.viewer
    python -m healer.viewer --port 9090
Или из оригинальной папки:
    cd ../healer-viewer && python viewer.py
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Пути ─────────────────────────────────────────────
# Если запущено из пакета: python -m healer.viewer
# Если запущено из оригинальной папки healer-viewer/
HEALER_DIR_CANDIDATES = [
    Path(__file__).parent.parent.parent,           # healer/viewer/viewer.py → HEALER/
    Path(__file__).parent.parent.parent / 'HEALER',  # alt package layout
    Path(__file__).parent.parent / 'HEALER',         # оригинальная healer-viewer/ → HEALER/
]
HEALER_DIR: Path | None = None
for c in HEALER_DIR_CANDIDATES:
    if (c / 'healer').is_dir() and (c / 'aethon').is_dir():
        HEALER_DIR = c.resolve()
        break

if HEALER_DIR:
    sys.path.insert(0, str(HEALER_DIR))
else:
    print('[viewer] HEALER не найден. Часть функций (диагностика) будет недоступна', file=sys.stderr)

try:
    from aethon.xray import start_trace, start_span, SpanKind, store, Trace, trace_to_summary
    XRAY_AVAILABLE = True
except ImportError:
    XRAY_AVAILABLE = False
    print('[viewer] X-RAY ядро не загружено. Трейсинг отключён.', file=sys.stderr)

VIEWER_DIR = Path(__file__).parent
TRACE_STORE_PATH = VIEWER_DIR / 'data' / 'trace_store'
STATIC_DIR = VIEWER_DIR / 'static'
INDEX_HTML = STATIC_DIR / 'index.html'
_current_trace = None
_healer_diag_result: list[dict] = []
_healer_diag_timestamp: str | None = None
_diag_tasks: dict[str, dict] = {}
_diag_events: dict[str, list[dict]] = {}
_diag_lock = threading.Lock()
_diag_executor = ThreadPoolExecutor(max_workers=1)

def init_xray():
    if not XRAY_AVAILABLE:
        return
    os.makedirs(TRACE_STORE_PATH, exist_ok=True)
    store.configure_persistence(str(TRACE_STORE_PATH))
    print(f'[viewer] X-RAY: {TRACE_STORE_PATH}')

def make_viewer_trace(name: str, metadata: dict | None=None) -> Any:
    """Создаёт trace для действия viewer-а."""
    if not XRAY_AVAILABLE:
        return None
    global _current_trace
    try:
        trace = start_trace(f'viewer.{name}', metadata=metadata or {})
        _current_trace = trace
        return trace
    except Exception:
        return None

def end_viewer_trace(trace, status: str='ok'):
    if trace is None:
        return
    try:
        trace.end(status)
    except Exception:
        pass

def _build_span_tree(spans: list[dict]) -> dict | None:
    """Строит дерево спанов из плоского списка."""
    if not spans:
        return None
    span_map = {s['span_id']: {**s, 'children': []} for s in spans}
    roots = []
    for s in span_map.values():
        pid = s.get('parent_span_id')
        if pid and pid in span_map:
            span_map[pid]['children'].append(s)
        else:
            roots.append(s)

    def _to_tree(node: dict) -> dict:
        return {
            'name': node.get('name', node.get('span_id', '')),
            'span_id': node.get('span_id', ''),
            'status': node.get('status', 'ok'),
            'duration_ms': node.get('duration_ms', 0),
            'children': [_to_tree(c) for c in node.get('children', [])],
        }

    tree_nodes = [_to_tree(r) for r in roots]
    return {'tree': tree_nodes}

def _read_traces_from_disk(store_path: Path) -> list[dict]:
    """Читает трейсы напрямую с диска, без переключения глобального store."""
    index_path = store_path / 'index.json'
    traces_dir = store_path / 'traces'
    if not index_path.exists() or not traces_dir.exists():
        return []
    try:
        index = json.loads(index_path.read_text('utf-8'))
    except Exception:
        return []
    result = []
    for trace_id, info in index.items():
        trace_file = traces_dir / f'{trace_id}.json'
        if trace_file.exists():
            try:
                data = json.loads(trace_file.read_text('utf-8'))
                result.append({
                    'trace_id': data.get('trace_id', trace_id),
                    'name': data.get('name', ''),
                    'status': data.get('status', info.get('status', 'unknown')),
                    'started_at': data.get('started_at', info.get('started_at', 0)),
                    'ended_at': data.get('ended_at', info.get('ended_at', 0)),
                    'duration_ms': data.get('duration_ms', info.get('duration_ms', 0)),
                    'span_count': len(data.get('spans', [])),
                })
            except Exception:
                result.append({
                    'trace_id': trace_id,
                    'name': '',
                    'status': info.get('status', 'unknown'),
                    'started_at': info.get('started_at', 0),
                    'ended_at': info.get('ended_at', 0),
                    'duration_ms': 0,
                    'span_count': info.get('span_count', 0),
                })
    result.sort(key=lambda x: x.get('started_at', 0), reverse=True)
    return result

def _read_trace_detail_from_disk(store_path: Path, trace_id: str) -> dict | None:
    """Читает детали трейса с диска."""
    trace_file = store_path / 'traces' / f'{trace_id}.json'
    if not trace_file.exists():
        return None
    try:
        data = json.loads(trace_file.read_text('utf-8'))
        spans = data.get('spans', [])
        tree = _build_span_tree(spans)
        return {
            'trace_id': data.get('trace_id', trace_id),
            'name': data.get('name', ''),
            'status': data.get('status', ''),
            'started_at': data.get('started_at', 0),
            'ended_at': data.get('ended_at', 0),
            'duration_ms': data.get('duration_ms', 0),
            'freeze': data.get('freeze', False),
            'span_count': len(spans),
            'spans': spans,
            'tree': tree,
        }
    except Exception:
        return None

def _run_diagnostics_worker(task_id: str, target_path: str) -> None:
    """Фоновый запуск HEALER диагностики с захватом live-событий."""
    global _healer_diag_result, _healer_diag_timestamp
    events: list[dict] = []
    with _diag_lock:
        _diag_events[task_id] = events
    try:
        from aethon.xray.trace_store import store
        from healer.diagnostics.runner import run_diagnostics

        def _on_event(event: dict):
            events.append(event)

        with _diag_lock:
            ts = store.get(target_path)
            if not ts.persist_enabled:
                ts.configure_persistence(target_path)
            store.set_active(target_path)
            all_reports = run_diagnostics(event_callback=_on_event)
            _healer_diag_result = [r.to_dict() for r in all_reports]
            _healer_diag_timestamp = datetime.now(timezone.utc).isoformat()
            store.set_active(str(TRACE_STORE_PATH))
        events.append({'type': 'diagnostics_done', 'timestamp': time.time(), 'total_reports': len(_healer_diag_result)})
        error_count = sum(1 for r in _healer_diag_result if r.get('severity') in ('error', 'critical'))
        with _diag_lock:
            _diag_tasks[task_id] = {
                'status': 'done',
                'report_count': len(_healer_diag_result),
                'error_count': error_count,
                'timestamp': _healer_diag_timestamp,
            }
    except Exception as e:
        events.append({'type': 'diagnostics_error', 'error': str(e)})
        with _diag_lock:
            _diag_tasks[task_id] = {'status': 'error', 'error': str(e)}

class ViewerHandler(BaseHTTPRequestHandler):
    timeout = 60

    def log_message(self, format, *args):
        if args and args[0] != 'GET':
            super().log_message(format, *args)

    def _send_json(self, data: Any, status: int=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_html(self, html: str, status: int=200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _send_error(self, msg: str, status: int=400):
        self._send_json({'error': msg}, status)

    def do_GET(self):
        trace = make_viewer_trace(self.path.strip('/').replace('/', '.') or 'root')
        handler_map = {'/api/status': self._handle_status, '/api/traces': self._handle_traces, '/api/trace/': self._handle_trace_detail, '/api/invoke-healer': self._handle_invoke_healer, '/api/healer-result': self._handle_healer_result, '/api/server-traces': self._handle_server_traces, '/api/diagnostics/status/': self._handle_diag_status, '/api/diagnostics/events/': self._handle_diag_events, '/api/sentry/issues': self._handle_sentry_issues}
        try:
            handled = False
            for prefix, handler in handler_map.items():
                if self.path.startswith(prefix):
                    handler()
                    handled = True
                    break
            if not handled:
                self._serve_static()
        finally:
            end_viewer_trace(trace)

    def do_POST(self):
        handlers = {'/api/patch': self._handle_patch, '/api/patch/apply': self._handle_patch_apply, '/api/patch/rollback': self._handle_patch_rollback, '/api/diagnostics/run': self._handle_invoke_healer, '/api/sentry/analyze': self._handle_sentry_analyze}
        handler = handlers.get(self.path)
        if handler:
            handler()
        else:
            self._send_error('Not found', 404)

    def _read_body(self) -> dict:
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode('utf-8'))

    def _handle_patch(self):
        """Run HEALER PythonPatcher on a file."""
        body = self._read_body()
        source_path = body.get('source_path', '')
        detector = body.get('detector', '')
        if not source_path or not detector:
            self._send_json({'success': False, 'error': 'source_path and detector required'}, 400)
            return
        if not os.path.isfile(source_path):
            self._send_json({'success': False, 'error': f'File not found: {source_path}'}, 400)
            return
        if not HEALER_DIR.exists():
            self._send_json({'success': False, 'error': 'HEALER not found'}, 503)
            return
        try:
            from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
            from healer.patcher.python_patcher import PythonPatcher
            report = DiagnosticReport(detector=detector, severity=ReportSeverity.WARNING, category=ReportCategory.CORRECTNESS, message=body.get('message', ''))
            result = PythonPatcher().patch_file(source_path, report)
            if result.success:
                with open(source_path, 'r', encoding='utf-8') as f:
                    current = f.read()
                self._send_json({'success': True, 'pattern': result.pattern, 'source_path': result.source_path, 'diff': result.diff, 'original_code': result.original_code, 'patched_code': result.patched_code, 'metadata': result.metadata})
            else:
                self._send_json({'success': False, 'error': result.error or 'No changes needed', 'pattern': result.pattern})
        except ImportError:
            self._send_json({'success': False, 'error': 'HEALER modules not available'}, 503)
        except Exception as e:
            self._send_json({'success': False, 'error': str(e)}, 500)

    def _handle_patch_apply(self):
        """Apply a patch (write patched code)."""
        body = self._read_body()
        sp = body.get('source_path', '')
        orig = body.get('original_code', '')
        patched = body.get('patched_code', '')
        if not sp or not patched:
            self._send_json({'success': False, 'error': 'source_path and patched_code required'}, 400)
            return
        if not HEALER_DIR.exists():
            self._send_json({'success': False, 'error': 'HEALER not found'}, 503)
            return
        try:
            from healer.patcher.result import PatchResult
            r = PatchResult(patcher='viewer', pattern='manual', source_path=sp, original_code=orig, patched_code=patched, success=True)
            ok = r.apply(backup=True)
            self._send_json({'success': ok, 'source_path': sp, 'backup': sp + '.healer.bak'})
        except ImportError:
            self._send_json({'success': False, 'error': 'HEALER modules not available'}, 503)
        except Exception as e:
            self._send_json({'success': False, 'error': str(e)}, 500)

    def _handle_patch_rollback(self):
        """Rollback via .healer.bak file."""
        sp = self._read_body().get('source_path', '')
        if not sp:
            self._send_json({'success': False, 'error': 'source_path required'}, 400)
            return
        try:
            if not HEALER_DIR.exists():
                self._send_json({'success': False, 'error': 'HEALER not found'}, 503)
                return
            from healer.verifier.rollback import RollbackEngine
            r = RollbackEngine().rollback(sp)
            self._send_json({'success': r.verdict.value == 'passed', 'message': r.message})
        except ImportError:
            self._send_json({'success': False, 'error': 'HEALER modules not available'}, 503)
        except Exception as e:
            self._send_json({'success': False, 'error': str(e)}, 500)

    def _serve_static(self):
        path = self.path.lstrip('/')
        if path == '' or path == 'index.html':
            filepath = INDEX_HTML
        elif path.startswith('static/'):
            filepath = STATIC_DIR / path[7:]
        else:
            filepath = STATIC_DIR / path
        if not filepath.exists():
            self._send_error('Not found', 404)
            return
        ext = filepath.suffix.lower()
        ctype = {'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml'}.get(ext, 'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        with open(filepath, 'rb') as f:
            self.wfile.write(f.read())

    def _handle_status(self):
        """Статус приложения."""
        has_healer = HEALER_DIR.exists()
        self._send_json({'app': 'healer-viewer', 'version': '0.1.0', 'timestamp': datetime.now(timezone.utc).isoformat(), 'xray': XRAY_AVAILABLE, 'healer_path': str(HEALER_DIR) if has_healer else None, 'healer_available': has_healer, 'trace_store': str(TRACE_STORE_PATH), 'diag_available': _healer_diag_result is not None})

    def _handle_server_traces(self):
        """Трейсы самого viewer-а — чтение с диска, без переключения store."""
        traces = _read_traces_from_disk(TRACE_STORE_PATH)
        self._send_json({'count': len(traces), 'traces': traces[:100]})

    def _handle_traces(self):
        """Трейсы HEALER — чтение с диска."""
        healer_store = HEALER_DIR / 'data' / 'trace_store'
        if not healer_store.exists():
            self._send_json({'traces': [], 'error': 'HEALER trace_store not found'})
            return
        traces = _read_traces_from_disk(healer_store)
        self._send_json({'count': len(traces), 'traces': traces[:100]})

    def _handle_trace_detail(self):
        trace_id = self.path.replace('/api/trace/', '').split('/')[0]
        if not trace_id:
            self._send_error('Missing trace_id', 400)
            return
        healer_store = HEALER_DIR / 'data' / 'trace_store'
        data = _read_trace_detail_from_disk(healer_store, trace_id) if healer_store.exists() else None
        if data is None:
            data = _read_trace_detail_from_disk(TRACE_STORE_PATH, trace_id)
        if data is None:
            self._send_error('Not found', 404)
            return
        self._send_json(data)

    def _handle_invoke_healer(self):
        """Запускает HEALER диагностику в фоновом потоке."""
        qs = self.path.split('?', 1)[1] if '?' in self.path else ''
        params = dict(p.split('=', 1) if '=' in p else (p, '') for p in qs.split('&') if p)
        target_raw = params.get('target', '')
        target_path = str(Path(target_raw) if target_raw else TRACE_STORE_PATH)
        if not os.path.isdir(target_path):
            self._send_error(f'Цель не найдена: {target_path}', 400)
            return
        if not HEALER_DIR or not HEALER_DIR.exists():
            self._send_error('HEALER не найден', 500)
            return
        task_id = uuid.uuid4().hex[:12]
        task = {'status': 'running'}
        with _diag_lock:
            _diag_tasks[task_id] = task
        _diag_executor.submit(_run_diagnostics_worker, task_id, target_path)
        end_viewer_trace(make_viewer_trace('invoke.healer', {'target': target_path}))
        self._send_json({'success': True, 'task_id': task_id, 'status': 'running'})

    def _handle_diag_status(self):
        """Статус фоновой диагностики по task_id."""
        task_id = self.path.replace('/api/diagnostics/status/', '').split('/')[0]
        with _diag_lock:
            task = _diag_tasks.get(task_id)
        if task is None:
            self._send_error('Task not found', 404)
            return
        self._send_json({'status': task['status'], **{k: v for k, v in task.items() if k != 'status'}})

    def _handle_diag_events(self):
        """Live-события диагностики по task_id с since-индексом."""
        rest = self.path.replace('/api/diagnostics/events/', '').split('?')
        task_id = rest[0].split('/')[0]
        since = 0
        if len(rest) > 1 and rest[1].startswith('since='):
            since = int(rest[1].split('=')[1])
        if not task_id:
            self._send_error('Missing task_id', 400)
            return
        with _diag_lock:
            task = _diag_tasks.get(task_id)
            evts = list(_diag_events.get(task_id, []))
        if task is None and not evts:
            self._send_error('Task not found', 404)
            return
        new_events = evts[since:]
        status = task['status'] if task else 'running'
        self._send_json({'events': new_events, 'since': since + len(new_events), 'done': status in ('done', 'error'), 'task_status': status})

    def _handle_healer_result(self):
        """Последний результат диагностики HEALER."""
        self._send_json({'timestamp': _healer_diag_timestamp, 'report_count': len(_healer_diag_result) if _healer_diag_result else 0, 'reports': _healer_diag_result or []})

    def _handle_sentry_issues(self):
        """GET /api/sentry/issues — список нерешённых ошибок из Sentry."""
        token = os.getenv("SENTRY_AUTH_TOKEN")
        if not token:
            self._send_json({"issues": [], "error": "SENTRY_AUTH_TOKEN не настроен"})
            return

        try:
            import urllib.request
            org = "pad-op"
            project = "pad-ai"
            url = f"https://sentry.io/api/0/projects/{org}/{project}/issues/?query=is:unresolved&limit=20"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode("utf-8"))

            issues = []
            for item in data:
                error_type = "unknown"
                if item.get("metadata", {}).get("type"):
                    error_type = item["metadata"]["type"]
                elif item.get("title"):
                    error_type = item["title"].split(":")[0].strip()[:50]

                issues.append({
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "error_type": error_type,
                    "count": item.get("count", 0),
                    "level": item.get("level", "error"),
                    "status": item.get("status", "unresolved"),
                    "first_seen": item.get("firstSeen", ""),
                    "last_seen": item.get("lastSeen", ""),
                    "permalink": item.get("permalink", ""),
                })
            self._send_json({"issues": issues, "total": len(issues)})
        except Exception as e:
            self._send_json({"issues": [], "error": str(e)})

    def _handle_sentry_analyze(self):
        """POST /api/sentry/analyze — запустить HEALER диагностику по типу ошибки."""
        body = self._read_body()
        error_type = body.get("error_type", "")
        issue_title = body.get("title", "")

        detector_map = {
            "ProviderFailedError": "ErrorPathDetector",
            "AllProvidersFailedError": "ErrorPathDetector",
            "ConnectionError": "ErrorPathDetector",
            "TimeoutError": "LatencyAnomalyDetector",
            "DatabaseError": "ResourceLeakDetector",
            "MemoryError": "HighMemoryDetector",
            "ImportError": "SlowImportDetector",
        }
        detector = detector_map.get(error_type, "ErrorPathDetector")

        if not HEALER_DIR or not HEALER_DIR.exists():
            self._send_json({"success": False, "error": "HEALER не найден"}, 500)
            return

        try:
            from healer.diagnostics.report import DiagnosticReport, ReportSeverity, ReportCategory
            from healer.patcher.python_patcher import PythonPatcher

            report = DiagnosticReport(
                detector=detector,
                severity=ReportSeverity.ERROR,
                category=ReportCategory.CORRECTNESS,
                message=f"Sentry: {error_type} — {issue_title[:200]}",
            )

            source_path = str(HEALER_DIR / "backend" / "core" / "pipeline" / "phases" / "generate.py")
            if not os.path.isfile(source_path):
                source_path = str(HEALER_DIR / "backend" / "main.py")
            if not os.path.isfile(source_path):
                source_path = str(HEALER_DIR / "viewer.py")

            result = PythonPatcher().patch_file(source_path, report)
            if result.success:
                self._send_json({
                    "success": True,
                    "detector": detector,
                    "source_path": result.source_path,
                    "pattern": result.pattern,
                    "diff": result.diff,
                    "original_code": result.original_code,
                    "patched_code": result.patched_code,
                })
            else:
                self._send_json({
                    "success": True,
                    "detector": detector,
                    "source_path": source_path,
                    "pattern": None,
                    "message": result.error or "HEALER не нашёл что чинить",
                })
        except ImportError as e:
            self._send_json({"success": False, "error": f"HEALER модули не загружены: {e}"}, 503)
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

def parse_args(argv: list[str] | None=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='HEALER Viewer')
    parser.add_argument('--port', '-p', type=int, default=8085)
    parser.add_argument('--host', default='127.0.0.1')
    return parser.parse_args(argv)

def main(argv: list[str] | None=None) -> int:
    args = parse_args(argv)
    init_xray()
    boot_trace = make_viewer_trace('startup', {'port': args.port, 'host': args.host})
    if boot_trace:
        boot_span = start_span(SpanKind.CUSTOM, 'server.listen')
        boot_span.end('ok')
        end_viewer_trace(boot_trace, 'ok')
    server = HTTPServer((args.host, args.port), ViewerHandler)
    print('\n==============================================')
    print('  HEALER Viewer')
    print('==============================================')
    print(f'  URL:    http://{args.host}:{args.port}')
    print(f'  Status: running')
    print(f"  HEALER: {('found' if HEALER_DIR and HEALER_DIR.exists() else 'not found')}")
    print('==============================================')
    print('  Open browser to the URL above. Ctrl+C to stop.\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  ⏹  Остановлен')
        server.server_close()
    return 0
if __name__ == '__main__':
    sys.exit(main())