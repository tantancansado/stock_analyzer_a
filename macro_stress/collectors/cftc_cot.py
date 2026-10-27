"""CFTC Commitments of Traders collector with historical net positioning."""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

# API pública de la CFTC (Legacy, solo futuros). El fichero de antes
# (dea/newcot/deacot.txt) devolvía 404 desde octubre-2026 y, cuando existía,
# traía solo la última semana y sin cabecera: el percentil a 3 años no se
# podía calcular nunca.
COT_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

# Código de contrato y no nombre: buscar "GOLD" mezclaba el oro de COMEX con el
# micro-oro y el PAX Gold de Coinbase en la misma serie.
CONTRACT_CODES = {
    "crude_oil_wti": "067651",  # WTI-PHYSICAL - NYMEX
    "natgas": "023651",         # NAT GAS NYME - NYMEX
    "gold": "088691",           # GOLD - COMEX
    "copper": "085692",         # COPPER- #1 - COMEX
}

SEMANAS = 156


def _parse_cot(code: str) -> Optional[pd.DataFrame]:
    params = {
        "cftc_contract_market_code": code,
        "$select": ("report_date_as_yyyy_mm_dd,noncomm_positions_long_all,"
                    "noncomm_positions_short_all,open_interest_all"),
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": SEMANAS + 52,
    }
    try:
        resp = requests.get(COT_URL, params=params, timeout=30)
        resp.raise_for_status()
        return pd.DataFrame(resp.json())
    except Exception as e:
        log.warning("CFTC fetch/parse failed: %s", e)
        return None


def fetch(contract: str) -> Optional[dict]:
    code = CONTRACT_CODES.get(contract)
    if not code:
        log.warning("Unknown COT contract alias: %s", contract)
        return None

    df = _parse_cot(code)
    if df is None or df.empty:
        return None

    sub = pd.DataFrame({
        "date": pd.to_datetime(df.get("report_date_as_yyyy_mm_dd"), errors="coerce"),
        "long": pd.to_numeric(df.get("noncomm_positions_long_all"), errors="coerce"),
        "short": pd.to_numeric(df.get("noncomm_positions_short_all"), errors="coerce"),
        "open_interest": pd.to_numeric(df.get("open_interest_all"), errors="coerce"),
    })
    sub = sub.dropna(subset=["date", "long", "short"]).sort_values("date")
    if sub.empty:
        log.warning("COT: no rows for contract=%s", contract)
        return None

    sub["net"] = sub["long"] - sub["short"]
    sub["net_pct_oi"] = (sub["net"] / sub["open_interest"]) * 100.0

    hist = sub.set_index("date")["net_pct_oi"].dropna()
    latest = sub.iloc[-1]

    percentile = None
    zscore = None
    if not hist.empty:
        tail = hist.tail(min(len(hist), SEMANAS))
        percentile = float((tail <= hist.iloc[-1]).mean() * 100.0)
        std = tail.std()
        if std and std == std:
          zscore = float((hist.iloc[-1] - tail.mean()) / std)

    return {
        "contract": contract,
        "non_commercial_long": int(latest["long"]),
        "non_commercial_short": int(latest["short"]),
        "non_commercial_net": int(latest["net"]),
        "open_interest": int(latest["open_interest"]) if pd.notna(latest["open_interest"]) else None,
        "net_pct_of_open_interest": round(float(latest["net_pct_oi"]), 2) if pd.notna(latest["net_pct_oi"]) else None,
        "percentile_3y": round(percentile, 1) if percentile is not None else None,
        "zscore_3y": round(zscore, 2) if zscore is not None else None,
        "history": hist,
    }
