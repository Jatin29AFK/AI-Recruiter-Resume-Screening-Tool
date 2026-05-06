from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

VISITOR_FILE = DATA_DIR / "visitor_count.json"
_counter_lock = Lock()


def _ensure_file():
    if not VISITOR_FILE.exists():
        VISITOR_FILE.write_text(json.dumps({"count": 0}), encoding="utf-8")


def _read_count() -> int:
    _ensure_file()
    try:
        data = json.loads(VISITOR_FILE.read_text(encoding="utf-8"))
        return int(data.get("count", 0))
    except Exception:
        return 0


def _write_count(count: int) -> None:
    VISITOR_FILE.write_text(json.dumps({"count": count}), encoding="utf-8")


def register_visit() -> int:
    with _counter_lock:
        current = _read_count()
        updated = current + 1
        _write_count(updated)
        return updated


def get_visitor_count() -> int:
    with _counter_lock:
        return _read_count()