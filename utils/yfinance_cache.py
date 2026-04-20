#!/usr/bin/env python3
"""
Centralized yfinance wrapper with in-process + on-disk TTL caching.

Drop-in replacement for the most common yfinance calls:
    from utils.yfinance_cache import get_info, get_history, get_ticker

Design:
- In-process memoization (per run) → identical calls within the same script
  pay the cost once.
- On-disk pickle cache with TTL → identical calls across runs (same ticker,
  same TTL window) are served from disk instead of hitting yfinance.
- Different TTLs for different data families:
    * info / fundamentals → 24 h  (slow-changing)
    * daily prices        → 1 h   (intraday refresh OK)
    * 5-minute prices     → 5 min (rarely used)
    * financials/cashflow → 24 h
- Silent fallback: if the cache can't be read/written the call still proceeds
  live, so the module never blocks a run.
"""
from __future__ import annotations

import hashlib
import pickle
import time
from pathlib import Path
from typing import Any, Optional

import yfinance as yf

CACHE_ROOT = Path("data/cache/yf")
CACHE_ROOT.mkdir(parents=True, exist_ok=True)

# Default TTLs (seconds)
TTL_INFO = 24 * 3600
TTL_HISTORY_DAILY = 3600
TTL_HISTORY_INTRADAY = 300
TTL_FINANCIALS = 24 * 3600

# In-process memo: { key -> (expires_at, value) }
_MEMO: dict[str, tuple[float, Any]] = {}

# Stats for observability
stats = {"hits_mem": 0, "hits_disk": 0, "misses": 0, "errors": 0}


def _key(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


def _disk_path(key: str) -> Path:
    return CACHE_ROOT / f"{key}.pkl"


def _get(key: str, ttl: int) -> Optional[Any]:
    now = time.time()
    memo = _MEMO.get(key)
    if memo and memo[0] > now:
        stats["hits_mem"] += 1
        return memo[1]

    path = _disk_path(key)
    if path.exists():
        try:
            age = now - path.stat().st_mtime
            if age < ttl:
                with path.open("rb") as f:
                    value = pickle.load(f)
                _MEMO[key] = (now + ttl - age, value)
                stats["hits_disk"] += 1
                return value
        except (pickle.UnpicklingError, EOFError, OSError):
            stats["errors"] += 1
            try:
                path.unlink()
            except OSError:
                pass

    stats["misses"] += 1
    return None


def _set(key: str, value: Any, ttl: int) -> None:
    _MEMO[key] = (time.time() + ttl, value)
    try:
        with _disk_path(key).open("wb") as f:
            pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
    except (OSError, pickle.PicklingError):
        stats["errors"] += 1


def get_ticker(ticker: str) -> yf.Ticker:
    """Return a raw yf.Ticker object (not cached — cheap constructor)."""
    return yf.Ticker(ticker)


def get_info(ticker: str, ttl: int = TTL_INFO) -> dict:
    """Cached `Ticker.info`. Returns {} on error."""
    key = _key("info", ticker, ttl)
    cached = _get(key, ttl)
    if cached is not None:
        return cached
    try:
        info = yf.Ticker(ticker).info or {}
    except (KeyError, ValueError, ConnectionError, TimeoutError):
        stats["errors"] += 1
        return {}
    _set(key, info, ttl)
    return info


def get_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    ttl: Optional[int] = None,
):
    """Cached `Ticker.history`. Returns None on error."""
    if ttl is None:
        ttl = TTL_HISTORY_INTRADAY if interval != "1d" else TTL_HISTORY_DAILY
    key = _key("hist", ticker, period, interval, ttl)
    cached = _get(key, ttl)
    if cached is not None:
        return cached
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
    except (KeyError, ValueError, ConnectionError, TimeoutError):
        stats["errors"] += 1
        return None
    if df is None or df.empty:
        return df
    _set(key, df, ttl)
    return df


def get_financials(ticker: str, ttl: int = TTL_FINANCIALS):
    """Cached `Ticker.financials`. Returns None on error."""
    key = _key("financials", ticker, ttl)
    cached = _get(key, ttl)
    if cached is not None:
        return cached
    try:
        df = yf.Ticker(ticker).financials
    except (KeyError, ValueError, ConnectionError, TimeoutError):
        stats["errors"] += 1
        return None
    if df is None:
        return df
    _set(key, df, ttl)
    return df


def get_cashflow(ticker: str, ttl: int = TTL_FINANCIALS):
    """Cached `Ticker.cashflow`. Returns None on error."""
    key = _key("cashflow", ticker, ttl)
    cached = _get(key, ttl)
    if cached is not None:
        return cached
    try:
        df = yf.Ticker(ticker).cashflow
    except (KeyError, ValueError, ConnectionError, TimeoutError):
        stats["errors"] += 1
        return None
    if df is None:
        return df
    _set(key, df, ttl)
    return df


def cleanup(max_age_days: int = 7) -> int:
    """Remove cache files older than `max_age_days`. Returns count removed."""
    cutoff = time.time() - max_age_days * 86400
    n = 0
    for p in CACHE_ROOT.glob("*.pkl"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
                n += 1
        except OSError:
            pass
    return n


def print_stats() -> None:
    total = sum(stats.values())
    hit_rate = (stats["hits_mem"] + stats["hits_disk"]) / total * 100 if total else 0
    print(
        f"[yf_cache] mem={stats['hits_mem']} disk={stats['hits_disk']} "
        f"miss={stats['misses']} err={stats['errors']} hit_rate={hit_rate:.1f}%"
    )


if __name__ == "__main__":
    print("Testing yfinance cache...")
    info = get_info("AAPL")
    print(f"AAPL info keys: {len(info)}")
    info2 = get_info("AAPL")  # should hit memo
    print_stats()
    df = get_history("AAPL", period="5d")
    print(f"AAPL 5d history: {len(df) if df is not None else 'None'} rows")
    print_stats()
