"""Normalize heterogeneous macro signals into a common 0-100 stress scale."""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def _rolling_percentile(series: pd.Series, window: int) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    window = max(int(window), 12)
    return values.rolling(window, min_periods=max(12, min(26, window // 4))).apply(
        lambda arr: float((arr <= arr[-1]).mean() * 100.0),
        raw=True,
    )


def _score_from_percentile(percentile: Optional[float], direction: str) -> Optional[float]:
    if percentile is None or percentile != percentile:
        return None
    pct = float(percentile)
    if direction == "low_is_stress":
        return _clip(100.0 - pct)
    if direction == "high_is_stress":
        return _clip(pct)
    if direction == "extreme_is_stress":
        distance = abs(pct - 50.0) * 2.0
        return _clip(distance)
    return _clip(pct)


def band(score: Optional[float], thresholds: Optional[dict] = None) -> str:
    if score is None:
        return "unknown"
    thresholds = thresholds or {}
    green_max = float(thresholds.get("green_max", 30))
    amber_max = float(thresholds.get("amber_max", 60))
    if score < green_max:
        return "green"
    if score < amber_max:
        return "amber"
    return "red"


def regime(score: Optional[float]) -> str:
    if score is None:
        return "UNKNOWN"
    if score < 30:
        return "BALANCED"
    if score < 50:
        return "BUILDING"
    if score < 70:
        return "TIGHTENING"
    return "DISLOCATED"


def _inventory_like(raw: Any, cfg: dict) -> dict:
    if raw is None or getattr(raw, "empty", True):
        return {"score": None, "meta": {"note": "no data"}, "history_scores": None}

    series = pd.to_numeric(raw.get("value"), errors="coerce")
    if series is None or series.dropna().empty:
        return {"score": None, "meta": {"note": "no value series"}, "history_scores": None}

    lookback = int(cfg.get("lookback_periods", 260))
    pct_series = _rolling_percentile(series, lookback)
    z_series = pd.to_numeric(raw.get("zscore_52w"), errors="coerce")
    latest_value = float(series.iloc[-1])
    latest_pct = float(pct_series.iloc[-1]) if pd.notna(pct_series.iloc[-1]) else None
    latest_z = float(z_series.iloc[-1]) if z_series is not None and pd.notna(z_series.iloc[-1]) else None
    latest_pct_5y = None
    pct_5y_series = raw.get("pct_change_vs_5y_avg")
    if pct_5y_series is not None:
        pct_5y_series = pd.to_numeric(pct_5y_series, errors="coerce")
        if pd.notna(pct_5y_series.iloc[-1]):
            latest_pct_5y = float(pct_5y_series.iloc[-1])

    direction = cfg.get("direction", "low_is_stress")
    score = _score_from_percentile(latest_pct, direction)
    history_scores = pct_series.apply(lambda pct: _score_from_percentile(pct, direction))
    history_scores.index = pd.to_datetime(raw["date"], errors="coerce")
    history_scores = history_scores.dropna()

    return {
        "value": round(latest_value, 2),
        "percentile": round(latest_pct, 1) if latest_pct is not None else None,
        "z": round(latest_z, 2) if latest_z is not None else None,
        "score": round(score, 1) if score is not None else None,
        "meta": {
            "pct_change_vs_5y_avg": round(latest_pct_5y, 2) if latest_pct_5y is not None else None,
            "units": "weekly",
        },
        "history_scores": history_scores,
    }


def _curve_shape(raw: Any, cfg: dict) -> dict:
    if not raw:
        return {"score": None, "meta": {"note": "no data"}, "history_scores": None}

    history = raw.get("history")
    percentile = raw.get("percentile_1y")
    score = _score_from_percentile(percentile, cfg.get("direction", "high_is_stress"))
    history_scores = None
    if isinstance(history, pd.Series) and not history.empty:
        pct_series = _rolling_percentile(history, int(cfg.get("lookback_periods", 252)))
        history_scores = pct_series.apply(lambda pct: _score_from_percentile(pct, cfg.get("direction", "high_is_stress")))
        history_scores.index = pd.to_datetime(history.index)
        history_scores = history_scores.dropna()

    return {
        "value": round(float(raw.get("backwardation_pct", 0.0)), 2),
        "percentile": round(float(percentile), 1) if percentile is not None else None,
        "z": None,
        "score": round(score, 1) if score is not None else None,
        "meta": {
            "curve_state": raw.get("curve_state"),
            "front_price": raw.get("front_price"),
            "deferred_price": raw.get("deferred_price"),
        },
        "history_scores": history_scores,
    }


def _geopolitical(raw: Any, _cfg: dict) -> dict:
    if not raw:
        return {"score": None, "meta": {"note": "no data"}, "history_scores": None}
    escalation = float(raw.get("escalation_score", 0.0))
    tone = float(raw.get("tone_avg", 0.0))
    score = _clip(escalation * 0.8 + max(0.0, -tone) * 4.0)
    return {
        "value": int(raw.get("event_count_24h", 0)),
        "percentile": round(escalation, 1),
        "z": None,
        "score": round(score, 1),
        "meta": {
            "tone_avg": tone,
            "query": raw.get("query"),
            "event_count_30d": raw.get("event_count_30d"),
        },
        "history_scores": None,
    }


def _positioning(raw: Any, cfg: dict) -> dict:
    if not raw:
        return {"score": None, "meta": {"note": "no data"}, "history_scores": None}
    hist = raw.get("history")
    z = raw.get("zscore_3y")
    percentile = raw.get("percentile_3y")
    if z is not None:
        score = _clip(abs(float(z)) * 25.0)
    else:
        score = _score_from_percentile(percentile, cfg.get("direction", "extreme_is_stress"))

    history_scores = None
    if isinstance(hist, pd.Series) and not hist.empty:
        rolling_mean = hist.rolling(156, min_periods=26).mean()
        rolling_std = hist.rolling(156, min_periods=26).std()
        z_hist = ((hist - rolling_mean) / rolling_std).abs() * 25.0
        history_scores = z_hist.apply(lambda v: _clip(v) if pd.notna(v) else None).dropna()

    return {
        "value": round(float(raw.get("net_pct_of_open_interest", 0.0)), 2) if raw.get("net_pct_of_open_interest") is not None else None,
        "percentile": round(float(percentile), 1) if percentile is not None else None,
        "z": round(float(z), 2) if z is not None else None,
        "score": round(score, 1) if score is not None else None,
        "meta": {
            "net_contracts": raw.get("non_commercial_net"),
            "open_interest": raw.get("open_interest"),
        },
        "history_scores": history_scores,
    }


SCORERS = {
    "inventory": _inventory_like,
    "refinery": _inventory_like,
    "curve_shape": _curve_shape,
    "geopolitical": _geopolitical,
    "positioning": _positioning,
}


def score_signal(signal_cfg: dict, raw_data: Any) -> dict:
    scorer = SCORERS.get(signal_cfg.get("type"))
    if not scorer:
        return {"score": None, "meta": {"note": f"no scorer for {signal_cfg.get('type')}"}}

    result = scorer(raw_data, signal_cfg)
    return {
        "label": signal_cfg.get("label", signal_cfg.get("type", "signal")),
        "weight": float(signal_cfg.get("weight", 0.0)),
        "direction": signal_cfg.get("direction"),
        "value": result.get("value"),
        "percentile": result.get("percentile"),
        "z": result.get("z"),
        "score": result.get("score"),
        "contribution": None,
        "meta": result.get("meta", {}),
        "history_scores": result.get("history_scores"),
    }


def compose(signals: dict[str, dict], thresholds: Optional[dict] = None) -> dict:
    weighted = 0.0
    used_weight = 0.0
    used_count = 0
    normalized = {}

    for name, signal in signals.items():
        weight = float(signal.get("weight", 0.0))
        score = signal.get("score")
        contribution = round(float(score) * weight, 1) if score is not None else None
        clean = {k: v for k, v in signal.items() if k != "history_scores"}
        clean["contribution"] = contribution
        clean["history_ready"] = signal.get("history_scores") is not None and not signal.get("history_scores").empty
        normalized[name] = clean
        if score is None or weight <= 0:
            continue
        weighted += float(score) * weight
        used_weight += weight
        used_count += 1

    composite = round(weighted / used_weight, 1) if used_weight > 0 else None
    return {
        "stress_score": composite,
        "band": band(composite, thresholds),
        "regime": regime(composite),
        "signals_used": used_count,
        "coverage_pct": round(used_weight * 100.0, 1),
        "signals": normalized,
    }
