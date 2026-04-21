"""EIA weekly inventory / utilization series via free v2 API.

Requires env var EIA_API_KEY (free signup at https://www.eia.gov/opendata/).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

EIA_BASE = "https://api.eia.gov/v2/seriesid"


def fetch(series_id: str, weeks: int = 260) -> Optional[pd.DataFrame]:
    """Return weekly series with `[date, value, pct_change_vs_5y_avg, zscore_52w]`.

    Returns None (never fake data) if the key is missing or the request fails.
    """
    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        log.warning("EIA_API_KEY not set; skipping %s", series_id)
        return None

    url = f"{EIA_BASE}/{series_id}"
    params = {"api_key": api_key, "length": weeks}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        log.warning("EIA fetch failed for %s: %s", series_id, e)
        return None

    rows = (payload.get("response") or {}).get("data") or []
    if not rows:
        log.warning("EIA returned empty data for %s", series_id)
        return None

    df = pd.DataFrame(rows)
    date_col = "period" if "period" in df.columns else "date"
    value_col = "value" if "value" in df.columns else df.columns[-1]
    df = df[[date_col, value_col]].rename(columns={date_col: "date", value_col: "value"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date").reset_index(drop=True)

    if df.empty:
        return None

    # 5-year (260w) rolling average for % deviation; 52w z-score for anomaly
    roll_5y = df["value"].rolling(260, min_periods=52).mean()
    df["pct_change_vs_5y_avg"] = (df["value"] - roll_5y) / roll_5y * 100.0

    roll_52 = df["value"].rolling(52, min_periods=12)
    mean_52 = roll_52.mean()
    std_52 = roll_52.std()
    df["zscore_52w"] = (df["value"] - mean_52) / std_52

    return df
