"""CFTC Commitments of Traders collector with historical net positioning."""
from __future__ import annotations

import io
import logging
from typing import Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

COT_URL = "https://www.cftc.gov/dea/newcot/deacot.txt"

CONTRACT_ALIASES = {
    "crude_oil_wti": ["CRUDE OIL, LIGHT SWEET", "WTI-PHYSICAL", "CRUDE OIL, LIGHT SWEET-NYMEX"],
    "natgas": ["NATURAL GAS", "NAT GAS NYME"],
    "gold": ["GOLD - COMMODITY EXCHANGE", "GOLD"],
    "copper": ["COPPER-GRADE #1", "COPPER"],
}


def _parse_cot() -> Optional[pd.DataFrame]:
    try:
        resp = requests.get(COT_URL, timeout=20)
        resp.raise_for_status()
        return pd.read_csv(io.StringIO(resp.text), engine="python", on_bad_lines="skip")
    except Exception as e:
        log.warning("CFTC fetch/parse failed: %s", e)
        return None


def _find_col(columns: list[str], tokens: list[str]) -> Optional[str]:
    for col in columns:
        lc = col.lower()
        if all(tok in lc for tok in tokens):
            return col
    return None


def fetch(contract: str) -> Optional[dict]:
    aliases = CONTRACT_ALIASES.get(contract)
    if not aliases:
        log.warning("Unknown COT contract alias: %s", contract)
        return None

    df = _parse_cot()
    if df is None or df.empty:
        return None

    cols = list(df.columns)
    name_col = _find_col(cols, ["market", "exchange", "names"]) or _find_col(cols, ["market", "name"])
    date_col = _find_col(cols, ["as_of_date"]) or _find_col(cols, ["report_date"])
    long_col = (
        _find_col(cols, ["noncomm", "positions", "long"]) or
        _find_col(cols, ["noncommercial", "positions", "long"]) or
        _find_col(cols, ["managed", "money", "long"])
    )
    short_col = (
        _find_col(cols, ["noncomm", "positions", "short"]) or
        _find_col(cols, ["noncommercial", "positions", "short"]) or
        _find_col(cols, ["managed", "money", "short"])
    )
    oi_col = _find_col(cols, ["open", "interest"])

    if not name_col or not date_col or not long_col or not short_col:
        log.warning("COT parser could not find key columns")
        return None

    mask = df[name_col].astype(str).str.upper().apply(lambda s: any(alias.upper() in s for alias in aliases))
    sub = df.loc[mask, [name_col, date_col, long_col, short_col] + ([oi_col] if oi_col else [])].copy()
    if sub.empty:
        log.warning("COT: no rows for contract=%s", contract)
        return None

    sub["date"] = pd.to_datetime(sub[date_col], errors="coerce")
    sub["long"] = pd.to_numeric(sub[long_col], errors="coerce")
    sub["short"] = pd.to_numeric(sub[short_col], errors="coerce")
    sub["open_interest"] = pd.to_numeric(sub[oi_col], errors="coerce") if oi_col else None
    sub = sub.dropna(subset=["date", "long", "short"]).sort_values("date")
    if sub.empty:
        return None

    sub["net"] = sub["long"] - sub["short"]
    if oi_col:
        sub["net_pct_oi"] = (sub["net"] / sub["open_interest"]) * 100.0
    else:
        sub["net_pct_oi"] = None

    hist = sub.set_index("date")["net_pct_oi"].dropna()
    latest = sub.iloc[-1]

    percentile = None
    zscore = None
    if not hist.empty:
        tail = hist.tail(min(len(hist), 156))
        percentile = float((tail <= hist.iloc[-1]).mean() * 100.0)
        std = tail.std()
        if std and std == std:
          zscore = float((hist.iloc[-1] - tail.mean()) / std)

    return {
        "contract": contract,
        "non_commercial_long": int(latest["long"]),
        "non_commercial_short": int(latest["short"]),
        "non_commercial_net": int(latest["net"]),
        "open_interest": int(latest["open_interest"]) if oi_col and pd.notna(latest["open_interest"]) else None,
        "net_pct_of_open_interest": round(float(latest["net_pct_oi"]), 2) if pd.notna(latest["net_pct_oi"]) else None,
        "percentile_3y": round(percentile, 1) if percentile is not None else None,
        "zscore_3y": round(zscore, 2) if zscore is not None else None,
        "history": hist,
    }
