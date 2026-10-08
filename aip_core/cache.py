"""
aip_core/cache.py — Content-addressed SQLite cache for LLM calls.

Mirrors `Plaksha_AI_in_Practise_modified/aip/cache.py`:
- Keys every response by SHA-256(model, prompt, temperature, extra_key).
- Supports `AIP_OFFLINE=1` (serves only from cache; raises OfflineCacheMiss on miss).
- Includes `sample_idx` support so self-consistency sampling at temperature > 0
  does not silently return the same cached output.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from typing import Any, Optional
from config import CACHE_DIR, CACHE_ENABLED, OFFLINE_MODE

_LOCK = threading.Lock()
_CONN: Optional[sqlite3.Connection] = None


class OfflineCacheMiss(RuntimeError):
    """Raised when OFFLINE_MODE is enabled and a request is not in the SQLite cache."""


def _db() -> sqlite3.Connection:
    global _CONN
    db_path = CACHE_DIR / "cache.sqlite"
    if _CONN is not None and not db_path.exists():
        _CONN = None
    if _CONN is None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _CONN = sqlite3.connect(str(db_path), check_same_thread=False)
        _CONN.execute(
            """
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                model TEXT NOT NULL,
                created_at REAL NOT NULL,
                value TEXT NOT NULL
            )
            """
        )
        _CONN.commit()
    return _CONN


def make_key(kind: str, model: str, payload: Any) -> str:
    """Create a deterministic 32-character SHA-256 fingerprint for any request."""
    blob = json.dumps(
        {"kind": kind, "model": model, "payload": payload},
        sort_keys=True,
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:32]


def get(key: str) -> Optional[Any]:
    """Look up a cached response by its SHA-256 key. Returns None on cache miss."""
    if not CACHE_ENABLED:
        return None
    with _LOCK:
        row = _db().execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    if row is None:
        if OFFLINE_MODE:
            raise OfflineCacheMiss(
                f"AIP_OFFLINE=1 and key {key} was not found in {CACHE_DIR / 'cache.sqlite'}."
            )
        return None
    return json.loads(row[0])


def put(key: str, kind: str, model: str, value: Any) -> None:
    """Save a response into the SQLite cache."""
    if not CACHE_ENABLED:
        return
    with _LOCK:
        _db().execute(
            "INSERT OR REPLACE INTO kv (key, kind, model, created_at, value) VALUES (?, ?, ?, ?, ?)",
            (key, kind, model, time.time(), json.dumps(value, default=str)),
        )
        _db().commit()


def stats() -> dict[str, int]:
    """Return total cached items grouped by kind (e.g., {'chat': 12, 'rag': 5})."""
    with _LOCK:
        rows = _db().execute("SELECT kind, COUNT(*) FROM kv GROUP BY kind").fetchall()
    return {kind: int(count) for kind, count in rows}


def clear() -> int:
    """Wipe all entries from the SQLite cache table."""
    global _CONN
    with _LOCK:
        try:
            cur = _db().execute("DELETE FROM kv")
            _db().commit()
            return cur.rowcount
        except Exception:
            _CONN = None
            return 0

