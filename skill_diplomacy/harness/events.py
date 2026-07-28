"""Append-only JSONL event log — the durable substrate of the harness.

Per the ACTIR handoff brief (§4): "Append-only event logs as the durable
substrate ... the adoption graph and trajectory metrics fall out of the log
for free." Nothing in the harness mutates history; every metric is a fold
over this log.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Iterator


class EventLog:
    """Append-only JSONL log. One log per experiment run."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = sum(1 for _ in self._iter_raw()) if self.path.exists() else 0

    def _iter_raw(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def append(self, type: str, **fields: Any) -> dict[str, Any]:
        event = {"seq": self._seq, "ts": time.time(), "type": type, **fields}
        with self.path.open("a") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._seq += 1
        return event

    def read(self, where: Callable[[dict], bool] | None = None) -> list[dict[str, Any]]:
        events = list(self._iter_raw())
        return [e for e in events if where(e)] if where else events

    def by_type(self, type: str) -> list[dict[str, Any]]:
        return self.read(lambda e: e["type"] == type)

    def by_state(self, state: str) -> list[dict[str, Any]]:
        return self.read(lambda e: e.get("state") == state)
