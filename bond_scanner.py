#!/usr/bin/env python3
"""
Bond Scanner — ETF bonds + corporate bonds via yfinance proxy tickers.

Outputs docs/bonds_opportunities.csv with yield, duration, price vs 52w, VALUE rating.

Universe:
  ETFs: SHY, IEF, TLT, BND, VCIT, LQD, TIPS, HYG, AGG, SCHD (screened)
  EUR ETFs: IBTS.MI, IEAG.MI, IEMB.MI
  Corp proxies (closest liquid bond ETF per issuer bucket):
    - MSFT, AAPL, GOOGL, AMZN → VCIT (IG Tech)
    - JPM, BAC, WFC → VCIT (IG Financials, use LQD for longer)
  Individual bond tickers accessible on Yahoo: e.g. "MSFT4.5" style tickers
  don't reliably work — we use the ETF universe + yfinance .info overrides.
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

DOCS = Path("docs")
OUTPUT = DOCS / "bonds_opportunities.csv"

# ─── Universe ────────────────────────────────────────────────────────────────
# Each entry: ticker, display_name, bond_type, avg_duration_years, currency
UNIVERSE = [
    # ── US Treasury ETFs ──────────────────────────────────────────────────────
    ("SHY",     "iShares 1-3yr Treasury",        "Treasury",   2.0,  "USD"),
    ("IEF",     "iShares 7-10yr Treasury",        "Treasury",   8.5,  "USD"),
    ("TLT",     "iShares 20+yr Treasury",         "Treasury",  17.0,  "USD"),
    ("TIPS",    "iShares TIPS Bond",              "TIPS",       7.5,  "USD"),
    # ── US Aggregate / IG Corp ────────────────────────────────────────────────
    ("AGG",     "iShares Core US Aggregate",      "Aggregate",  6.2,  "USD"),
    ("BND",     "Vanguard Total Bond Market",     "Aggregate",  6.5,  "USD"),
    ("VCIT",    "Vanguard Intermediate IG Corp",  "IG_Corp",    5.8,  "USD"),
    ("LQD",     "iShares IG Corporate Bond",      "IG_Corp",    9.0,  "USD"),
    ("VCSH",    "Vanguard Short-Term IG Corp",    "IG_Corp",    2.8,  "USD"),
    # ── High Yield ────────────────────────────────────────────────────────────
    ("HYG",     "iShares HY Corporate Bond",      "HY_Corp",    4.0,  "USD"),
    ("JNK",     "SPDR Bloomberg HY Bond",         "HY_Corp",    3.8,  "USD"),
    # ── EUR Govt & IG ────────────────────────────────────────────────────────
    ("IBTS.MI", "iShares EUR Govt 1-3yr",         "EUR_Govt",   1.9,  "EUR"),
    ("IEAG.MI", "iShares EUR IG Corporate",       "EUR_IG",     5.0,  "EUR"),
    ("IEMB.MI", "iShares EUR Emerging Mkts Bond", "EM_Bond",    6.5,  "EUR"),
    # ── EM Dollar ────────────────────────────────────────────────────────────
    ("EMB",     "iShares USD Emerging Mkts Bond", "EM_Bond",    7.2,  "USD"),
]

# Historical average yields for VALUE comparison (approximate long-term averages)
HIST_AVG_YIELD = {
    "SHY":     3.5,
    "IEF":     3.8,
    "TLT":     3.8,
    "TIPS":    1.5,   # real yield
    "AGG":     3.6,
    "BND":     3.6,
    "VCIT":    4.5,
    "LQD":     4.8,
    "VCSH":    4.0,
    "HYG":     7.0,
    "JNK":     7.2,
    "IBTS.MI": 2.5,
    "IEAG.MI": 3.0,
    "IEMB.MI": 5.5,
    "EMB":     6.5,
}

# Max drawdown thresholds to flag price dislocation (% below 52w high)
DISLOCATION_THRESHOLD = -8.0   # below this → potentially attractive
OVERVALUED_THRESHOLD  = -1.0   # above this (near high) → expensive


def _safe(val, default=None):
    if val is None:
        return default
    try:
        if isinstance(val, float) and math.isnan(val):
            return default
    except Exception:
        pass
    return val


def _fetch_bond_data(ticker: str, duration_hint: float, currency: str) -> dict | None:
    """Fetch ETF data from yfinance and compute bond metrics."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        price = _safe(info.get("regularMarketPrice") or info.get("navPrice"))
        if price is None or price <= 0:
            # fallback via fast_info
            fi = getattr(t, "fast_info", None)
            if fi:
                price = _safe(getattr(fi, "last_price", None))

        if price is None or price <= 0:
            print(f"  [SKIP] {ticker}: no price")
            return None

        week52_high = _safe(info.get("fiftyTwoWeekHigh"))
        week52_low  = _safe(info.get("fiftyTwoWeekLow"))
        pct_from_high = round((price / week52_high - 1) * 100, 2) if week52_high else None

        # Yield — ETFs expose yield directly or as trailingAnnualDividendYield
        # yfinance returns some ETF yields as decimal (0.045 = 4.5%)
        raw_yield = (
            _safe(info.get("yield"))
            or _safe(info.get("trailingAnnualDividendYield"))
            or _safe(info.get("dividendYield"))
        )
        # Normalize: if < 0.20 → decimal form → multiply by 100
        if raw_yield is not None and raw_yield < 0.20:
            yield_pct = round(raw_yield * 100, 2)
        elif raw_yield is not None:
            yield_pct = round(raw_yield, 2)
        else:
            yield_pct = None

        # Duration: ETFs don't expose duration in yfinance.
        # We use our curated hint + a price-movement proxy if we have enough data.
        duration_years = duration_hint

        # Modified duration ≈ duration (approximate for ETFs)
        modified_duration = duration_years

        # 30-day SEC yield if available (more accurate)
        sec_yield = _safe(info.get("secYield"))
        if sec_yield is not None and sec_yield < 0.20:
            sec_yield = round(sec_yield * 100, 2)
        elif sec_yield is not None:
            sec_yield = round(sec_yield, 2)

        effective_yield = sec_yield if sec_yield else yield_pct

        # Credit quality from name/type context
        expense_ratio = _safe(info.get("annualReportExpenseRatio"))
        if expense_ratio and expense_ratio < 0.005:
            expense_ratio = round(expense_ratio * 100, 3)  # convert to %
        elif expense_ratio:
            expense_ratio = round(expense_ratio, 3)

        short_name = _safe(info.get("shortName") or info.get("longName"), ticker)

        return {
            "price": price,
            "week52_high": week52_high,
            "week52_low": week52_low,
            "pct_from_high": pct_from_high,
            "yield_pct": effective_yield,
            "sec_yield_pct": sec_yield,
            "duration_years": duration_years,
            "modified_duration": modified_duration,
            "expense_ratio_pct": expense_ratio,
            "short_name": short_name,
            "currency": currency,
        }

    except Exception as e:
        print(f"  [ERROR] {ticker}: {e}")
        return None


