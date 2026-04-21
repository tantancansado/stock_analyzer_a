"""Turn collector outputs into 0-100 sub-scores + weighted composite."""
from __future__ import annotations

from typing import Any, Optional

BANDS = [
    (0, 25, "calm"),
    (25, 50, "watch"),
    (50, 75, "elevated"),
    (75, 101, "crisis"),
]


def _band(score: float) -> str:
    for lo, hi, name in BANDS:
        if lo <= score < hi:
            return name
    return "unknown"


def _clip(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _score_inventory(data, direction: str) -> tuple[Optional[float], dict]:
    # Contrarian: low inventory (negative z-score) → high stress.
    if data is None or getattr(data, "empty", True):
        return None, {"note": "no data"}
    last = data.iloc[-1]
    z = last.get("zscore_52w")
    pct_5y = last.get("pct_change_vs_5y_avg")
    if z is None or (isinstance(z, float) and z != z):
        return None, {"note": "insufficient history"}

    raw = -float(z) * 25.0 + 50.0 if direction == "contrarian" else float(z) * 25.0 + 50.0
    score = _clip(raw)
    return score, {
        "latest_value": float(last["value"]),
        "zscore_52w": round(float(z), 2),
        "pct_change_vs_5y_avg": round(float(pct_5y), 2) if pct_5y is not None else None,
        "direction": direction,
    }


def _score_curve(data) -> tuple[Optional[float], dict]:
    if not data:
        return None, {"note": "no data"}
    back = data.get("backwardation_pct", 0.0)
    # strong backwardation (≥2%) ≈ 90, flat ≈ 50, strong contango (≤-2%) ≈ 10
    raw = 50.0 + back * 20.0
    return _clip(raw), data


def _score_geopolitical(data) -> tuple[Optional[float], dict]:
    if not data:
        return None, {"note": "no data"}
    esc = float(data.get("escalation_score", 0))
    tone = float(data.get("tone_avg", 0.0))
    tone_penalty = _clip(-tone * 5.0, -20.0, 30.0)
    raw = esc * 0.7 + tone_penalty + 15.0
    return _clip(raw), data


def _score_positioning(data) -> tuple[Optional[float], dict]:
    if not data:
        return None, {"note": "no data"}
    pct_oi = data.get("net_pct_of_open_interest")
    if pct_oi is None:
        return 50.0, data
    # Crowded long = exhausted = higher near-term stress (mean-reverts down).
    raw = 50.0 + float(pct_oi) * 1.5
    return _clip(raw), data


def _score_refinery(data) -> tuple[Optional[float], dict]:
    # Low utilization (negative z) = supply bottleneck = stress.
    if data is None or getattr(data, "empty", True):
        return None, {"note": "no data"}
    last = data.iloc[-1]
    z = last.get("zscore_52w")
    if z is None or (isinstance(z, float) and z != z):
        return None, {"note": "insufficient history"}
    raw = -float(z) * 25.0 + 50.0
    return _clip(raw), {
        "latest_value": float(last["value"]),
        "zscore_52w": round(float(z), 2),
    }


SCORERS = {
    "inventory": _score_inventory,
    "curve_shape": _score_curve,
    "geopolitical": _score_geopolitical,
    "positioning": _score_positioning,
    "refinery_utilization": _score_refinery,
}


def score_signal(signal_name: str, signal_cfg: dict, raw_data: Any) -> dict:
    scorer = SCORERS.get(signal_name)
    if not scorer:
        return {"score": None, "context": {"note": f"no scorer for {signal_name}"}}
    if signal_name == "inventory":
        score, ctx = scorer(raw_data, signal_cfg.get("direction", "contrarian"))
    else:
        score, ctx = scorer(raw_data)
    return {"score": score, "context": ctx}


def compose(signals: dict, weights: dict) -> dict:
    """Weighted average over signals that produced a valid sub-score."""
    num = 0.0
    den = 0.0
    breakdown = {}
    for name, result in signals.items():
        sub = result.get("score")
        w = float(weights.get(name, 0.0))
        breakdown[name] = {
            "score": round(sub, 1) if sub is not None else None,
            "weight": w,
            "context": result.get("context"),
        }
        if sub is None or w <= 0:
            continue
        num += sub * w
        den += w

    if den == 0:
        return {"stress_score": None, "band": "unknown", "breakdown": breakdown, "signals_used": 0}

    composite = round(num / den, 1)
    return {
        "stress_score": composite,
        "band": _band(composite),
        "breakdown": breakdown,
        "signals_used": sum(1 for b in breakdown.values() if b["score"] is not None),
    }
