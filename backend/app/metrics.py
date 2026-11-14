"""Minimal in-process metrics for operational monitoring.

Deliberately dependency-free: the deployment target is one process on a small machine.
Counters are exposed to operators (monitor role) through ``GET /api/v1/admin/metrics``;
nothing here is public, and no label contains personal data (no IPs, no question text).

Scrape with any HTTP checker, e.g.:

    curl -s -H "X-Admin-Token: $MONITOR" https://host/api/v1/admin/metrics | python -m json.tool

If the app is ever scaled to several processes or you need Prometheus, replace this
module with a real client — the call sites are the same.
"""
from __future__ import annotations

import threading
import time
from typing import Any

_STARTED = time.time()


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}

    def inc(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
        return {
            "uptime_s": int(time.time() - _STARTED),
            "counters": dict(sorted(counters.items())),
            "ai": {
                key.split(".", 1)[1]: value
                for key, value in counters.items()
                if key.startswith("ai.")
            },
            "http": {
                key.split(".", 1)[1]: value
                for key, value in counters.items()
                if key.startswith("http.")
            },
        }

    def reset(self) -> None:
        """Test helper: clear counters without restarting the process."""
        with self._lock:
            self._counters.clear()


metrics = Metrics()
