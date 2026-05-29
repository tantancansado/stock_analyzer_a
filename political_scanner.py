#!/usr/bin/env python3
"""
Political Scanner — agrega señales de mercado de fuentes gubernamentales públicas:

  1. Congressional trades  — Senate/House Stock Watcher (STOCK Act disclosures)
  2. Government contracts  — USASpending.gov API (contratos nuevos >$10M)
  3. Executive Orders      — Federal Register API (EOs que afectan sectores)

Output:
  - docs/political_signals.json  — histórico unificado
  - Telegram alert cuando hay señales nuevas de alta/media relevancia
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

DOCS = Path("docs")
DOCS.mkdir(exist_ok=True)

SIGNALS_PATH = DOCS / "political_signals.json"
SEEN_PATH    = DOCS / ".political_seen_hashes.json"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
GROQ_KEY  = os.environ.get("GROQ_API_KEY", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StockAnalyzer/1.0)",
    "Accept": "application/json",
}

# ─── Ticker lookups ───────────────────────────────────────────────────────────

# Top 300 S&P500 companies → ticker (lowercase name → ticker)
COMPANY_TO_TICKER: dict[str, str] = {
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA", "amazon": "AMZN",
    "alphabet": "GOOGL", "google": "GOOGL", "meta": "META", "tesla": "TSLA",
    "berkshire": "BRK-B", "eli lilly": "LLY", "jpmorgan": "JPM",
    "jp morgan": "JPM", "visa": "V", "unitedhealth": "UNH", "exxon": "XOM",
    "exxonmobil": "XOM", "johnson & johnson": "JNJ", "johnson and johnson": "JNJ",
    "walmart": "WMT", "mastercard": "MA", "procter & gamble": "PG",
    "procter and gamble": "PG", "home depot": "HD", "chevron": "CVX",
    "abbvie": "ABBV", "merck": "MRK", "costco": "COST", "pepsico": "PEP",
    "cocacola": "KO", "coca-cola": "KO", "coca cola": "KO",
    "bank of america": "BAC", "adobe": "ADBE", "salesforce": "CRM",
    "netflix": "NFLX", "disney": "DIS", "wells fargo": "WFC",
    "intel": "INTC", "qualcomm": "QCOM", "amd": "AMD",
    "advanced micro devices": "AMD", "oracle": "ORCL", "ibm": "IBM",
    "cisco": "CSCO", "comcast": "CMCSA", "pfizer": "PFE",
    "amgen": "AMGN", "gilead": "GILD", "moderna": "MRNA",
    "biogen": "BIIB", "bristol myers": "BMY", "bristol-myers": "BMY",
    "astrazeneca": "AZN", "novartis": "NVS", "roche": "RHHBY",
    "raytheon": "RTX", "lockheed": "LMT", "lockheed martin": "LMT",
    "northrop": "NOC", "northrop grumman": "NOC", "boeing": "BA",
    "general dynamics": "GD", "l3harris": "LHX", "leidos": "LDOS",
    "booz allen": "BAH", "saic": "SAIC", "caci": "CACI",
    "palantir": "PLTR", "anduril": None, "shield ai": None,
    "dell": "DELL", "dell technologies": "DELL", "hp": "HPQ", "hewlett": "HPQ",
    "accenture": "ACN", "cognizant": "CTSH", "gartner": "IT",
    "amazon web services": "AMZN", "aws": "AMZN",
    "microsoft azure": "MSFT", "azure": "MSFT",
    "google cloud": "GOOGL", "alphabet cloud": "GOOGL",
    "ups": "UPS", "fedex": "FDX",
    "caterpillar": "CAT", "deere": "DE", "john deere": "DE",
    "honeywell": "HON", "3m": "MMM", "ge": "GE", "general electric": "GE",
    "ge aerospace": "GE", "united technologies": "RTX",
    "eaton": "ETN", "parker": "PH", "emerson": "EMR",
    "ford": "F", "general motors": "GM",
    "us steel": "X", "united states steel": "X", "nucor": "NUE",
    "alcoa": "AA", "freeport": "FCX", "freeport-mcmoran": "FCX",
    "chevron phillips": "CVX",
    "schlumberger": "SLB", "halliburton": "HAL", "baker hughes": "BKR",
    "conocophillips": "COP", "pioneer": "PXD", "devon": "DVN",
    "first solar": "FSLR", "nextera": "NEE", "duke energy": "DUK",
    "southern company": "SO", "dominion": "D", "sempra": "SRE",
    "at&t": "T", "verizon": "VZ", "t-mobile": "TMUS",
    "charter": "CHTR", "comcast": "CMCSA",
    "jpmc": "JPM", "citigroup": "C", "citi": "C", "goldman": "GS",
    "goldman sachs": "GS", "morgan stanley": "MS", "blackrock": "BLK",
    "blackstone": "BX", "kkr": "KKR", "carlyle": "CG",
    "american airlines": "AAL", "delta": "DAL", "united airlines": "UAL",
    "southwest": "LUV",
    "trump media": "DJT", "truth social": "DJT",
}

# NAICS codes → sector name → watchlist tickers
NAICS_SECTOR_MAP: dict[str, tuple[str, list[str]]] = {
    "336":  ("Defense/Aerospace",  ["LMT", "RTX", "NOC", "BA", "GD", "LHX"]),
    "5415": ("IT/Software Gov",    ["PLTR", "LDOS", "BAH", "SAIC", "CACI", "MSFT"]),
    "5112": ("Software",           ["MSFT", "ORCL", "CRM", "ADBE"]),
    "3341": ("Computer Hardware",  ["DELL", "HPQ", "INTC", "AMD"]),
    "3344": ("Semiconductors",     ["NVDA", "INTC", "QCOM", "AMD", "MU"]),
    "2111": ("Oil & Gas",          ["XOM", "CVX", "COP", "HAL", "SLB"]),
    "2211": ("Electric Power",     ["NEE", "DUK", "SO", "D", "AES"]),
    "4841": ("Trucking/Logistics", ["UPS", "FDX"]),
    "6211": ("Healthcare",         ["UNH", "HUM", "CI", "CVS", "MCK"]),
    "3254": ("Pharma",             ["PFE", "MRK", "ABBV", "BMY", "LLY"]),
    "5171": ("Telecom",            ["VZ", "T", "TMUS"]),
    "5179": ("Telecom Resellers",  ["TMUS", "VZ", "T"]),
    "9711": ("National Defense",   ["LMT", "RTX", "NOC", "BA", "GD", "LHX", "LDOS"]),
    "9721": ("Int'l Affairs",      ["RTX", "LMT", "NOC"]),
}

# EO agency → affected tickers
EO_AGENCY_TICKERS: dict[str, list[str]] = {
    "Department of Defense":        ["LMT", "RTX", "NOC", "BA", "GD", "LHX", "PLTR"],
    "Department of Energy":         ["XOM", "CVX", "COP", "NEE", "FSLR", "PLUG"],
    "Department of Commerce":       ["NVDA", "INTC", "QCOM", "AMD", "AAPL", "MSFT"],
    "Office of the United States Trade Representative": ["BA", "CAT", "DE", "GM", "F"],
    "Food and Drug Administration": ["PFE", "MRK", "ABBV", "LLY", "AMGN", "GILD"],
    "Department of Health":         ["UNH", "HUM", "CI", "CVS", "PFE", "MRK"],
    "Securities and Exchange Commission": ["GS", "MS", "JPM", "BAC", "BLK"],
    "Federal Communications Commission": ["VZ", "T", "TMUS", "CMCSA", "CHTR"],
    "Department of Transportation": ["UAL", "DAL", "AAL", "LUV", "UPS", "FDX"],
    "Environmental Protection Agency": ["XOM", "CVX", "NEE", "DUK", "FSLR"],
    "Department of Homeland Security": ["LMT", "RTX", "BAH", "SAIC", "CACI", "PLTR"],
    "Department of the Treasury":   ["GS", "MS", "JPM", "BAC", "BLK", "BX"],
}

TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b")


# ─── Persistence ─────────────────────────────────────────────────────────────

def _load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text())
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        return {h for h, ts in data.items() if ts > cutoff}
    except Exception:
        return set()


def _save_seen(seen: set[str]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    existing: dict = {}
    if SEEN_PATH.exists():
        try:
            existing = json.loads(SEEN_PATH.read_text())
        except Exception:
            pass
    for h in seen:
        existing[h] = now
    if len(existing) > 3000:
        items = sorted(existing.items(), key=lambda kv: kv[1])
        existing = dict(items[-1500:])
    SEEN_PATH.write_text(json.dumps(existing))


def _load_signals() -> list[dict]:
    if not SIGNALS_PATH.exists():
        return []
    try:
        return json.loads(SIGNALS_PATH.read_text())
    except Exception:
        return []


def _save_signal(signal: dict) -> None:
    signals = _load_signals()
    # Deduplicate by id
    ids = {s["id"] for s in signals}
    if signal["id"] not in ids:
        signals.insert(0, signal)
    SIGNALS_PATH.write_text(json.dumps(signals[:1000], indent=2, default=str))


def _item_hash(*parts: str) -> str:
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:16]


# ─── Groq analysis ───────────────────────────────────────────────────────────

def _groq_relevance(text: str, context: str) -> dict | None:
    if not GROQ_KEY:
        return None
    prompt = f"""Analyze this {context} for stock market impact.

