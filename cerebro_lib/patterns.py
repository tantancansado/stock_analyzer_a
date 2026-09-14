"""Pure helpers for pattern-mining over portfolio_tracker history.

Extracted from cerebro.py mine_patterns() so each slice of the data
(tiers, sectors, regimes) can be tested without the full orchestration.
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd

from horizontes import PRINCIPAL, SECUNDARIO


def compute_stats(
    sub: pd.DataFrame,
    label: str,
    base_wr: float,
    base_ret: float,
    *,
    min_n: int = 3,
    horizonte: str = PRINCIPAL,
    horizonte_2: str = SECUNDARIO,
) -> dict | None:
    """Summary stats for a slice of the portfolio_tracker history.

    Returns None if sub has fewer than `min_n` rows.

    El horizonte era 7 días, fijo. A ese plazo el sistema no tiene ventaja
    —29% de aciertos sobre 1692 señales— porque a una semana de una tesis
    VALUE todavía no ha pasado nada, así que los "patrones" que salían de
    aquí describían ruido y alimentaban las recomendaciones de Cerebro.
    Ver horizontes.py.
    """
    if len(sub) < min_n:
        return None

    col_win, col_ret = f"win_{horizonte}", f"return_{horizonte}"
    wr = float(sub[col_win].mean()) * 100 if col_win in sub.columns else 0.0
    ret = float(sub[col_ret].mean()) if col_ret in sub.columns else 0.0

    ret_2: float | None = None
    col_ret_2 = f"return_{horizonte_2}"
    if col_ret_2 in sub.columns and sub[col_ret_2].notna().any():
        ret_2 = float(sub[col_ret_2].mean())

    return dict(
        label=label,
        horizonte=horizonte,
        win_rate=round(wr, 1),
        avg_return=round(ret, 2),
        avg_return_2=round(ret_2, 2) if ret_2 else None,
        n=len(sub),
        vs_baseline_wr=round(wr - base_wr, 1),
        vs_baseline_ret=round(ret - base_ret, 2),
    )


def tier_column(
    df: pd.DataFrame,
    col: str,
    ranges: Iterable[tuple[float, float]],
    base_wr: float,
    base_ret: float,
) -> list[dict]:
    """Bucket rows of `df` by `col` into half-open [lo, hi) ranges and
    return compute_stats for each non-empty bucket."""
    out: list[dict] = []
    for lo, hi in ranges:
        sub = df[(df[col] >= lo) & (df[col] < hi)]
        s = compute_stats(sub, f"{lo}–{hi}", base_wr, base_ret)
        if s:
            out.append(s)
    return out
