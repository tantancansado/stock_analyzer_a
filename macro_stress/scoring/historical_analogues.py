"""KNN lookup of historically similar stress regimes.

STUB for MVP: returns empty list until we accumulate 5+ years of signal history.

TODO bootstrap: persist each orchestrator run to `docs/macro_stress/history/<date>.json`,
then load last N dates into a (dates, signals) matrix, standardize, run
`sklearn.neighbors.NearestNeighbors(n_neighbors=5)` on today's vector, and join
forward returns of `primary_ticker` (1w/4w/12w) via yfinance.
"""
from __future__ import annotations

from typing import Optional


def find_analogues(
    signal_vector: dict[str, float],
    primary_ticker: str,
    k: int = 5,
    history_dir: Optional[str] = None,
) -> dict:
    return {
        "analogues": [],
        "note": (
            "Historical analogues not yet built — requires 5+ years of signal "
            "history. Bootstrap by persisting daily runs to "
            "docs/macro_stress/history/ and replaying once N>=260 weeks."
        ),
        "k_requested": k,
    }