def _value_rating(ticker: str, bond_type: str, yield_pct: float | None, pct_from_high: float | None) -> str:
    """Simple VALUE rating based on yield vs historical average + price dislocation."""
    if yield_pct is None:
        return "SIN_DATO"

    hist = HIST_AVG_YIELD.get(ticker)

    # Score components
    score = 0

    # 1. Yield vs historical average
    if hist:
        spread = yield_pct - hist
        if spread >= 0.5:
            score += 2    # yield above average = attractive
        elif spread >= 0:
            score += 1    # at average = fair
        elif spread <= -0.5:
            score -= 2    # yield below average = expensive
        else:
            score -= 1

    # 2. Price dislocation
    if pct_from_high is not None:
        if pct_from_high <= DISLOCATION_THRESHOLD:
            score += 2    # significant drop = price opportunity
        elif pct_from_high >= OVERVALUED_THRESHOLD:
            score -= 1    # near 52w high = priced in

    # 3. HY penalty when markets are complacent (spreads compressed)
    if bond_type in ("HY_Corp",) and yield_pct < 6.5:
        score -= 1    # HY spread compressed

    if score >= 3:
        return "MUY_ATRACTIVO"
    elif score >= 1:
        return "ATRACTIVO"
    elif score == 0:
        return "NEUTRAL"
    else:
        return "CARO"


