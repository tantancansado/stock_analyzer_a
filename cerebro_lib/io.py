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

    Accepts either a dict (already parsed) or a JSON string. Returns {} on
    any parse failure or non-dict payload.
    """
    raw = row.get("health_details")
    if not raw:
        return {}
    try:
        d = json.loads(raw) if isinstance(raw, str) else raw
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}
