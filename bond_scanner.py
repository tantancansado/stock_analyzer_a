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
OUTPUT           = DOCS / "bonds_opportunities.csv"
OUTPUT_PREFERRED = DOCS / "preferred_stocks.csv"

# ─── Universe ────────────────────────────────────────────────────────────────
# Each entry: ticker, display_name, bond_type, avg_duration_years, currency
UNIVERSE = [
    # ── US T-Bills / Ultracorto (< 1 año) ────────────────────────────────────
    ("BIL",     "SPDR Bloomberg 1-3m T-Bill",     "T_Bill",     0.2,  "USD"),
    ("SHV",     "iShares Short Treasury Bond",    "T_Bill",     0.4,  "USD"),
    ("SGOV",    "iShares 0-3m Treasury Bond",     "T_Bill",     0.2,  "USD"),
    # ── US Treasury 1-2 años ─────────────────────────────────────────────────
    ("SHY",     "iShares 1-3yr Treasury",         "Treasury",   2.0,  "USD"),
    ("VGSH",    "Vanguard Short-Term Treasury",   "Treasury",   2.0,  "USD"),
    # ── US Treasury medio/largo ───────────────────────────────────────────────
    ("IEF",     "iShares 7-10yr Treasury",        "Treasury",   8.5,  "USD"),
    ("TLT",     "iShares 20+yr Treasury",         "Treasury",  17.0,  "USD"),
    ("TIPS",    "iShares TIPS Bond",              "TIPS",       7.5,  "USD"),
    ("STIP",    "iShares 0-5yr TIPS Bond",        "TIPS",       2.5,  "USD"),
    # ── US Aggregate / IG Corp ────────────────────────────────────────────────
    ("AGG",     "iShares Core US Aggregate",      "Aggregate",  6.2,  "USD"),
    ("BND",     "Vanguard Total Bond Market",     "Aggregate",  6.5,  "USD"),
    ("VCSH",    "Vanguard Short-Term IG Corp",    "IG_Corp",    2.8,  "USD"),
    ("VCIT",    "Vanguard Intermediate IG Corp",  "IG_Corp",    5.8,  "USD"),
    ("LQD",     "iShares IG Corporate Bond",      "IG_Corp",    9.0,  "USD"),
    # ── High Yield ────────────────────────────────────────────────────────────
    ("HYG",     "iShares HY Corporate Bond",      "HY_Corp",    4.0,  "USD"),
    ("JNK",     "SPDR Bloomberg HY Bond",         "HY_Corp",    3.8,  "USD"),
    # ── EUR Ultracorto / Govt ─────────────────────────────────────────────────
    ("XEON.DE", "Xtrackers EUR Overnight Rate",   "EUR_Cash",   0.1,  "EUR"),
    ("IBTS.MI", "iShares EUR Govt 1-3yr",         "EUR_Govt",   1.9,  "EUR"),
    ("IEAG.MI", "iShares EUR IG Corporate",       "EUR_IG",     5.0,  "EUR"),
    ("IEMB.MI", "iShares EUR Emerging Mkts Bond", "EM_Bond",    6.5,  "EUR"),
    # ── UK Gilts (GBP) ───────────────────────────────────────────────────────
    ("IGLT.L",  "iShares UK Gilts All Stocks",   "UK_Gilt",    9.5,  "GBP"),
    ("VGOV.L",  "Vanguard UK Govt Bond",         "UK_Gilt",   13.5,  "GBP"),
    ("IGLS.L",  "iShares UK Gilts 0-5yr",        "UK_Gilt",    2.8,  "GBP"),
    # ── EM Dollar ────────────────────────────────────────────────────────────
    ("EMB",     "iShares USD Emerging Mkts Bond", "EM_Bond",    7.2,  "USD"),
]

# Historical average yields for VALUE comparison (approximate long-term averages)
HIST_AVG_YIELD = {
    "BIL":     3.8,
    "SHV":     3.8,
    "SGOV":    3.8,
    "SHY":     3.5,
    "VGSH":    3.5,
    "IEF":     3.8,
    "TLT":     3.8,
    "TIPS":    1.5,   # real yield
    "STIP":    1.2,   # real yield short
    "AGG":     3.6,
    "BND":     3.6,
    "VCSH":    4.0,
    "VCIT":    4.5,
    "LQD":     4.8,
    "HYG":     7.0,
    "JNK":     7.2,
    "XEON.DE": 2.0,
    "IBTS.MI": 2.5,
    "IEAG.MI": 3.0,
    "IEMB.MI": 5.5,
    "EMB":     6.5,
    # UK Gilts — historical avg yield (10y ~4.0%, 30y ~4.5% over past 20 years)
    "IGLT.L":  4.0,   # all-stocks avg ~4%
    "VGOV.L":  4.2,   # longer duration, slightly higher avg
    "IGLS.L":  3.5,   # short gilts, lower avg
}

