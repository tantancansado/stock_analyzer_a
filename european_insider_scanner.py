#!/usr/bin/env python3
"""
EUROPEAN INSIDER SCANNER
Detecta compras de insiders en tickers europeos via yfinance y BaFin.

Cobertura real por mercado:
- FTSE100 (.L)  : 100% — datos FCA/RNS de alta calidad (via yfinance)
- AEX25  (.AS)  : ~20% — parcial, filtra buybacks corporativos (via yfinance)
- DAX40  (.DE)  : 100% — via BaFin Directors' Dealings portal (scraping)
- CAC40, IBEX35, SMI20, FTSEMIB : sin cobertura

Output: docs/eu_recurring_insiders.csv (mismo schema que recurring_insiders.csv + columna market)
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

try:
    import requests
    from bs4 import BeautifulSoup
    BAFIN_AVAILABLE = True
except ImportError:
    BAFIN_AVAILABLE = False

# ── Setup ──────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING)  # suppress yfinance noise
DOCS = Path("docs")
REPORTS = DOCS / "reports"

DAYS_BACK = 90        # Lookback window for recent purchases
MIN_PURCHASES = 2     # Recurring threshold (≥2 purchases required)
DELAY = 0.4           # Seconds between yfinance calls (rate limit safety)

# BaFin Directors' Dealings portal
BAFIN_URL   = "https://portal.mvp.bafin.de/database/DealingsInfo/sucheForm.do"
BAFIN_DELAY = 1.5     # Seconds between BaFin requests (be respectful)

# Market suffix → market name mapping
SUFFIX_TO_MARKET = {
    ".L":  "FTSE100",
    ".AS": "AEX25",
    ".DE": "DAX40",
    ".PA": "CAC40",
    ".MC": "IBEX35",
    ".SW": "SMI20",
    ".MI": "FTSEMIB",
}

# DAX40 ticker → (ISIN, company name) for BaFin search.
# ISINs are stable identifiers — update only if a company leaves/joins DAX40.
DAX40_ISIN_MAP: dict[str, tuple[str, str]] = {
    "ADS.DE":   ("DE000A1EWWW0", "Adidas"),
    "AIR.DE":   ("NL0000235190", "Airbus"),
    "ALV.DE":   ("DE0008404005", "Allianz"),
    "BAS.DE":   ("DE000BASF111", "BASF"),
    "BAYN.DE":  ("DE000BAY0017", "Bayer"),
    "BEI.DE":   ("DE0005200000", "Beiersdorf"),
    "BMW.DE":   ("DE0005190003", "BMW"),
    "BNR.DE":   ("DE000A1DAHH0", "Brenntag"),
    "CBK.DE":   ("DE000CBK1001", "Commerzbank"),
    "CON.DE":   ("DE0005439004", "Continental"),
    "1COV.DE":  ("DE0006062144", "Covestro"),
    "DBK.DE":   ("DE0005140008", "Deutsche Bank"),
    "DB1.DE":   ("DE0005810055", "Deutsche Boerse"),
    "DHL.DE":   ("DE0005552004", "DHL Group"),
    "DTE.DE":   ("DE0005557508", "Deutsche Telekom"),
    "EOAN.DE":  ("DE000ENAG999", "E.ON"),
    "FMC.DE":   ("DE0005785802", "Fresenius Medical Care"),
    "FRE.DE":   ("DE0005785604", "Fresenius"),
    "HNR1.DE":  ("DE0008402215", "Hannover Rueck"),
    "HEIG.DE":  ("DE0006047004", "Heidelberg Materials"),
    "HEN3.DE":  ("DE0006048432", "Henkel"),
    "IFX.DE":   ("DE0006231004", "Infineon"),
    "MBG.DE":   ("DE0007100000", "Mercedes-Benz"),
    "MRK.DE":   ("DE0006599905", "Merck KGaA"),
    "MTX.DE":   ("DE000A0D9PT0", "MTU Aero Engines"),
    "MUV2.DE":  ("DE0008430026", "Munich Re"),
    "P911.DE":  ("DE000PAG9113", "Porsche AG"),
    "PAH3.DE":  ("DE000PAH0023", "Porsche SE"),
    "QIA.DE":   ("NL0012169213", "QIAGEN"),
    "RHM.DE":   ("DE0007030009", "Rheinmetall"),
    "RWE.DE":   ("DE0007037129", "RWE"),
    "SAP.DE":   ("DE0007164600", "SAP"),
    "SRT3.DE":  ("DE0007165631", "Sartorius"),
    "SIE.DE":   ("DE0007236101", "Siemens"),
    "ENR.DE":   ("DE000ENER6Y0", "Siemens Energy"),
    "SHL.DE":   ("DE000SHL1006", "Siemens Healthineers"),
    "SY1.DE":   ("DE000SY1SY11", "Symrise"),
    "VOW3.DE":  ("DE0007664039", "Volkswagen"),
    "VNA.DE":   ("DE000A1ML7J1", "Vonovia"),
    "ZAL.DE":   ("DE000ZAL1111", "Zalando"),
    "G24.DE":   ("DE000A12DM80", "Scout24"),
}

# ── Ticker list ────────────────────────────────────────────────────────────────

def get_eu_tickers() -> list[str]:
    """Returns all European tickers from market_configs, falling back to FTSE100 hardcoded."""
    try:
        from market_configs import get_all_european_symbols
        tickers = get_all_european_symbols()
        print(f"Loaded {len(tickers)} EU tickers from market_configs")
        return tickers
    except Exception as e:
        print(f"market_configs not available ({e}), using FTSE100 fallback")
        return [
            "SHEL.L", "AZN.L", "HSBA.L", "BP.L", "ULVR.L", "DGE.L", "GSK.L",
            "RIO.L", "VOD.L", "LSEG.L", "CPG.L", "NG.L", "BARC.L", "LLOY.L",
            "NWG.L", "STAN.L", "BATS.L", "IMB.L", "REL.L", "SGE.L",
            "HIK.L", "CNA.L", "EXPN.L", "RKT.L", "INF.L", "PSN.L", "BA.L",
            "RR.L", "MNDI.L", "TSCO.L",
        ]


def get_market(ticker: str) -> str:
    for suffix, market in SUFFIX_TO_MARKET.items():
        if ticker.endswith(suffix):
            return market
    return "EU"


# ── Data fetching ──────────────────────────────────────────────────────────────

def fetch_eu_insider_purchases(tickers: list[str], days_back: int = DAYS_BACK) -> pd.DataFrame:
    """
    Fetches individual insider purchases for EU tickers via yfinance.

    Filters applied:
    - Only rows where Text contains "Bought at price" (individual purchases)
    - Excludes "Buy Back" rows (corporate buybacks, already tracked separately)
    - Only transactions within the last `days_back` days
    """
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days_back)
    all_rows: list[pd.DataFrame] = []
    skipped = 0
    no_data = 0

    print(f"\nEU Insider Scanner — scanning {len(tickers)} tickers (last {days_back} days)")
    print("─" * 60)

    for i, ticker in enumerate(tickers):
        try:
            it = yf.Ticker(ticker).insider_transactions

            if it is None or it.empty:
                no_data += 1
                time.sleep(DELAY)
                continue

            # Filter: individual purchases only (not sales, not corporate buybacks)
            if "Text" not in it.columns:
                no_data += 1
                time.sleep(DELAY)
                continue

            buys = it[
                it["Text"].str.contains(r"Bought at price|Purchased at price", case=False, na=False) &
                ~it["Text"].str.contains(r"Buy Back", case=False, na=False)
            ].copy()

            if buys.empty:
                no_data += 1
                time.sleep(DELAY)
                continue

            # Filter: date range
            if "Start Date" in buys.columns:
                buys = buys[buys["Start Date"] >= cutoff]

            if buys.empty:
                no_data += 1
                time.sleep(DELAY)
                continue

            buys["ticker"] = ticker
            buys["market"] = get_market(ticker)
            all_rows.append(buys)

            print(f"   ✅ {ticker:<12} {len(buys):>3} purchases | market={get_market(ticker)}")

        except Exception as e:
            err = str(e)
            if "404" not in err and "Not Found" not in err:
                print(f"   ⚠️  {ticker}: {err[:60]}")
            skipped += 1

        time.sleep(DELAY)

        if (i + 1) % 25 == 0:
            print(f"\n   [{i+1}/{len(tickers)}] processed — {len(all_rows)} tickers with data so far\n")

    print(f"\n─ Scan complete: {len(all_rows)} tickers with purchases | {no_data} no data | {skipped} errors ─")

    if not all_rows:
        return pd.DataFrame()

    combined = pd.concat(all_rows, ignore_index=True)
    return combined


# ── BaFin scraper (DAX40) ──────────────────────────────────────────────────────

def fetch_bafin_dax40_purchases(days_back: int = DAYS_BACK) -> pd.DataFrame:
    """
    Fetches insider purchases for DAX40 tickers via BaFin Directors' Dealings portal.

    POST to sucheForm.do:
        emittentIsin = ISIN
        zeitraum     = 3  (custom date range)
        zeitraumVon  = DD.MM.YYYY
        zeitraumBis  = DD.MM.YYYY

    Response: HTML table where each data row has:
        col[3] = Meldepflichtiger (insider name)
        col[6] = Art des Geschäfts ("Kauf" = buy, "Verkauf" = sell)
        col[7] = Datum (DD.MM.YYYY)

    Returns DataFrame with columns: ticker, Insider, Start Date, market
    Compatible with analyze_eu_recurring().
    """
    if not BAFIN_AVAILABLE:
        print("   ⚠️  requests/BeautifulSoup not installed — BaFin DAX40 scan skipped")
        return pd.DataFrame()

    cutoff    = datetime.now() - pd.Timedelta(days=days_back)
    date_from = cutoff.strftime("%d.%m.%Y")
    date_to   = datetime.now().strftime("%d.%m.%Y")

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )

    all_rows: list[dict] = []
    skipped  = 0
    no_data  = 0

    print(f"\nBaFin DAX40 Scanner — scanning {len(DAX40_ISIN_MAP)} tickers (last {days_back} days)")
    print("─" * 60)

    for ticker, (isin, company) in DAX40_ISIN_MAP.items():
        try:
            r = session.post(
                BAFIN_URL,
                data={
                    "emittentIsin":   isin,
                    "emittentButton": "Suche Emittent",  # triggers the search
                    "zeitraum":       "3",               # custom date range
                    "zeitraumVon":    date_from,
                    "zeitraumBis":    date_to,
                },
                timeout=20,
            )
            r.encoding = "utf-8"

            soup = BeautifulSoup(r.text, "html.parser")

            # Search all table rows for data rows: ≥8 cells AND col[6] is Kauf/Verkauf
            purchases = 0
            for row in soup.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 8:
                    continue

                art = cells[6].get_text(strip=True)
                if art != "Kauf":
                    continue  # skip sales and any other transaction types

                name     = cells[3].get_text(strip=True)
                date_str = cells[7].get_text(strip=True)

                try:
                    date = pd.to_datetime(date_str, format="%d.%m.%Y")
                except Exception:
                    continue  # skip rows with unparseable dates

                all_rows.append({
                    "ticker":     ticker,
                    "Insider":    name,
                    "Start Date": date,
                    "market":     "DAX40",
                })
                purchases += 1

            if purchases > 0:
                print(f"   ✅ {ticker:<12} {purchases:>3} purchases | {company}")
            else:
                no_data += 1

        except Exception as e:
            err = str(e)
            if not any(s in err.lower() for s in ("timeout", "connection", "refused")):
                print(f"   ⚠️  {ticker} ({company}): {err[:60]}")
            skipped += 1

        time.sleep(BAFIN_DELAY)

    n_tickers = len({r["ticker"] for r in all_rows})
    print(f"\n─ BaFin scan complete: {n_tickers} tickers with purchases | {no_data} no data | {skipped} errors ─")

    if not all_rows:
        return pd.DataFrame()

    return pd.DataFrame(all_rows)


# ── Analysis ───────────────────────────────────────────────────────────────────

def analyze_eu_recurring(df: pd.DataFrame, min_purchases: int = MIN_PURCHASES) -> pd.DataFrame:
    """
    Identifies recurring insider buyers (≥ min_purchases) and computes confidence scores.
    Same formula as analyze_recurring_insiders.py for consistency:
        confidence = min(100, purchase_count × 20 + unique_insiders × 10)
    """
    if df.empty:
        return pd.DataFrame()

    results = []

    for ticker, group in df.groupby("ticker"):
        purchase_count = len(group)
        if purchase_count < min_purchases:
            continue

        unique_insiders = int(group["Insider"].nunique()) if "Insider" in group.columns else 1
        market = group["market"].iloc[0] if "market" in group.columns else get_market(str(ticker))

        dates = pd.to_datetime(group["Start Date"]) if "Start Date" in group.columns else pd.Series(dtype="datetime64[ns]")
        days_span = int((dates.max() - dates.min()).days) if len(dates) > 1 else 0
        first_purchase = dates.min().strftime("%Y-%m-%d") if len(dates) > 0 else ""
        last_purchase  = dates.max().strftime("%Y-%m-%d") if len(dates) > 0 else ""

        confidence_score = min(100, purchase_count * 20 + unique_insiders * 10)

        if confidence_score >= 60:
            label = "MUY ALTA"
        elif confidence_score >= 40:
            label = "ALTA"
        else:
            label = "MODERADA"

        results.append({
            "ticker":           ticker,
            "purchase_count":   purchase_count,
            "unique_insiders":  unique_insiders,
            "days_span":        days_span,
            "first_purchase":   first_purchase,
            "last_purchase":    last_purchase,
            "confidence_score": confidence_score,
            "confidence_label": label,
            "market":           market,
        })

    if not results:
        return pd.DataFrame()

    out = pd.DataFrame(results).sort_values("confidence_score", ascending=False).reset_index(drop=True)

    muy_alta = (out["confidence_label"] == "MUY ALTA").sum()
    alta     = (out["confidence_label"] == "ALTA").sum()
    moderada = (out["confidence_label"] == "MODERADA").sum()

    print(f"\nRecurring EU insider buyers found: {len(out)}")
    print(f"  MUY ALTA  (≥60): {muy_alta}")
    print(f"  ALTA      (≥40): {alta}")
    print(f"  MODERADA  (<40): {moderada}")
    print(f"\n  By market:")
    for market, grp in out.groupby("market"):
        print(f"    {market:<10}: {len(grp)} tickers")

    return out


# ── Save ───────────────────────────────────────────────────────────────────────

def save_eu_insiders(df: pd.DataFrame) -> None:
    DOCS.mkdir(exist_ok=True)
    path = DOCS / "eu_recurring_insiders.csv"
    if df.empty:
        # Write empty file with correct schema so API doesn't break
        empty = pd.DataFrame(columns=[
            "ticker", "purchase_count", "unique_insiders", "days_span",
            "first_purchase", "last_purchase", "confidence_score",
            "confidence_label", "market",
        ])
        empty.to_csv(path, index=False)
        print(f"Saved empty file: {path}")
    else:
        df.to_csv(path, index=False)
        print(f"\nSaved: {path} ({len(df)} tickers with recurring purchases)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("EUROPEAN INSIDER SCANNER")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    tickers = get_eu_tickers()

    # ── yfinance: FTSE100, AEX25 ───────────────────────────────────────────────
    raw_yf = fetch_eu_insider_purchases(tickers)

    # ── BaFin: DAX40 ──────────────────────────────────────────────────────────
    raw_bafin = fetch_bafin_dax40_purchases()

    # ── Merge and analyse ─────────────────────────────────────────────────────
    frames = [f for f in [raw_yf, raw_bafin] if not f.empty]
    if not frames:
        print("\nNo EU insider purchase data found — saving empty CSV.")
        save_eu_insiders(pd.DataFrame())
        sys.exit(0)

    raw = pd.concat(frames, ignore_index=True)
    recurring = analyze_eu_recurring(raw)
    save_eu_insiders(recurring)

    print("\nDone.")


if __name__ == "__main__":
    main()
