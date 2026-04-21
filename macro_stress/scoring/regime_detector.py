"""Historical analogue engine for Macro Stress markets."""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Optional

import pandas as pd
import yfinance as yf


@dataclass
class AnalogueResult:
    analogues: list[dict]
    history_ready: bool
    note: str
    chart_series: list[dict]


def _strip_tz(index: pd.Index) -> pd.Index:
    dt_index = pd.to_datetime(index)
    return dt_index.tz_localize(None) if getattr(dt_index, "tz", None) is not None else dt_index


def _weekly_signal_history(signals: dict[str, dict]) -> pd.DataFrame:
    series_map = {}
    for name, signal in signals.items():
        hist = signal.get("history_scores")
        if hist is None or getattr(hist, "empty", True):
            continue
        s = pd.Series(hist).copy()
        s.index = pd.to_datetime(s.index, errors="coerce")
        s = s.dropna().sort_index()
        if s.empty:
            continue
        series_map[name] = s.resample("W-FRI").last().dropna()
    if not series_map:
        return pd.DataFrame()
    return pd.concat(series_map, axis=1).sort_index()


def _load_price_history(primary_ticker: str, start: str) -> pd.Series:
    hist = yf.Ticker(primary_ticker).history(start=start, period="max", interval="1d", auto_adjust=False)
    if hist.empty or "Close" not in hist.columns:
        return pd.Series(dtype=float)
    close = hist["Close"].dropna().astype(float)
    close.index = _strip_tz(close.index)
    return close


def _forward_return(series: pd.Series, base_date: pd.Timestamp, days: int) -> Optional[float]:
    if series.empty:
        return None
    try:
        base_idx = series.index.searchsorted(base_date)
        fwd_idx = series.index.searchsorted(base_date + pd.Timedelta(days=days))
    except Exception:
        return None
    if base_idx >= len(series) or fwd_idx >= len(series):
        return None
    base = float(series.iloc[base_idx])
    fwd = float(series.iloc[fwd_idx])
    if base == 0:
        return None
    return round((fwd / base - 1.0) * 100.0, 1)


def _annotate_event(events: list[dict], date: pd.Timestamp) -> tuple[str, Optional[str]]:
    if not events:
        return (date.strftime("%Y-%m-%d"), None)
    best = None
    best_delta = None
    for event in events:
        try:
            ev_date = pd.Timestamp(event.get("date"))
        except Exception:
            continue
        delta = abs((ev_date - date).days)
        if best_delta is None or delta < best_delta:
            best = event
            best_delta = delta
    if best and best_delta is not None and best_delta <= 21:
        return (str(best.get("name") or date.strftime("%Y-%m-%d")), best.get("note"))
    return (date.strftime("%Y-%m-%d"), None)


def _build_chart_series(price_history: pd.Series, score_history: pd.Series) -> list[dict]:
    if price_history.empty:
        return []
    weekly_price = price_history.resample("W-FRI").last().dropna()
    if not score_history.empty:
        weekly_price = pd.concat([weekly_price.rename("price"), score_history.rename("stress_score")], axis=1)
    else:
        weekly_price = weekly_price.to_frame(name="price")
        weekly_price["stress_score"] = None
    weekly_price = weekly_price.dropna(subset=["price"]).tail(260)
    output = []
    for idx, row in weekly_price.iterrows():
        output.append({
            "date": idx.strftime("%Y-%m-%d"),
            "price": round(float(row["price"]), 2),
            "stress_score": round(float(row["stress_score"]), 1) if pd.notna(row["stress_score"]) else None,
        })
    return output


def find_analogues(
    *,
    signals: dict[str, dict],
    primary_ticker: str,
    market_cfg: dict,
) -> AnalogueResult:
    history = _weekly_signal_history(signals)
    current_vector = {
        name: float(signal["score"])
        for name, signal in signals.items()
        if signal.get("score") is not None
    }
    weights = {
        name: float(signal.get("weight", 0.0))
        for name, signal in signals.items()
        if signal.get("score") is not None
    }

    price_history = _load_price_history(primary_ticker, market_cfg.get("history_start", "2000-01-01"))
    if history.empty or len(current_vector) < 2:
        return AnalogueResult(
            analogues=[],
            history_ready=False,
            note="No hay suficiente histórico de señales para buscar análogos todavía.",
            chart_series=_build_chart_series(price_history, pd.Series(dtype=float)),
        )

    if market_cfg.get("history_start"):
        history = history[history.index >= pd.Timestamp(market_cfg["history_start"])]
    history = history[history.index <= pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=90)]
    min_signals = int(market_cfg.get("analogy_min_signals", 3))
    k = int(market_cfg.get("analogy_k", 5))

    candidates = []
    composite_history = []
    for idx, row in history.iterrows():
        shared = [name for name in current_vector if pd.notna(row.get(name))]
        if len(shared) < min_signals:
            continue
        diffs = [(float(row[name]) - current_vector[name]) ** 2 for name in shared]
        distance = sqrt(sum(diffs) / len(diffs))
        similarity = max(0.0, 100.0 - distance)
        weight_sum = sum(weights[name] for name in shared if weights.get(name, 0) > 0)
        if weight_sum > 0:
            hist_score = sum(float(row[name]) * weights[name] for name in shared if weights.get(name, 0) > 0) / weight_sum
        else:
            hist_score = sum(float(row[name]) for name in shared) / len(shared)
        composite_history.append((idx, hist_score))
        candidates.append((idx, distance, similarity, hist_score, shared))

    score_history = pd.Series({idx: score for idx, score in composite_history}).sort_index()
    chart_series = _build_chart_series(price_history, score_history)
    if len(candidates) < max(3, k):
        return AnalogueResult(
            analogues=[],
            history_ready=False,
            note="Histórico insuficiente: aún no hay suficientes fechas comparables con al menos 3 señales.",
            chart_series=chart_series,
        )

    events = market_cfg.get("historical_events", [])
    top = sorted(candidates, key=lambda item: item[1])[:k]
    analogues = []
    for idx, distance, similarity, hist_score, shared in top:
        title, event_note = _annotate_event(events, idx)
        analogues.append({
            "date": idx.strftime("%Y-%m-%d"),
            "name": title,
            "event": event_note,
            "score": round(float(hist_score), 1),
            "similarity": round(float(similarity), 1),
            "shared_signals": shared,
            "forward_30d_return": _forward_return(price_history, idx, 30),
            "forward_60d_return": _forward_return(price_history, idx, 60),
            "forward_90d_return": _forward_return(price_history, idx, 90),
        })

    note = "KNN sobre señales históricas normalizadas. Se excluyen los últimos 90 días para evitar análogos triviales."
    return AnalogueResult(
        analogues=analogues,
        history_ready=True,
        note=note,
        chart_series=chart_series,
    )