# Max drawdown thresholds to flag price dislocation (% below 52w high)
DISLOCATION_THRESHOLD = -8.0   # below this → potentially attractive
OVERVALUED_THRESHOLD  = -1.0   # above this (near high) → expensive

# Liquidity thresholds — volumen medio diario (3 meses). ETFs grandes mueven
# millones/día; preferentes individuales decenas-cientos de miles. Por debajo
# de BAJA, una orden de mercado puede mover el precio significativamente.
LIQUIDITY_ALTA_MIN  = 1_000_000
LIQUIDITY_MEDIA_MIN = 100_000


def _liquidity(info: dict) -> dict:
    """Volumen medio (3m) + spread bid/ask desde el mismo .info ya descargado
    (sin llamada extra a yfinance). Rating ALTA/MEDIA/BAJA + nota de ejecución."""
    avg_vol = _safe(info.get("averageVolume") or info.get("averageDailyVolume3Month"))
    bid = _safe(info.get("bid"))
    ask = _safe(info.get("ask"))
    spread_pct = None
    if bid and ask and bid > 0 and ask > 0:
        spread_pct = round((ask - bid) / ((ask + bid) / 2) * 100, 2)

    if avg_vol is None:
        rating = "SIN_DATO"
    elif avg_vol >= LIQUIDITY_ALTA_MIN:
        rating = "ALTA"
    elif avg_vol >= LIQUIDITY_MEDIA_MIN:
        rating = "MEDIA"
    else:
        rating = "BAJA"

    note = {
        "ALTA":  "Entra y sale sin fricción, spread mínimo",
        "MEDIA": "Liquidez aceptable — usa orden límite, no market",
        "BAJA":  "Poco volumen — orden límite obligatoria, no muevas cantidades grandes de golpe",
        "SIN_DATO": "Sin dato de volumen",
    }[rating]

    return {
        "avg_volume_3m": int(avg_vol) if avg_vol is not None else None,
        "spread_pct": spread_pct,
        "liquidity_rating": rating,
        "liquidity_note": note,
    }


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
            **_liquidity(info),
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
        if bond_type == "T_Bill":
            return "Liquidez remunerada ~4-5% sin riesgo de tipos — ideal para capital en espera"
        if bond_type == "EUR_Cash":
            return "Equivalente a cuenta remunerada en EUR, sin riesgo de precio"
        if bond_type == "Treasury" and duration_years <= 3:
            return "Tesoro corto plazo: rendimiento competitivo sin exposición a subida de tipos"
        if bond_type == "Treasury" and duration_years >= 10:
            return "Bloquear yield alto con duración larga mientras dure"
        if bond_type == "IG_Corp" and duration_years <= 3:
            return "Corp IG corto: spread extra sobre Treasury sin riesgo de duración"
        if bond_type == "IG_Corp":
            return "IG corporativo con spread atractivo, bajo riesgo crédito"
        if bond_type == "HY_Corp":
            return "Alto rendimiento — solo posición pequeña, riesgo crédito"
        if bond_type == "TIPS" and duration_years <= 3:
            return "TIPS cortos: protección inflación con mínimo riesgo de tipos"
        if bond_type == "TIPS":
            return "Protección inflación a buen precio"
        if bond_type in ("EUR_Govt", "EUR_IG"):
            return "Bono europeo atractivo, diversifica fuera USD"
        if bond_type == "EM_Bond":
            return "Emergentes con prima de riesgo atractiva"
        if bond_type == "UK_Gilt":
            if duration_years >= 10:
                return "Gilt largo: yield históricamente alto — atractivo si BoE recorta tipos, riesgo divisa GBP"
            return "Gilt corto: yield competitivo con bajo riesgo de duración, riesgo divisa GBP"
        return "Atractivo para asignación de renta fija"
    if value_rating == "NEUTRAL":
        if bond_type == "T_Bill":
            return "Yield aceptable para liquidez pero sin prima especial ahora"
        if bond_type == "UK_Gilt":
            return "Gilt a yield justo — esperar catalizador BoE antes de entrar"
        return "Precio justo — mantener si ya en cartera"
    if bond_type == "UK_Gilt":
        return "Gilt caro vs histórico — yield insuficiente dado riesgo inflación UK"
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
            "avg_volume_3m":     data["avg_volume_3m"],
            "spread_pct":        data["spread_pct"],
            "liquidity_rating":  data["liquidity_rating"],
            "liquidity_note":    data["liquidity_note"],
            "generated_at":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    return pd.DataFrame(rows)


