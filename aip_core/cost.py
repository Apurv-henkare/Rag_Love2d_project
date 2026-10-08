"""
aip_core/cost.py — Token accounting, USD cost estimation, latency percentiles, and budget limits.

Mirrors `Plaksha_AI_in_Practise_modified/aip/cost.py`:
- Tracks input tokens, output tokens, USD cost, median latency (p50), and tail latency (p95).
- Enforces a hard USD ceiling (`BudgetExceeded`) so runaway loops cannot drain API quota.
"""
from __future__ import annotations

import contextvars
import statistics
import threading
from dataclasses import dataclass, field
from typing import List, Optional
from config import BUDGET_USD, FREE_PREFIXES, PRICES_PER_MTOK


class BudgetExceeded(RuntimeError):
    """Raised when cumulative spend exceeds the active Budget limit."""


@dataclass
class CallRecord:
    model: str
    tokens_in: int
    tokens_out: int
    usd: float
    latency_ms: float
    cached: bool = False
    priced: bool = True


def is_priced(model: str) -> bool:
    return model in PRICES_PER_MTOK or model.startswith(FREE_PREFIXES)


def price_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    """
    Calculate the dollar cost of an LLM call using the formula:
      Cost = (tokens_in / 1,000,000) * price_in + (tokens_out / 1,000,000) * price_out
    """
    p_in, p_out = PRICES_PER_MTOK.get(model, (0.0, 0.0))
    return (tokens_in * p_in + tokens_out * p_out) / 1_000_000.0


def estimate_tokens(text: str) -> int:
    """Fast heuristic token counter (~4 chars per token) when provider usage is absent."""
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class Budget:
    limit_usd: float = field(default_factory=lambda: BUDGET_USD)
    calls: List[CallRecord] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _token: Optional[contextvars.Token] = field(default=None, repr=False)

    def record(self, rec: CallRecord) -> None:
        with self._lock:
            self.calls.append(rec)
            total = self.usd
        if total > self.limit_usd:
            raise BudgetExceeded(
                f"Budget exceeded: spent ${total:.4f} > limit ${self.limit_usd:.2f} "
                f"after {len(self.calls)} calls."
            )

    @property
    def usd(self) -> float:
        return sum(c.usd for c in self.calls if not c.cached)

    @property
    def tokens_in(self) -> int:
        return sum(c.tokens_in for c in self.calls if not c.cached)

    @property
    def tokens_out(self) -> int:
        return sum(c.tokens_out for c in self.calls if not c.cached)

    @property
    def cached_hits(self) -> int:
        return sum(1 for c in self.calls if c.cached)

    @property
    def latency_p50_ms(self) -> float:
        """Median latency (50th percentile) across live (non-cached) calls."""
        live = [c.latency_ms for c in self.calls if not c.cached]
        return statistics.median(live) if live else 0.0

    @property
    def latency_p95_ms(self) -> float:
        """Tail latency (95th percentile) across live (non-cached) calls."""
        live = sorted(c.latency_ms for c in self.calls if not c.cached)
        if not live:
            return 0.0
        idx = min(len(live) - 1, int(round(0.95 * (len(live) - 1))))
        return live[idx]

    def summary_dict(self) -> dict[str, float | int]:
        return {
            "calls_total": len(self.calls),
            "calls_live": len(self.calls) - self.cached_hits,
            "calls_cached": self.cached_hits,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "usd": round(self.usd, 6),
            "latency_p50_ms": round(self.latency_p50_ms, 1),
            "latency_p95_ms": round(self.latency_p95_ms, 1),
        }

    def report(self) -> str:
        s = self.summary_dict()
        return (
            f"calls={s['calls_total']} (live={s['calls_live']}, cached={s['calls_cached']}) | "
            f"in={s['tokens_in']:,} tok | out={s['tokens_out']:,} tok | "
            f"cost=${s['usd']:.4f} / ${self.limit_usd:.2f} | "
            f"p50={s['latency_p50_ms']:.0f}ms | p95={s['latency_p95_ms']:.0f}ms"
        )

    def __enter__(self) -> "Budget":
        self._token = _ACTIVE.set(self)
        return self

    def __exit__(self, *exc) -> None:
        if self._token is not None:
            _ACTIVE.reset(self._token)


_GLOBAL = Budget()
_ACTIVE: contextvars.ContextVar[Budget] = contextvars.ContextVar("aip_budget", default=_GLOBAL)


def current_budget() -> Budget:
    return _ACTIVE.get()


def global_budget() -> Budget:
    return _GLOBAL


def record_call(
    model: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
    cached: bool = False,
) -> CallRecord:
    """Record a single LLM call into both the global budget and any active scoped Budget."""
    usd = 0.0 if cached else price_usd(model, tokens_in, tokens_out)
    rec = CallRecord(
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        usd=usd,
        latency_ms=latency_ms,
        cached=cached,
        priced=is_priced(model),
    )
    active = current_budget()
    active.record(rec)
    if active is not _GLOBAL:
        _GLOBAL.record(rec)
    return rec


def reset_session() -> None:
    """Clear all session calls so calls_total=0, usd=0, p50=0, p95=0."""
    with _GLOBAL._lock:
        _GLOBAL.calls.clear()