TEXT: {text[:1200]}

Return ONLY valid JSON:
{{
  "market_relevant": true,
  "tickers": ["AAPL"],
  "signal_type": "CONTRACT_AWARD",
  "signal_strength": "HIGH",
  "reasoning": "brief explanation"
}}

signal_type options: CONTRACT_AWARD | CONGRESS_BUY | CONGRESS_SELL | EXECUTIVE_ORDER | REGULATORY_CHANGE | TARIFF | NEUTRAL
signal_strength: HIGH (>$500M contract / >$500K trade / major EO) | MEDIUM | LOW
market_relevant: false if no specific publicly-traded company is clearly impacted"""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=15,
        )
        resp.raise_for_status()
        return json.loads(resp.json()["choices"][0]["message"]["content"])
    except Exception as e:
        log.warning("Groq failed: %s", e)
        return None


# ─── Telegram ────────────────────────────────────────────────────────────────

SIGNAL_ICONS = {
    "CONTRACT_AWARD":    "💰",
    "CONGRESS_BUY":      "🏛️📈",
    "CONGRESS_SELL":     "🏛️📉",
    "EXECUTIVE_ORDER":   "📜",
    "REGULATORY_CHANGE": "⚖️",
    "TARIFF":            "🚧",
    "NEUTRAL":           "📢",
}
STRENGTH_ICONS = {"HIGH": "🔥🔥🔥", "MEDIUM": "🟡🟡", "LOW": "⚪"}


def _send_telegram(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print("[DRY RUN]\n" + text + "\n")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": "true"},
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        log.error("Telegram failed: %s", e)


def _format_alert(signal: dict) -> str:
    sig = signal.get("signal_type", "NEUTRAL")
    strength = signal.get("signal_strength", "LOW")
    tickers = signal.get("tickers", [])
    source = signal.get("source_type", "?")

    lines = [
        f"{SIGNAL_ICONS.get(sig, '📢')} <b>POLITICAL SIGNAL</b> {STRENGTH_ICONS.get(strength, '')}",
        "",
        f"<b>Tipo:</b> {sig}",
        f"<b>Fuente:</b> {source}",
    ]
    if tickers:
        lines.append(f"<b>Tickers:</b> {' '.join('$' + t for t in tickers[:5])}")
    if signal.get("politician"):
        lines.append(f"<b>Político:</b> {signal['politician']} ({signal.get('party', '?')})")
    if signal.get("amount"):
        lines.append(f"<b>Importe:</b> {signal['amount']}")
    lines += [
        "",
        f"📝 {signal.get('reasoning', signal.get('title', '')[:200])}",
        "",
        f"📰 {signal.get('title', '')[:200]}",
    ]
    if signal.get("link"):
        lines.append(f"🔗 {signal['link']}")
    return "\n".join(lines)


# ─── Source 1: Congressional trades ──────────────────────────────────────────
# Uses the public JSON files from housestockwatcher.com / senatestockwatcher.com
# No auth required. Updated daily as STOCK Act filings are processed.

CONGRESS_SOURCES = [
    {
        "name": "Senate",
        "url": "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json",
        "fallback": "https://raw.githubusercontent.com/ratemydorm/senate-stock-watcher-data/master/all_transactions.json",
        "chamber": "Senate",
    },
    {
        "name": "House",
        "url": "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json",
        "fallback": "https://housestockwatcher.com/api/transactions_all.json",
        "chamber": "House",
    },
]

# Minimum days back to consider a trade "new"
CONGRESS_LOOKBACK_DAYS = 7

# Minimum amount bucket to alert (skip $1,001–$15,000 noise)
SKIP_AMOUNTS = {"$1,001 - $15,000", "$1,001 -$15,000"}

# Politicians known for market-moving trades (alert even on medium strength)
HIGH_PROFILE = {
    "Nancy Pelosi", "Paul Pelosi", "Dan Crenshaw", "Tommy Tuberville",
    "Richard Burr", "Kelly Loeffler", "David Perdue", "Ro Khanna",
    "Michael McCaul", "Virginia Foxx", "Josh Gottheimer",
}


def _parse_amount(amount_str: str | None) -> int:
    """Return midpoint of amount range in USD, 0 if unknown."""
    if not amount_str:
        return 0
    # e.g. "$1,001 - $15,000" → 8000; "$500,001 - $1,000,000" → 750000
    nums = re.findall(r"\$?([\d,]+)", amount_str)
    vals = [int(n.replace(",", "")) for n in nums]
    return sum(vals) // len(vals) if vals else 0


def _fetch_congress_trades(seen: set[str]) -> list[dict]:
    signals: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=CONGRESS_LOOKBACK_DAYS)

    for src in CONGRESS_SOURCES:
        data: list[dict] = []
        for url in [src["url"], src.get("fallback", "")]:
            if not url:
                continue
            try:
                r = requests.get(url, headers=HEADERS, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    log.info("  %s: %d trades loaded", src["name"], len(data))
                    break
            except Exception as e:
                log.warning("  %s fetch failed (%s): %s", src["name"], url[:60], e)

        if not data:
            continue

        for trade in data:
            # Parse date
            tx_date_str = trade.get("transaction_date") or trade.get("disclosure_date") or ""
            try:
                tx_date = datetime.strptime(tx_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if tx_date < cutoff:
                continue

            ticker = str(trade.get("ticker") or "").strip().upper()
            if not ticker or ticker in {"N/A", "--", ""}:
                continue
            # Skip bonds/funds that aren't stocks
            asset_type = str(trade.get("asset_type") or "").lower()
            if any(x in asset_type for x in ["bond", "note", "treasury", "mutual fund", "etf"]):
                continue

            amount = trade.get("amount") or trade.get("Range") or ""
            if amount in SKIP_AMOUNTS:
                continue

            tx_type = str(trade.get("type") or trade.get("Transaction") or "").lower()
            if not any(x in tx_type for x in ["purchase", "sale", "exchange"]):
                continue

            politician = f"{trade.get('first_name', '')} {trade.get('last_name', '')}".strip()
            if not politician:
                politician = trade.get("Representative") or trade.get("Senator") or "Unknown"

            sig_id = _item_hash(politician, ticker, tx_date_str, tx_type)
            if sig_id in seen:
                continue

            signal_type = "CONGRESS_BUY" if "purchase" in tx_type else "CONGRESS_SELL"
            amount_mid = _parse_amount(str(amount))
            if amount_mid >= 500_000 or politician in HIGH_PROFILE:
                strength = "HIGH"
            elif amount_mid >= 50_000:
                strength = "MEDIUM"
            else:
                strength = "LOW"

            party = str(trade.get("party") or "").strip() or "?"

            signals.append({
                "id": sig_id,
                "source_type": "CONGRESS_TRADE",
                "chamber": src["chamber"],
                "title": f"{politician} ({party}) — {signal_type.replace('_', ' ')} {ticker} [{amount}]",
                "politician": politician,
                "party": party,
                "ticker": ticker,
                "tickers": [ticker],
                "transaction_type": tx_type,
                "amount": str(amount),
                "amount_mid": amount_mid,
                "asset_description": str(trade.get("asset_description") or ""),
                "transaction_date": tx_date_str,
                "disclosure_date": trade.get("disclosure_date") or tx_date_str,
                "link": trade.get("ptr_link") or "",
                "scanned_at": datetime.now(timezone.utc).isoformat(),
                "signal_type": signal_type,
                "signal_strength": strength,
                "reasoning": f"{politician} ({src['chamber']}, {party}) {tx_type} {ticker} — {amount}",
            })

    log.info("Congressional trades: %d new signals", len(signals))
    return signals


# ─── Source 2: USASpending.gov contracts ─────────────────────────────────────
# Free API, no key needed. We search for recent large contract awards and
# try to map the recipient to a publicly-traded company.

USASPENDING_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
MIN_CONTRACT_USD = 10_000_000  # $10M minimum to reduce noise

def _recipient_to_tickers(name: str) -> list[str]:
    """Best-effort map of recipient company name to stock tickers."""
    name_lower = name.lower()
    found: list[str] = []

    # Direct map lookup
    for company, ticker in COMPANY_TO_TICKER.items():
        if company in name_lower and ticker:
            found.append(ticker)

    # Heuristic: extract first word and check
    first = name_lower.split()[0] if name_lower.split() else ""
    for company, ticker in COMPANY_TO_TICKER.items():
        if first and company.startswith(first) and ticker and ticker not in found:
            found.append(ticker)

    return list(dict.fromkeys(found))[:4]  # dedupe, max 4


def _fetch_contracts(seen: set[str]) -> list[dict]:
    signals: list[dict] = []
    today = datetime.now(timezone.utc)
    start_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": ["A", "B", "C", "D"],  # contracts only
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
            "Description", "Award Type", "Period of Performance Start Date",
            "Period of Performance Current End Date", "NAICS Code", "NAICS Description",
        ],
        "sort": "Award Amount",
        "order": "desc",
        "limit": 50,
        "page": 1,
    }

    try:
        r = requests.post(USASPENDING_URL, json=payload, headers=HEADERS, timeout=30)
        r.raise_for_status()
        awards = r.json().get("results", [])
        log.info("  USASpending: %d contracts fetched", len(awards))
    except Exception as e:
        log.warning("  USASpending fetch failed: %s", e)
        return []

    for award in awards:
        amount = float(award.get("Award Amount") or 0)
        if amount < MIN_CONTRACT_USD:
            continue

        recipient = str(award.get("Recipient Name") or "Unknown")
        tickers = _recipient_to_tickers(recipient)
        if not tickers:
            continue  # skip if we can't map to a stock

        naics = str(award.get("NAICS Code") or "")[:4]
        naics_info = NAICS_SECTOR_MAP.get(naics, ("Unknown", []))
        sector_name = naics_info[0]

        award_id = str(award.get("Award ID") or "")
        sig_id = _item_hash(award_id, recipient, str(int(amount)))
        if sig_id in seen:
            continue

        amount_fmt = f"${amount/1e9:.1f}B" if amount >= 1e9 else f"${amount/1e6:.0f}M"
        agency = str(award.get("Awarding Agency") or "")
        description = str(award.get("Description") or "")[:200]

        strength = "HIGH" if amount >= 500_000_000 else ("MEDIUM" if amount >= 50_000_000 else "LOW")

        signals.append({
            "id": sig_id,
            "source_type": "GOVERNMENT_CONTRACT",
            "title": f"{recipient} — contrato {amount_fmt} ({agency})",
            "recipient": recipient,
            "tickers": tickers,
            "amount": amount_fmt,
            "amount_raw": amount,
            "agency": agency,
            "naics_code": naics,
            "sector": sector_name,
            "description": description,
            "award_id": award_id,
            "link": f"https://www.usaspending.gov/award/{award_id}/",
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "signal_type": "CONTRACT_AWARD",
            "signal_strength": strength,
            "reasoning": f"{recipient} recibe contrato {amount_fmt} de {agency} | NAICS {naics} ({sector_name})",
        })

    log.info("Government contracts: %d new signals", len(signals))
    return signals


# ─── Source 3: Federal Register — Executive Orders ───────────────────────────

FEDREGISTER_URL = "https://www.federalregister.gov/api/v1/documents.json"

EO_MARKET_KEYWORDS = [
    "tariff", "trade", "sanction", "embargo", "defense", "energy",
    "semiconductor", "chip", "infrastructure", "broadband", "pharmaceutical",
    "drug price", "health care", "financial", "bank", "investment",
    "national security", "export control", "import", "manufacturing",
    "ai ", "artificial intelligence", "cybersecurity", "technology",
]


def _eo_to_tickers(title: str, abstract: str, agencies: list[str]) -> list[str]:
    """Map EO agencies + keywords to affected tickers."""
    tickers: set[str] = set()
    combined = f"{title} {abstract}".lower()

    for agency in agencies:
        for agency_key, agency_tickers in EO_AGENCY_TICKERS.items():
            if agency_key.lower() in agency.lower():
                tickers.update(agency_tickers)

    # Keyword-based additions
    if any(k in combined for k in ["semiconductor", "chip", "ai ", "artificial intelligence"]):
        tickers.update(["NVDA", "INTC", "QCOM", "AMD", "AMAT", "LRCX"])
    if any(k in combined for k in ["defense", "pentagon", "military", "national security"]):
        tickers.update(["LMT", "RTX", "NOC", "BA", "GD"])
    if any(k in combined for k in ["tariff", "trade", "import", "steel", "aluminum"]):
        tickers.update(["X", "NUE", "AA", "STLD", "CAT", "DE"])
    if any(k in combined for k in ["pharmaceutical", "drug price", "health"]):
        tickers.update(["PFE", "MRK", "ABBV", "LLY", "UNH"])
    if any(k in combined for k in ["energy", "oil", "gas", "lng", "pipeline"]):
        tickers.update(["XOM", "CVX", "COP", "HAL", "SLB"])
    if any(k in combined for k in ["bank", "financial", "wall street", "investment"]):
        tickers.update(["JPM", "BAC", "GS", "MS", "BLK"])

    return list(tickers)[:8]


def _fetch_executive_orders(seen: set[str]) -> list[dict]:
    signals: list[dict] = []

    params = {
        "conditions[presidential_document_type]": "executive_order",
        "conditions[type]": "PRESDOC",
        "per_page": 20,
        "order": "newest",
        "fields[]": ["document_number", "title", "abstract", "signing_date",
                     "publication_date", "executive_order_number", "agencies",
                     "html_url", "full_text_xml_url"],
    }

    try:
        r = requests.get(FEDREGISTER_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
        results = r.json().get("results", [])
        log.info("  Federal Register: %d EOs fetched", len(results))
    except Exception as e:
        log.warning("  Federal Register fetch failed: %s", e)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    for doc in results:
        pub_date_str = doc.get("publication_date") or doc.get("signing_date") or ""
        try:
            pub_date = datetime.strptime(pub_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if pub_date < cutoff:
            continue

        title = str(doc.get("title") or "")
        abstract = str(doc.get("abstract") or "")
        combined_lower = f"{title} {abstract}".lower()

        # Only process EOs with market-relevant keywords
        if not any(kw in combined_lower for kw in EO_MARKET_KEYWORDS):
            continue

        agencies_raw = doc.get("agencies", [])
        agency_names = [a.get("name", "") for a in agencies_raw if isinstance(a, dict)]

        tickers = _eo_to_tickers(title, abstract, agency_names)
        if not tickers:
            continue

        eo_num = str(doc.get("executive_order_number") or doc.get("document_number") or "")
        sig_id = _item_hash("EO", eo_num, title[:50])
        if sig_id in seen:
            continue

        strength = "HIGH" if any(kw in combined_lower for kw in [
            "national emergency", "tariff", "sanction", "defense", "semiconductor"
        ]) else "MEDIUM"

        signals.append({
            "id": sig_id,
            "source_type": "EXECUTIVE_ORDER",
            "title": f"EO {eo_num}: {title}",
            "eo_number": eo_num,
            "abstract": abstract[:400],
            "agencies": agency_names[:5],
            "tickers": tickers[:8],
            "signing_date": doc.get("signing_date") or pub_date_str,
            "publication_date": pub_date_str,
            "link": doc.get("html_url") or "",
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "signal_type": "EXECUTIVE_ORDER",
            "signal_strength": strength,
            "reasoning": f"Executive Order {eo_num}: {title[:150]}",
        })

    log.info("Executive Orders: %d new signals", len(signals))
    return signals


# ─── Main scan ────────────────────────────────────────────────────────────────

def scan() -> int:
    seen = _load_seen()
    all_signals: list[dict] = []
    new_hashes: set[str] = set()

    log.info("=== Congressional Trades ===")
    congress = _fetch_congress_trades(seen)
    all_signals.extend(congress)

    log.info("=== Government Contracts (USASpending) ===")
    contracts = _fetch_contracts(seen)
    all_signals.extend(contracts)

    log.info("=== Executive Orders (Federal Register) ===")
    eos = _fetch_executive_orders(seen)
    all_signals.extend(eos)

    # Save + alert
    for signal in all_signals:
        _save_signal(signal)
        new_hashes.add(signal["id"])
        # Only Telegram for medium+ signals
        if signal.get("signal_strength") in ("HIGH", "MEDIUM"):
            _send_telegram(_format_alert(signal))
            time.sleep(0.5)

    _save_seen(new_hashes)
    log.info("Scan complete — %d new political signals", len(all_signals))
    return len(all_signals)


def print_recent(n: int = 15) -> None:
    signals = _load_signals()
    if not signals:
        print("No signals recorded yet.")
        return
    print(f"\n{'='*70}\nPOLITICAL SIGNALS — last {min(n, len(signals))}\n{'='*70}")
    for s in signals[:n]:
        src  = s.get("source_type", "?")
        sig  = s.get("signal_type", "?")
        stre = s.get("signal_strength", "?")
        tks  = " ".join("$" + t for t in s.get("tickers", [])[:4])
        ttl  = s.get("title", "")[:80]
        dt   = s.get("scanned_at", "?")[:16]
        print(f"  [{dt}] {src} | {sig} [{stre}] {tks}")
        print(f"         {ttl}")
        print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        print_recent(20)
    else:
        count = scan()
        print(f"\nDone — {count} political signals detected.")
        if count > 0:
            print_recent(count)
