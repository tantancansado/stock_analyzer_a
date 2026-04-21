"""Futures curve-shape collector using yfinance.

Detects backwardation vs contango, which is a strong near-term tightness signal.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)


def _last_close(ticker: str) -> Optional[float]:
    try:
        hist = yf.Ticker(ticker).history(period="1y", interval="1d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        log.warning("yfinance fetch failed for %s: %s", ticker, e)
        return None


def _spread_series(front: str, nxt: str) -> Optional[pd.Series]:
    try:
        front_h = yf.Ticker(front).history(period="1y", interval="1d")["Close"]
        next_h = yf.Ticker(nxt).history(period="1y", interval="1d")["Close"]
        if front_h.empty or next_h.empty:
            return None
        df = pd.concat([front_h, next_h], axis=1).dropna()
        df.columns = ["front", "next"]
        return (df["front"] - df["next"]) / df["front"] * 100.0
    except Exception as e:
        log.warning("spread series failed %s/%s: %s", front, nxt, e)
        return None


def fetch(ticker_chain: list[str]) -> Optional[dict]:
    """Given [front, next, next+1] tickers, return curve shape metrics.

    Positive `backwardation_pct` = front above deferred = tight physical market.
    """
    if not ticker_chain or len(ticker_chain) < 2:
        log.warning("ticker_chain too short: %s", ticker_chain)
        return None

    front, nxt = ticker_chain[0], ticker_chain[1]
    front_px = _last_close(front)
    next_px = _last_close(nxt)
    if front_px is None or next_px is None:
        return None

    backwardation_pct = (front_px - next_px) / front_px * 100.0
    if backwardation_pct > 0.1:
        state = "BACKWARDATION"
    elif backwardation_pct < -0.1:
        state = "CONTANGO"
    else:
        state = "FLAT"

    percentile = None
    series = _spread_series(front, nxt)
    if series is not None and len(series) > 30:
        rank = (series.iloc[-1] > series).mean()
        percentile = float(round(rank * 100, 1))

    return {
        "curve_state": state,
        "backwardation_pct": round(backwardation_pct, 3),
        "front_price": round(front_px, 2),
        "next_price": round(next_px, 2),
        "spread_percentile_1y": percentile,
    }
