"""Pure I/O + coercion helpers used across cerebro modules.

All functions swallow I/O errors and return empty defaults — upstream code
relies on being able to probe for optional artifacts without try/except.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def load_json(path: Path) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def sf(v: Any) -> float | None:
    """Safe-float: coerce to float, return None for NaN / non-numeric / None."""
    try:
        x = float(v)
        return None if (x != x) else x  # NaN check
    except Exception:
        return None


def parse_health_details(row) -> dict:
    """Extract health_details dict from a DataFrame row.

    Accepts either a dict (already parsed) or a string. The CSV pipeline writes
    this column via Python's str(dict) — single-quoted repr, NOT JSON — so
    json.loads() alone fails on every real row (it requires double quotes).
    Try JSON first (in case the format ever changes), fall back to
    ast.literal_eval for the actual single-quoted format. Returns {} on any
    parse failure or non-dict payload.
    """
    raw = row.get("health_details")
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        d = json.loads(raw)
        return d if isinstance(d, dict) else {}
    except Exception:
        pass
    try:
        import ast
        d = ast.literal_eval(raw)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}