def _recommendation(bond_type: str, value_rating: str, duration_years: float) -> str:
    if value_rating in ("MUY_ATRACTIVO", "ATRACTIVO"):
        if bond_type == "Treasury" and duration_years >= 10:
            return "Bloquear yield alto con duración larga mientras dure"
        if bond_type == "IG_Corp":
            return "IG corporativo con spread atractivo, bajo riesgo crédito"
        if bond_type == "HY_Corp":
            return "Alto rendimiento — solo posición pequeña, riesgo crédito"
        if bond_type == "TIPS":
            return "Protección inflación a buen precio"
        if bond_type in ("EUR_Govt", "EUR_IG"):
            return "Bono europeo atractivo, diversifica fuera USD"
        if bond_type == "EM_Bond":
            return "Emergentes con prima de riesgo atractiva"
        return "Atractivo para asignación de renta fija"
    if value_rating == "NEUTRAL":
        return "Precio justo — mantener si ya en cartera"
    return "Caro vs histórico — esperar corrección"


def scan() -> pd.DataFrame:
    rows = []
    for ticker, name, bond_type, duration, currency in UNIVERSE:
        print(f"Fetching {ticker}...")
        data = _fetch_bond_data(ticker, duration, currency)
        time.sleep(0.4)   # gentle rate limiting

        if data is None:
            continue

        y = data["yield_pct"]
        pfh = data["pct_from_high"]
        rating = _value_rating(ticker, bond_type, y, pfh)
        rec = _recommendation(bond_type, rating, duration)

        hist_avg = HIST_AVG_YIELD.get(ticker)
        yield_vs_avg = round(y - hist_avg, 2) if (y is not None and hist_avg) else None

        rows.append({
            "ticker":            ticker,
            "name":              name,
            "short_name":        data["short_name"],
            "bond_type":         bond_type,
            "currency":          currency,
            "price":             data["price"],
            "week52_high":       data["week52_high"],
            "week52_low":        data["week52_low"],
            "pct_from_high":     pfh,
            "yield_pct":         y,
            "sec_yield_pct":     data["sec_yield_pct"],
            "hist_avg_yield_pct": hist_avg,
            "yield_vs_avg_pct":  yield_vs_avg,
            "duration_years":    data["duration_years"],
            "modified_duration": data["modified_duration"],
            "expense_ratio_pct": data["expense_ratio_pct"],
            "value_rating":      rating,
            "recommendation":    rec,
            "generated_at":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    return pd.DataFrame(rows)


def main():
    print("=== Bond Scanner ===")
    DOCS.mkdir(exist_ok=True)
    df = scan()

    if df.empty:
        print("No bond data retrieved — aborting")
        return

    # Sort: most attractive first, then by yield desc
    rating_order = {"MUY_ATRACTIVO": 0, "ATRACTIVO": 1, "NEUTRAL": 2, "CARO": 3, "SIN_DATO": 4}
    df["_sort"] = df["value_rating"].map(rating_order).fillna(4)
    df = df.sort_values(["_sort", "yield_pct"], ascending=[True, False]).drop(columns=["_sort"])

    df.to_csv(OUTPUT, index=False)
    print(f"\n=== Done: {len(df)} bonds written to {OUTPUT} ===")

    atractivo = df[df["value_rating"].isin(["MUY_ATRACTIVO", "ATRACTIVO"])]
    if not atractivo.empty:
        print("\nATRACTIVOS:")
        for _, r in atractivo.iterrows():
            yield_str = f"{r['yield_pct']:.2f}%" if r["yield_pct"] else "N/A"
            print(f"  {r['ticker']:12s} {r['value_rating']:15s} yield={yield_str}  dur={r['duration_years']}y  {r['recommendation'][:60]}")


if __name__ == "__main__":
    main()
