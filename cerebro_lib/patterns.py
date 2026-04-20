"""Pure helpers for pattern-mining over portfolio_tracker history.

Extracted from cerebro.py mine_patterns() so each slice of the data
(tiers, sectors, regimes) can be tested without the full orchestration.
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd


def compute_stats(
    sub: pd.DataFrame,
    label: str,
    base_wr: float,
    base_ret: float,
    *,
    min_n: int = 3,
) -> dict | None:
    """Summary stats for a slice of the portfolio_tracker history.

    Returns None if sub has fewer than `min_n` rows.  Expects columns
    `win_7d` / `return_7d` / (optional) `return_14d`.  Preserves the
    exact shape produced by cerebro.py's mine_patterns.stats closure.
    """
    if len(sub) < min_n:
        return None

    wr = float(sub["win_7d"].mean()) * 100 if "win_7d" in sub.columns else 0.0
    ret = float(sub["return_7d"].mean())

    ret14: float | None = None
    if "return_14d" in sub.columns and sub["return_14d"].notna().any():
        ret14 = float(sub["return_14d"].mean())

    return dict(
        label=label,
        win_rate_7d=round(wr, 1),
        avg_return_7d=round(ret, 2),
        avg_return_14d=round(ret14, 2) if ret14 else None,
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
