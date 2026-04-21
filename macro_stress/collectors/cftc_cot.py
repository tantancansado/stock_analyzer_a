"""CFTC Commitments of Traders (COT) collector — public CSV, fragile parser."""
from __future__ import annotations

import io
import logging
from typing import Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

COT_URL = "https://www.cftc.gov/dea/newcot/deacot.txt"

# Keyword matching on the "Market_and_Exchange_Names" field. Keep loose.
CONTRACT_ALIASES = {
    "crude_oil_wti": ["CRUDE OIL, LIGHT SWEET-NYMEX", "WTI-PHYSICAL", "CRUDE OIL, LIGHT SWEET"],
    "natgas": ["NAT GAS NYME", "NATURAL GAS - NYMEX"],
    "gold": ["GOLD - COMMODITY EXCHANGE"],
    "copper": ["COPPER-GRADE #1"],
}


def _parse_cot() -> Optional[pd.DataFrame]:
    try:
        resp = requests.get(COT_URL, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        log.warning("CFTC fetch failed: %s", e)
        return None

    try:
        df = pd.read_csv(io.StringIO(resp.text), engine="python", on_bad_lines="skip")
    except Exception as e:
        log.warning("CFTC parse failed: %s", e)
        return None
    return df


def fetch(contract: str) -> Optional[dict]:
    """Return positioning snapshot for one contract, or None on any failure."""
    aliases = CONTRACT_ALIASES.get(contract)
    if not aliases:
        log.warning("Unknown COT contract alias: %s", contract)
        return None

    df = _parse_cot()
    if df is None or df.empty:
        return None

    name_col = next((c for c in df.columns if "Market" in c and "Name" in c), None)
    if not name_col:
        log.warning("COT: no market-name column found")
        return None

    mask = df[name_col].astype(str).str.upper().apply(
        lambda s: any(a.upper() in s for a in aliases)
    )
    sub = df[mask]
    if sub.empty:
        log.warning("COT: no rows for contract=%s", contract)
        return None

    row = sub.iloc[0]

    def _num(col_contains: list[str]) -> Optional[float]:
        for col in df.columns:
            if all(tok in col for tok in col_contains):
                try:
                    return float(row[col])
                except (TypeError, ValueError):
                    return None
        return None

    nc_long = _num(["NonComm", "Positions", "Long"]) or _num(["Noncommercial", "Long"])
    nc_short = _num(["NonComm", "Positions", "Short"]) or _num(["Noncommercial", "Short"])
    oi = _num(["Open", "Interest"])

    if nc_long is None or nc_short is None:
        log.warning("COT: could not locate non-commercial position columns")
        return None

    net = int(nc_long - nc_short)
    pct_oi = round((net / oi) * 100.0, 2) if oi else None

    return {
        "contract": contract,
        "non_commercial_long": int(nc_long),
        "non_commercial_short": int(nc_short),
        "non_commercial_net": net,
        "open_interest": int(oi) if oi else None,
        "net_pct_of_open_interest": pct_oi,
        "weekly_change": None,
        "percentile_3y": None,
    }
