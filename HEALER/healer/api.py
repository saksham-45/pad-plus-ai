"""HTTP API для управления HEALER Orchestrator.

Запуск:
    python -m healer.api
    python -m healer.api --port 8090 --project /path/to/project
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from aethon.xray.version import API_VERSION
from healer.orchestrator import HealerOrchestrator, HealerMode


DEFAULT_PORT = 8090
orchestrator: HealerOrchestrator | None = None
_sse_diagnostics_callback: Any = None


class HealerAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        if args and args[0] != "GET" and self.path != "/api/live":
            super().log_message(format, *args)

    def _normalize_path(self) -> str:
        """Normalize /api/v1/... to /api/... preserving query string."""
        raw = self.path
        if raw.startswith("/api/v1/"):
            return "/api/" + raw[len("/api/v1/"):]
        return raw

    def _send_json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-API-Version", API_VERSION)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_error(self, msg: str, status: int = 400):
        self._send_json({"error": msg}, status)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        path = self._normalize_path()
        handlers = {
            "/api/status": self._handle_status,
            "/api/history": self._handle_history,
            "/api/diagnostics": self._handle_diagnostics,
            "/api/patchers": self._handle_patchers,
            "/api/live": self._handle_live,
            "/api/events": self._handle_events,
            "/api/restart-required": self._handle_restart_required,
        }
        handler = handlers.get(path)
        if handler:
            handler()
        else:
            self._send_error("Not found", 404)

    def do_POST(self):
        path = self._normalize_path()
        handlers = {
            "/api/run": self._handle_run,
            "/api/mode": self._handle_set_mode,
        }
        handler = handlers.get(path)
        if handler:
            handler()
        else:
            self._send_error("Not found", 404)

    def _handle_status(self):
        if not orchestrator:
            self._send_json({"error": "orchestrator not initialized"}, 500)
            return
        self._send_json(orchestrator.get_status())

    def _handle_history(self):
        if not orchestrator:
            self._send_json([])
            return
        limit = int(self.path.split("?limit=")[1]) if "?limit=" in self.path else 10
        self._send_json({"cycles": orchestrator.get_history(limit)})

    def _handle_diagnostics(self):
        if not orchestrator:
            self._send_json([])
            return
        detectors = [{"name": n, "doc": d.__class__.__doc__ or ""} for n, d in DETECTORS]
        self._send_json({"detectors": detectors})

    def _handle_patchers(self):
        if not orchestrator:
            self._send_json({})
            return
        patchers_info = {}
        for name, patcher in orchestrator.patchers.items():
            patchers_info[name] = {
                "language": patcher.language,
                "patterns": patcher.get_supported_patterns(),
            }
        self._send_json({"patchers": patchers_info})

    def _handle_live(self):
        if not orchestrator:
            self._send_json({"status": "idle"})
            return
        status = orchestrator.get_status()
        self._send_json(status)

    def _handle_events(self):
        """SSE endpoint для real-time событий healing цикла.
        Использует event_callback из run_diagnostics() для streaming."""
        global _sse_diagnostics_callback
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        def _on_diag_event(event: dict):
            try:
                etype = event.get("type", "unknown")
                msg = f"event: diag_{etype}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                self.wfile.write(msg.encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

        _sse_diagnostics_callback = _on_diag_event

        if orchestrator:
            def on_orch_event(event: str, data: dict):
                try:
                    msg = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    pass
            orchestrator.on_event(on_orch_event)

        try:
            while True:
                self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
                time.sleep(5)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            _sse_diagnostics_callback = None

    def _handle_run(self):
        if not orchestrator:
            self._send_error("orchestrator not initialized", 500)
            return
        body = self._read_body()
        trace_path = body.get("trace_path", None)
        cycle = orchestrator.run_cycle(trace_path=trace_path,
                                       diagnostics_callback=_sse_diagnostics_callback)
        self._send_json(cycle.to_dict())

    def _handle_set_mode(self):
        if not orchestrator:
            self._send_error("orchestrator not initialized", 500)
            return
        body = self._read_body()
        mode = body.get("mode", "")
        if mode not in ("monitor", "suggest", "auto"):
            self._send_error(f"Invalid mode: {mode}. Use: monitor, suggest, auto", 400)
            return
        orchestrator.set_mode(mode)
        self._send_json({"mode": mode, "status": "ok"})

    def _handle_restart_required(self):
        if not orchestrator:
            self._send_json({"restart_required": False})
            return
        self._send_json({"restart_required": orchestrator.check_restart_required()})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HEALER Orchestrator API")
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--project", default=None, help="Путь к проекту для авто-лечения")
    parser.add_argument("--mode", default="monitor", choices=["monitor", "suggest", "auto"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global orchestrator

    args = parse_args(argv)

    orchestrator = HealerOrchestrator(
        project_path=args.project,
        mode=args.mode,
    )

    server = HTTPServer((args.host, args.port), HealerAPIHandler)

    atexit.register(server.server_close)
    atexit.register(lambda: print("  Server closed"))

    def _handle_signal(signum, frame):
        print(f"\n  Signal {signum} received, shutting down...")
        if orchestrator:
            orchestrator.stop()
        server.server_close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_signal)

    print(f"\n{'='*50}")
    print(f"  HEALER Orchestrator API")
    print(f"{'='*50}")
    print(f"  URL:  http://{args.host}:{args.port}")
    print(f"  Mode: {args.mode}")
    print(f"  Project: {args.project or 'not set'}")
    print(f"{'='*50}")
    print(f"  API Version: {API_VERSION}")
    print(f"  Endpoints:")
    print(f"    GET  /api/v1/status       — статус")
    print(f"    GET  /api/v1/history      — история циклов")
    print(f"    GET  /api/v1/diagnostics  — список детекторов")
    print(f"    GET  /api/v1/patchers     — список патчеров")
    print(f"    GET  /api/v1/live         — live status")
    print(f"    POST /api/v1/run          — запустить healing cycle")
    print(f"    POST /api/v1/mode         — сменить режим")
    print(f"{'='*50}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutdown requested...")
    finally:
        server.server_close()
        print("  Server closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
