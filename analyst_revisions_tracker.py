#!/usr/bin/env python3
"""
Analyst revisions tracker — snapshots daily target price / recommendation / analyst count
per ticker and computes rolling deltas. Output:
  docs/analyst_revisions_history.json   (rolling 90d of snapshots)
  docs/analyst_revisions.csv            (latest-per-ticker + deltas ready to merge into value_score)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from yfinance_client import get_info, RateLimitError, YFClientError

DOCS = Path(__file__).resolve().parent / "docs"
HISTORY_FILE = DOCS / "analyst_revisions_history.json"
LATEST_CSV = DOCS / "analyst_revisions.csv"
RETENTION_DAYS = 90


def _load_history() -> dict[str, list[dict[str, Any]]]:
    if not HISTORY_FILE.exists():
        return {}
    try:
        return json.loads(HISTORY_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_history(history: dict[str, list[dict[str, Any]]]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, sort_keys=True))


def _prune(snapshots: list[dict[str, Any]], cutoff: datetime) -> list[dict[str, Any]]:
    pruned = []
    for snap in snapshots:
        try:
            snap_dt = datetime.fromisoformat(snap["date"])
            if snap_dt.tzinfo is None:
                snap_dt = snap_dt.replace(tzinfo=timezone.utc)
            if snap_dt >= cutoff:
                pruned.append(snap)
        except (KeyError, ValueError):
            continue
    return pruned


def _fetch_snapshot(ticker: str) -> dict[str, Any] | None:
    try:
        info = get_info(ticker)
    except RateLimitError:
        # No imprimir como error: es del cliente, no del ticker
        print(f"   ⚠ {ticker}: rate limited", flush=True)
        return None
    except YFClientError as exc:
        print(f"   ⚠ {ticker}: yfinance error: {exc}", flush=True)
        return None
    target_mean = info.get("targetMeanPrice")
    if target_mean is None:
        return None
    return {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "target_mean": float(target_mean),
        "target_high": _opt_float(info.get("targetHighPrice")),
        "target_low": _opt_float(info.get("targetLowPrice")),
        "reco_mean": _opt_float(info.get("recommendationMean")),
        "analyst_count": _opt_int(info.get("numberOfAnalystOpinions")),
        "current_price": _opt_float(info.get("currentPrice") or info.get("regularMarketPrice")),
    }


def _opt_float(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _opt_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _find_past(snapshots: list[dict[str, Any]], days: int) -> dict[str, Any] | None:
    if len(snapshots) < 2:
        return None
    target_date = datetime.now(timezone.utc).date() - timedelta(days=days)
    closest = None
    closest_diff = None
    for snap in snapshots[:-1]:
        try:
            snap_date = datetime.fromisoformat(snap["date"]).date()
        except (KeyError, ValueError):
            continue
        diff = abs((snap_date - target_date).days)
        if closest_diff is None or diff < closest_diff:
            closest = snap
            closest_diff = diff
    # Only return if we have at least `days // 2` of history — otherwise the delta is noise
    if closest is None or closest_diff is None or closest_diff > max(days, 2):
        return None
    return closest


def _compute_deltas(history_for_ticker: list[dict[str, Any]]) -> dict[str, Any]:
    if not history_for_ticker:
        return {}
    latest = history_for_ticker[-1]
    out: dict[str, Any] = {
        "ticker": None,
        "target_mean": latest.get("target_mean"),
        "reco_mean": latest.get("reco_mean"),
        "analyst_count": latest.get("analyst_count"),
        "snapshots": len(history_for_ticker),
    }
    for window in (1, 7, 30):
        past = _find_past(history_for_ticker, window)
        if not past:
            out[f"target_change_{window}d_pct"] = None
            out[f"reco_change_{window}d"] = None
            out[f"analyst_count_change_{window}d"] = None
            continue
        past_target = past.get("target_mean")
        past_reco = past.get("reco_mean")
        past_count = past.get("analyst_count")
        out[f"target_change_{window}d_pct"] = (
            round((latest["target_mean"] - past_target) / past_target * 100, 2)
            if past_target and latest.get("target_mean")
            else None
        )
        out[f"reco_change_{window}d"] = (
            round(past_reco - latest["reco_mean"], 2)  # lower reco_mean = better
            if past_reco is not None and latest.get("reco_mean") is not None
            else None
        )
        out[f"analyst_count_change_{window}d"] = (
            latest["analyst_count"] - past_count
            if past_count is not None and latest.get("analyst_count") is not None
            else None
        )
    # Upgrade velocity — days in last 14d where target rose vs prior
    ups = 0
    downs = 0
    recent = history_for_ticker[-15:]
    for prev, curr in zip(recent, recent[1:]):
        pt = prev.get("target_mean")
        ct = curr.get("target_mean")
        if pt and ct and pt > 0:
            delta_pct = (ct - pt) / pt * 100
            if delta_pct >= 0.5:
                ups += 1
            elif delta_pct <= -0.5:
                downs += 1
    out["upgrade_days_14d"] = ups
    out["downgrade_days_14d"] = downs
    return out


def _load_universe() -> list[str]:
    scores = DOCS / "fundamental_scores.csv"
    if scores.exists():
        df = pd.read_csv(scores, usecols=["ticker"])
        return df["ticker"].dropna().astype(str).unique().tolist()
    return []


def run(tickers: list[str], sleep_s: float = 0.4) -> None:
    history = _load_history()
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    rows = []
    for idx, ticker in enumerate(tickers, 1):
        snapshots = _prune(history.get(ticker, []), cutoff)
        snap = _fetch_snapshot(ticker)
        if snap:
            # Replace same-day snapshot if already present (idempotent re-runs)
            if snapshots and snapshots[-1].get("date") == snap["date"]:
                snapshots[-1] = snap
            else:
                snapshots.append(snap)
        history[ticker] = snapshots
        deltas = _compute_deltas(snapshots)
        deltas["ticker"] = ticker
        rows.append(deltas)
        if idx % 20 == 0:
            print(f"   {idx}/{len(tickers)} procesados", flush=True)
        time.sleep(sleep_s)

    _save_history(history)
    pd.DataFrame(rows).to_csv(LATEST_CSV, index=False)
    print(f"✅ Guardado {len(rows)} tickers → {LATEST_CSV.name}", flush=True)
    print(f"✅ Histórico ({sum(len(v) for v in history.values())} snapshots) → {HISTORY_FILE.name}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", help="Single ticker for quick test")
    parser.add_argument("--universe", default="fundamental_scores", help="Universe source")
    parser.add_argument("--sleep", type=float, default=0.4)
    args = parser.parse_args()

    tickers = [args.ticker] if args.ticker else _load_universe()
    if not tickers:
        print("❌ No hay tickers para procesar", flush=True)
        return 1
    print(f"📡 Tracking revisiones de analistas para {len(tickers)} tickers", flush=True)
    run(tickers, sleep_s=args.sleep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
