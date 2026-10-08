"""
aip_core/tracing.py — Structured JSONL span logger for RAG & Agent stages.

Mirrors `Plaksha_AI_in_Practise_modified/aip/tracing.py`:
- Writes one JSON line per pipeline step into `.aip_traces/<run>.jsonl`.
- Makes every stage (guardrail check, retrieval, prompt formatting, LLM call,
  citation validation) inspectable with exact millisecond timings.
"""
from __future__ import annotations

import contextvars
import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional
from config import TRACE_DIR

_RUN_FILE: contextvars.ContextVar[Optional[Path]] = contextvars.ContextVar("aip_trace_file", default=None)


@contextmanager
def trace_run(name: str = "rag") -> Iterator[Path]:
    """Start a named trace run and write all nested spans to `.aip_traces/<ts>-<name>.jsonl`."""
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    short_id = uuid.uuid4().hex[:6]
    path = TRACE_DIR / f"{stamp}-{name}-{short_id}.jsonl"
    token = _RUN_FILE.set(path)
    try:
        yield path
    finally:
        _RUN_FILE.reset(token)


@contextmanager
def trace(stage: str, **attrs: Any) -> Iterator[dict[str, Any]]:
    """Record a single pipeline stage with start time, duration_ms, status, and custom attributes."""
    span: dict[str, Any] = {"stage": stage, "ts": time.time(), **attrs}
    t0 = time.perf_counter()
    try:
        yield span
        span["status"] = "ok"
    except Exception as exc:
        span["status"] = "error"
        span["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        span["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        target = _RUN_FILE.get() or (TRACE_DIR / "default.jsonl")
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(span, ensure_ascii=False, default=str) + "\n")
