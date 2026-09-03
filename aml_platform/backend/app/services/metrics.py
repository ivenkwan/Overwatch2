"""
Minimal Prometheus-text metrics (TASK-022).

Zero-dependency counters kept in-process: HTTP requests by (method, route)
with a status bucket, plus a duration histogram. Served at GET /metrics in
Prometheus text exposition format v0.0.4 so a scraped can ingest them
without extra libraries; swap for prometheus-client when a full pipeline
lands.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

_lock = threading.Lock()
_requests: dict[tuple, int] = defaultdict(int)      # (method, route, status)
_durations: dict[tuple, list] = defaultdict(list)   # (method, route) -> seconds
_started_at: dict[tuple, float] = {}


def note_start(method: str, route: str) -> None:
    _started_at[(method, route)] = time.monotonic()


def note_end(method: str, route: str, status: int) -> None:
    with _lock:
        _requests[(method, route, status)] += 1
        started = _started_at.pop((method, route), None)
        if started is not None:
            _durations[(method, route)].append(time.monotonic() - started)


def render() -> str:
    with _lock:
        lines = ["# HELP aml_http_requests_total Total HTTP requests by route/status.",
                 "# TYPE aml_http_requests_total counter",
                 "# HELP aml_http_request_duration_seconds Request duration (last 1k per route).",
                 "# TYPE aml_http_request_duration_seconds summary"]
        for (method, route, status), count in sorted(_requests.items()):
            lines.append(
                f'aml_http_requests_total{{method="{method}",route="{route}",status="{status}"}} {count}')
        for (method, route), samples in sorted(_durations.items()):
            recent = samples[-1000:]
            total = sum(recent)
            lines.append(
                f'aml_http_request_duration_seconds_sum{{method="{method}",route="{route}"}} '
                f'{total:.6f}')
            lines.append(
                f'aml_http_request_duration_seconds_count{{method="{method}",route="{route}"}} '
                f'{len(recent)}')
        return "\n".join(lines) + "\n"


class MetricsMiddleware:
    """Starlette middleware wrapping request counting."""

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "")
        route = scope.get("path", "")

        async def wrapped_send(message: Any) -> None:
            if message["type"] == "http.response.start":
                note_end(method, route, message.get("status", 0))
            await send(message)

        note_start(method, route)
        try:
            await self.app(scope, receive, wrapped_send)
        except Exception:
            note_end(method, route, 500)
            raise
