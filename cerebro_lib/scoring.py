"""Pure scoring functions used by cerebro scan modules.

These functions deliberately have no I/O, no Groq calls, no side effects —
so they are cheap to unit-test and swap implementations later.
"""
from __future__ import annotations

from typing import Iterable


def score_smart_money(
    *,
    n_hedge_funds: int,
    n_insiders: int,
    value_score: float | None,
) -> int:
    """Convergence score for smart-money signals. Pure.

    15 pts/fund + 10 pts/insider + 0.3 × value_score, capped at 100.
    Preserves current cerebro.py behavior exactly.
    """
    return round(min(100, n_hedge_funds * 15 + n_insiders * 10 + (value_score or 0) * 0.3))


def score_insider_cluster(*, ticker_count: int, total_purchases: int) -> int:
    """Cluster score = 20 pts/ticker + 2 pts/purchase, capped at 100."""
    return min(100, ticker_count * 20 + total_purchases * 2)


def score_dividend_safety(
    *,
    dividend_yield_pct: float,
    payout_ratio_pct: float | None,
    fcf_yield_pct: float | None,
    interest_coverage: float | None,
) -> tuple[int, str, list[str]]:
    """Return (safety_score, rating, risk_flags).

    Start at 100 (safe), subtract for each risk:
      payout >90%  → -40  "insostenible"
      payout >75%  → -20  "zona de riesgo"
      payout <50%  → +10  (bonus)
      FCF < 0      → -35  "FCF negativo"
      FCF < yield  → -15  "cobertura ajustada"
      int_cov < 2x → -15  "deuda consume caja"

    Rating: AT_RISK < 40, WATCH < 65, else SAFE.
    """
    risk_flags: list[str] = []
    score = 100

    if payout_ratio_pct is not None:
        if payout_ratio_pct > 90:
            risk_flags.append(f"Payout {payout_ratio_pct:.0f}% — insostenible")
            score -= 40
        elif payout_ratio_pct > 75:
            risk_flags.append(f"Payout {payout_ratio_pct:.0f}% — zona de riesgo")
            score -= 20
        elif payout_ratio_pct < 50:
            score += 10

    if fcf_yield_pct is not None:
        if fcf_yield_pct < 0:
            risk_flags.append("FCF negativo — dividendo no cubierto por caja")
            score -= 35
        elif fcf_yield_pct < dividend_yield_pct:
            risk_flags.append(
                f"FCF ({fcf_yield_pct:.1f}%) < dividendo ({dividend_yield_pct:.1f}%) — cobertura ajustada"
            )
            score -= 15

    if interest_coverage is not None and interest_coverage < 2:
        risk_flags.append(f"Interest coverage {interest_coverage:.1f}x — deuda consume caja")
        score -= 15

    score = max(0, min(100, score))
    rating = "AT_RISK" if score < 40 else "WATCH" if score < 65 else "SAFE"
    return score, rating, risk_flags


def classify_piotroski_trend(
    current: float,
    previous: float | None,
) -> tuple[str, float]:
    """Classify Piotroski score trend vs previous snapshot.

    Returns (trend_label, delta). If no previous snapshot, trend is STABLE.
    Thresholds: delta >=2 IMPROVING, >=1 SLIGHT_UP, <=-2 DETERIORATING,
    <=-1 SLIGHT_DOWN, else STABLE.
    """
    if previous is None:
        return "STABLE", 0.0
    delta = current - previous
    if delta >= 2:
        return "IMPROVING", delta
    if delta >= 1:
        return "SLIGHT_UP", delta
    if delta <= -2:
        return "DETERIORATING", delta
    if delta <= -1:
        return "SLIGHT_DOWN", delta
    return "STABLE", delta


def classify_piotroski_signal(current: float) -> str:
    """STRONG if >=7, WEAK if <=3, else NEUTRAL."""
    if current >= 7:
        return "STRONG"
    if current <= 3:
        return "WEAK"
    return "NEUTRAL"


def score_value_trap(
    *,
    piotroski: float | None,
    fcf_yield_pct: float | None,
    fundamental_score: float | None,
    analyst_count: float | None,
    analyst_recommendation: str,
    value_score: float,
    debt_to_equity: float | None,
    operating_margin_pct: float | None,
) -> tuple[int, list[str]]:
    """Return (trap_score, flags) for a VALUE ticker. Pure — no I/O.

    Rules (preserved from cerebro.py scan_value_traps):
      - Piotroski ≤ 2  → +4 (muy débil)
      - Piotroski ≤ 4  → +2 (débil)
      - FCF negative   → +3 (quema caja)
      - fundamental_score ∈ [48, 53]  → +2 (cerca de default)
      - analyst_count < 2 AND value_score > 65  → +2 (sin cobertura)
      - analyst_recommendation ∈ {hold, sell} AND value_score > 65  → +2
      - debt_to_equity > 2.0 AND operating_margin_pct < 5  → +2
    """
    score = 0
    flags: list[str] = []

    if piotroski is not None:
        if piotroski <= 2:
            score += 4
            flags.append(
                f"Piotroski muy débil ({piotroski:.0f}/9) — calidad financiera en deterioro"
            )
        elif piotroski <= 4:
            score += 2
            flags.append(f"Piotroski débil ({piotroski:.0f}/9)")

    if fcf_yield_pct is not None and fcf_yield_pct < 0:
        score += 3
        flags.append(
            f"FCF negativo ({fcf_yield_pct:.1f}%) — quema caja pese a valuación barata"
        )

    if fundamental_score is not None and 48 <= fundamental_score <= 53:
        score += 2
        flags.append("Fundamental score cerca de default (50) — datos poco fiables")

    if (analyst_count is None or analyst_count < 2) and value_score > 65:
        score += 2
        flags.append("Sin cobertura de analistas — tesis sin verificar externamente")

    rec = (analyst_recommendation or "").lower()
    if rec in ("hold", "sell") and value_score > 65:
        score += 2
        flags.append(f"Analistas recomiendan '{rec}' pese a score alto")

    if debt_to_equity is not None and operating_margin_pct is not None:
        if debt_to_equity > 2.0 and operating_margin_pct < 5:
            score += 2
            flags.append(
                f"Deuda alta ({debt_to_equity:.1f}x) + margen operativo bajo ({operating_margin_pct:.1f}%)"
            )

    return score, flags


def compute_convergence_score(
    strategies: Iterable[str],
    value_score: float | None,
    streak_days: int,
) -> int:
    """Score a ticker that appears in multiple strategy lists today.

    - 20 pts per strategy (capped implicitly by later min(100,·))
    - VALUE bonus: value_score/5, capped at 20
    - INSIDERS bonus: flat +10
    - Streak bonus: +10 if in convergence ≥3 consecutive days (persistence)

    Returns int in [0, 100]. Preserves current cerebro.py behavior exactly.
    """
    strats = list(strategies)
    score = len(strats) * 20
    if "VALUE" in strats and value_score:
        score += min(20, (value_score or 0) / 5)
    if "INSIDERS" in strats:
        score += 10
    if streak_days >= 3:
        score += 10
    return min(100, int(score))
