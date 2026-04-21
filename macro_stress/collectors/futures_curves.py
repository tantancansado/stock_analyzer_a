"""Futures curve-shape collector using yfinance history."""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)


def _strip_tz(index: pd.Index) -> pd.Index:
    dt_index = pd.to_datetime(index)
    return dt_index.tz_localize(None) if getattr(dt_index, "tz", None) is not None else dt_index


def _history_close(ticker: str, period: str = "max") -> Optional[pd.Series]:
    try:
        hist = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
        if hist.empty or "Close" not in hist.columns:
            return None
        series = hist["Close"].dropna()
        series.index = _strip_tz(series.index)
        return series.astype(float)
    except Exception as e:
        log.warning("curve history failed for %s: %s", ticker, e)
        return None


def fetch(symbols: list[str]) -> Optional[dict]:
    """Return current curve metrics plus a historical spread series.

    Positive spread = backwardation = tighter physical market.
    """
    if not symbols or len(symbols) < 2:
        log.warning("curve symbols too short: %s", symbols)
        return None

    front, deferred = symbols[0], symbols[1]
    front_h = _history_close(front)
    deferred_h = _history_close(deferred)
    if front_h is None or deferred_h is None or front_h.empty or deferred_h.empty:
        return None

    df = pd.concat([front_h.rename("front"), deferred_h.rename("deferred")], axis=1).dropna()
    if df.empty:
        return None

    df["spread_pct"] = (df["front"] - df["deferred"]) / df["front"] * 100.0
    df = df.dropna()
    if df.empty:
        return None

    latest = df.iloc[-1]
    hist = df["spread_pct"]
    percentile = float((hist.iloc[-1] >= hist.tail(min(len(hist), 252))).mean() * 100.0)

    if latest["spread_pct"] > 0.1:
        state = "BACKWARDATION"
    elif latest["spread_pct"] < -0.1:
        state = "CONTANGO"
    else:
        state = "FLAT"

    return {
        "curve_state": state,
        "backwardation_pct": round(float(latest["spread_pct"]), 3),
        "front_price": round(float(latest["front"]), 2),
        "deferred_price": round(float(latest["deferred"]), 2),
        "percentile_1y": round(percentile, 1),
        "history": hist,
    }
