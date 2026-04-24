"""
Pure filter/penalty functions extracted from
SuperScoreIntegrator._apply_advanced_filters.

Cada función:
  - Recibe un DataFrame
  - Devuelve un DataFrame nuevo (no muta el input)
  - No hace I/O, no imprime, no llama a yfinance

Los sources externos (MarketRegimeDetector, MovingAverageFilter, etc.)
siguen en super_score_integrator.py — sólo sus OUTPUTS llegan aquí como
parámetros o como columnas del df.
"""
from __future__ import annotations

import pandas as pd


# ── Market regime penalty ─────────────────────────────────────────────────────

MARKET_PENALTY_AVOID    = 15
MARKET_PENALTY_CAUTION  = 5
MARKET_PENALTY_SAFE     = 0


def derive_market_penalty(recommendation: str | None) -> int:
    """
    Mapea la recomendación del MarketRegimeDetector a un penalty fijo.

    AVOID      → 15pts (market en corrección, evitar entrar)
    CAUTION    → 5pts  (market bajo presión, moderar)
    otro/None  → 0pts  (safe to trade)
    """
    if recommendation is None:
        return MARKET_PENALTY_SAFE
    rec = str(recommendation).strip().upper()
    if rec == 'AVOID':
        return MARKET_PENALTY_AVOID
    if rec == 'CAUTION':
        return MARKET_PENALTY_CAUTION
    return MARKET_PENALTY_SAFE


def apply_market_regime_to_df(
    df: pd.DataFrame,
    regime: str,
    recommendation: str,
) -> pd.DataFrame:
    """Añade columnas market_regime + market_recommendation al df."""
    result = df.copy()
    result['market_regime'] = regime
    result['market_recommendation'] = recommendation
    return result


# ── Filter penalty aggregation ────────────────────────────────────────────────
# super_score_integrator.py:528-551

def compute_filter_penalty(df: pd.DataFrame, market_penalty: int) -> pd.DataFrame:
    """
    Calcula filter_penalty sumando:
      - market_penalty (global, constante)
      - MA filter fail: +10
      - A/D signal STRONG_DISTRIBUTION: +15
      - A/D signal DISTRIBUTION: +10
      - A/D score < 50: +5
      - Float category MEGA_FLOAT: +3

    Requires columns: ma_filter_pass, ad_signal, ad_score, float_category.
    Missing columns are tolerated — penalty from missing signal is 0.
    """
    result = df.copy()
    result['filter_penalty'] = float(market_penalty)

    if 'ma_filter_pass' in result.columns:
        # False = fail filter
        failed = (result['ma_filter_pass'] == False)  # noqa: E712
        result.loc[failed, 'filter_penalty'] += 10

    if 'ad_signal' in result.columns:
        result.loc[result['ad_signal'] == 'STRONG_DISTRIBUTION', 'filter_penalty'] += 15
        result.loc[result['ad_signal'] == 'DISTRIBUTION', 'filter_penalty'] += 10

    if 'ad_score' in result.columns:
        result.loc[pd.to_numeric(result['ad_score'], errors='coerce') < 50, 'filter_penalty'] += 5

    if 'float_category' in result.columns:
        result.loc[result['float_category'] == 'MEGA_FLOAT', 'filter_penalty'] += 3

    return result


def apply_filter_penalty(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica filter_penalty a super_score_ultimate con clip a 0 (no scores negativos).

    Guarda super_score_before_filters como copia antes de restar el penalty.
    Requires: filter_penalty, super_score_ultimate.
    """
    result = df.copy()
    if 'super_score_ultimate' not in result.columns:
        return result
    if 'filter_penalty' not in result.columns:
        result['filter_penalty'] = 0.0

    result['super_score_before_filters'] = result['super_score_ultimate'].copy()
    result['super_score_ultimate'] = (
        result['super_score_ultimate'] - result['filter_penalty']
    ).clip(lower=0)
    return result


# ── RS Line bonus ─────────────────────────────────────────────────────────────
# super_score_integrator.py:587-601

def compute_rs_line_bonus(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bonus de 0-10 puntos por fuerza relativa (Minervini's RS Line).

      rs_line_at_new_high == True: +7
      rs_line_percentile >= 75:    +3
      rs_line_trend == 'up':       +2
      Total clipped to max 10.

    Positive-only signal — nunca resta.
    """
    result = df.copy()
    result['rs_line_bonus'] = 0.0

    if 'rs_line_at_new_high' in result.columns:
        result.loc[result['rs_line_at_new_high'] == True, 'rs_line_bonus'] += 7.0  # noqa: E712

    if 'rs_line_percentile' in result.columns:
        pct = pd.to_numeric(result['rs_line_percentile'], errors='coerce')
        result.loc[pct >= 75, 'rs_line_bonus'] += 3.0

    if 'rs_line_trend' in result.columns:
        result.loc[result['rs_line_trend'] == 'up', 'rs_line_bonus'] += 2.0

    result['rs_line_bonus'] = result['rs_line_bonus'].clip(upper=10.0)
    return result


def apply_rs_line_bonus(df: pd.DataFrame) -> pd.DataFrame:
    """
    Suma rs_line_bonus a super_score_ultimate, clip arriba a 100.
    Requires: rs_line_bonus, super_score_ultimate.
    """
    result = df.copy()
    if 'super_score_ultimate' not in result.columns or 'rs_line_bonus' not in result.columns:
        return result
    result['super_score_ultimate'] = (
        result['super_score_ultimate'] + result['rs_line_bonus']
    ).clip(upper=100)
    return result