# ─── Preferred Stocks Universe ───────────────────────────────────────────────
# Ticker, display_name, issuer, sector, nominal (par value), fixed_dividend_pct
# fixed_dividend_pct = annual dividend / par value (as stated in prospectus)
# Callable = company can redeem at par — listed for info only
PREFERRED_UNIVERSE = [
    # ── Big US Banks (Too-Big-To-Fail) ───────────────────────────────────────
    ("JPM-PD",  "JPMorgan Chase Pref D",  "JPMorgan Chase",  "Bank",      25.0, 6.10),
    ("JPM-PC",  "JPMorgan Chase Pref C",  "JPMorgan Chase",  "Bank",      25.0, 6.00),
    ("BAC-PM",  "BofA Preferred M",       "Bank of America", "Bank",      25.0, 6.10),
    ("WFC-PY",  "Wells Fargo Pref Y",     "Wells Fargo",     "Bank",      25.0, 5.63),
    ("C-PN",    "Citigroup Preferred N",  "Citigroup",       "Bank",      25.0, 6.30),
    ("GS-PA",   "Goldman Sachs Pref A",   "Goldman Sachs",   "Bank",      25.0, 5.50),
    # ── Insurance / Financial ─────────────────────────────────────────────────
    ("ALL-PB",  "Allstate Preferred B",   "Allstate",        "Insurance", 25.0, 6.625),
    # ── Utilities (reguladas, flujo de caja predecible) ───────────────────────
    ("DUK-PA",  "Duke Energy Pref A",     "Duke Energy",     "Utility",   25.0, 5.75),
    ("AEP-PA",  "AEP Preferred A",        "Am. Elec. Power", "Utility",   25.0, 6.125),
    # ── REITs (inmobiliario) ──────────────────────────────────────────────────
    ("PSA-PH",  "Public Storage Pref H",  "Public Storage",  "REIT",      25.0, 5.60),
    ("PSA-PK",  "Public Storage Pref K",  "Public Storage",  "REIT",      25.0, 5.875),
    ("O-PA",    "Realty Income Pref A",   "Realty Income",   "REIT",      25.0, 6.00),
]

# Risk tier por sector (para la explicación al usuario)
PREFERRED_RISK = {
    "Bank":      "BAJO",      # TBTF — respaldo implícito del estado
    "Insurance": "BAJO-MEDIO",
    "Utility":   "BAJO",      # Reguladas, monopolio regional
    "REIT":      "MEDIO",     # Sensibles a tipos y valoración inmobiliaria
}


def _fetch_preferred(ticker: str, par: float, fixed_div_pct: float) -> dict | None:
    """Fetch preferred stock data and compute current yield vs stated dividend."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        price = _safe(info.get("regularMarketPrice") or info.get("previousClose"))
        if price is None or price <= 0:
            fi = getattr(t, "fast_info", None)
            if fi:
                price = _safe(getattr(fi, "last_price", None))
        if price is None or price <= 0:
            print(f"  [SKIP] {ticker}: no price")
            return None
        # Sanity check: preferreds trade near $25 par — reject obviously wrong data
        if price > par * 5:
            print(f"  [SKIP] {ticker}: price ${price:.2f} implausible for ${par} par preferred")
            return None

        week52_high = _safe(info.get("fiftyTwoWeekHigh"))
        week52_low  = _safe(info.get("fiftyTwoWeekLow"))
        pct_from_par = round((price / par - 1) * 100, 2)
        pct_from_high = round((price / week52_high - 1) * 100, 2) if week52_high else None

        # Current yield = annual dividend / current price
        annual_div = par * fixed_div_pct / 100
        current_yield = round(annual_div / price * 100, 2)

        # Premium/discount to par — affects effective yield and call risk
        # If trading above par → callable risk (company redeems at par, you lose premium)
        # If trading below par → extra yield, price upside if called

        return {
            "price":          price,
            "week52_high":    week52_high,
            "week52_low":     week52_low,
            "pct_from_par":   pct_from_par,
            "pct_from_high":  pct_from_high,
            "annual_div":     round(annual_div, 4),
            "current_yield":  current_yield,
            "stated_div_pct": fixed_div_pct,
            **_liquidity(info),
        }
    except Exception as e:
        print(f"  [ERROR] {ticker}: {e}")
        return None


def _preferred_rating(current_yield: float, pct_from_par: float, sector: str) -> str:
    """VALUE rating for preferreds: yield attractiveness + price vs par."""
    score = 0

    # 1. Yield level — compare to T-Bill (~4.3%) and IG corp (~4.7%)
    if current_yield >= 6.5:
        score += 3
    elif current_yield >= 5.5:
        score += 2
    elif current_yield >= 4.8:
        score += 1
    else:
        score -= 1

    # 2. Price vs par — below par = extra upside if called, above par = call risk
    if pct_from_par <= -5:
        score += 2   # significant discount = price + yield upside
    elif pct_from_par <= -2:
        score += 1
    elif pct_from_par >= 3:
        score -= 1   # trading above par = call risk (company redeems at par)

    # 3. REIT preferreds penalty (more sensitive to rate cycle)
    if sector == "REIT":
        score -= 1

    if score >= 4:
        return "MUY_ATRACTIVO"
    elif score >= 2:
        return "ATRACTIVO"
    elif score >= 0:
        return "NEUTRAL"
    else:
        return "CARO"


def _preferred_recommendation(sector: str, rating: str, pct_from_par: float,
                               current_yield: float) -> str:
    risk = PREFERRED_RISK.get(sector, "MEDIO")
    above = pct_from_par > 1.5

    if rating in ("MUY_ATRACTIVO", "ATRACTIVO"):
        base = f"Yield {current_yield:.1f}% fijo, riesgo {risk}"
        if above:
            return f"{base} — cotiza sobre par, cuidado con llamada anticipada"
        if pct_from_par <= -3:
            return f"{base} — bajo par: yield alto + potencial de precio si la empresa la llama"
        return f"{base} — precio justo, cupón atractivo vs T-Bills"
    if rating == "NEUTRAL":
        return f"Yield {current_yield:.1f}% aceptable, sin prima especial vs alternativas"
    return f"Yield {current_yield:.1f}% — poco atractivo dado el riesgo; mejor un T-Bill o VCSH"


def scan_preferred() -> pd.DataFrame:
    rows = []
    for ticker, name, issuer, sector, par, fixed_div_pct in PREFERRED_UNIVERSE:
        print(f"Fetching preferred {ticker}...")
        data = _fetch_preferred(ticker, par, fixed_div_pct)
        time.sleep(0.4)

        if data is None:
            continue

        rating = _preferred_rating(data["current_yield"], data["pct_from_par"], sector)
        rec = _preferred_recommendation(sector, rating, data["pct_from_par"], data["current_yield"])

        rows.append({
            "ticker":          ticker,
            "name":            name,
            "issuer":          issuer,
            "sector":          sector,
            "par_value":       par,
            "stated_div_pct":  fixed_div_pct,
            "annual_div":      data["annual_div"],
            "price":           data["price"],
            "pct_from_par":    data["pct_from_par"],
            "week52_high":     data["week52_high"],
            "week52_low":      data["week52_low"],
            "pct_from_high":   data["pct_from_high"],
            "current_yield":   data["current_yield"],
            "risk_tier":       PREFERRED_RISK.get(sector, "MEDIO"),
            "value_rating":    rating,
            "recommendation":  rec,
            "avg_volume_3m":   data["avg_volume_3m"],
            "spread_pct":      data["spread_pct"],
            "liquidity_rating": data["liquidity_rating"],
            "liquidity_note":  data["liquidity_note"],
            "currency":        "USD",
            "generated_at":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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

    # ── Preferred stocks ──────────────────────────────────────────────────────
    print("\n=== Preferred Stocks Scanner ===")
    dfp = scan_preferred()

    if dfp.empty:
        print("No preferred data retrieved")
    else:
        rating_order = {"MUY_ATRACTIVO": 0, "ATRACTIVO": 1, "NEUTRAL": 2, "CARO": 3}
        dfp["_sort"] = dfp["value_rating"].map(rating_order).fillna(4)
        dfp = dfp.sort_values(["_sort", "current_yield"], ascending=[True, False]).drop(columns=["_sort"])
        dfp.to_csv(OUTPUT_PREFERRED, index=False)
        print(f"Done: {len(dfp)} preferreds written to {OUTPUT_PREFERRED}")
        for _, r in dfp.iterrows():
            print(f"  {r['ticker']:10s} {r['value_rating']:15s} yield={r['current_yield']:.2f}%  par_dist={r['pct_from_par']:+.1f}%  {r['recommendation'][:55]}")


if __name__ == "__main__":
    main()
