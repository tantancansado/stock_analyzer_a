#!/usr/bin/env python3
"""
Trump Stock Scanner — detecta cuando Trump (u otros políticos/insiders clave)
menciona empresas o acciones en Truth Social, RSS de noticias y Google News,
y dispara alerta Telegram con análisis IA del impacto potencial.

Fuentes:
  1. Truth Social scraping (con headers correctos)
  2. Google News RSS: "Trump stock company"
  3. Reuters / MarketWatch / CNBC RSS con filtro Trump
  4. AP News RSS

Lógica IA (Groq llama-3.3-70b):
  - Detecta tickers/empresas mencionadas
  - Clasifica BUY_SIGNAL / SELL_SIGNAL / CONTRACT_AWARD / TARIFF_IMPACT / NEUTRAL
  - Estima movimiento esperado basado en contexto histórico

Output:
  - Telegram alert inmediata con ticker, precio actual, análisis
  - docs/trump_signals.json — histórico persistente
"""
from __future__ import annotations

import json
import os
import re
import time
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

DOCS = Path("docs")
DOCS.mkdir(exist_ok=True)

SIGNALS_PATH = DOCS / "trump_signals.json"
SEEN_PATH    = DOCS / ".trump_seen_hashes.json"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
GROQ_KEY  = os.environ.get("GROQ_API_KEY", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

RSS_SOURCES = [
    {
        "name": "Google News: Trump company stock",
        "url": "https://news.google.com/rss/search?q=%22trump%22+%22stock%22+%22company%22&hl=en-US&gl=US&ceid=US:en",
        "type": "news",
        "filter_keywords": ["trump"],
    },
    {
        "name": "Google News: Trump contract deal",
        "url": "https://news.google.com/rss/search?q=%22trump%22+%22contract%22+%22billion%22&hl=en-US&gl=US&ceid=US:en",
        "type": "news",
        "filter_keywords": ["trump"],
    },
    {
        "name": "Reuters Politics",
        "url": "https://feeds.reuters.com/Reuters/politicsNews",
        "type": "news",
        "filter_keywords": ["trump", "president", "white house"],
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "type": "news",
        "filter_keywords": ["trump", "contract", "executive order", "tariff"],
    },
    {
        "name": "CNBC Top News",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "type": "news",
        "filter_keywords": ["trump", "government contract", "billion"],
    },
]

STOCK_SIGNAL_KEYWORDS = [
    "buy", "great company", "great stock", "should buy", "recommend",
    "contract", "billion dollar", "billion-dollar", "$9", "$7", "$5", "$3",
    "deal", "award", "selected", "chosen", "beautiful company",
    "tremendous", "invest", "stock market", "shares", "nasdaq", "nyse",
    "executive order", "tariff", "trade deal", "sanction", "fine",
    "department of defense", "pentagon", "dod contract", "federal contract",
    "white house", "administration buy",
]

TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b")

# Companies Trump has mentioned historically (for fallback matching)
KNOWN_TRUMP_TARGETS = {
    "dell": "DELL", "dell technologies": "DELL",
    "nvidia": "NVDA", "nvda": "NVDA",
    "intel": "INTC",
    "micron": "MU",
    "apple": "AAPL",
    "boeing": "BA",
    "lockheed": "LMT", "lockheed martin": "LMT",
    "raytheon": "RTX",
    "palantir": "PLTR",
    "spacex": None,  # private
    "exxon": "XOM", "exxonmobil": "XOM",
    "us steel": "X",
    "ford": "F",
    "general motors": "GM",
    "truth social": "DJT", "trump media": "DJT",
}


def _groq_analyze(text: str) -> dict | None:
    if not GROQ_KEY:
        return None

    prompt = f"""Analyze this US political news headline/statement for STOCK MARKET SIGNALS.

TEXT: {text[:1500]}

Does this text mention specific companies or stocks, and imply a positive or negative effect on their stock price?

Return ONLY valid JSON:
{{
  "has_stock_signal": true,
  "tickers": ["DELL"],
  "companies": ["Dell Technologies"],
  "signal_type": "CONTRACT_AWARD",
  "signal_strength": "HIGH",
  "reasoning": "Gobierno EEUU adjudica contrato $9.7B a Dell",
  "expected_move_pct": 20
}}

signal_type: BUY_SIGNAL | SELL_SIGNAL | CONTRACT_AWARD | TARIFF_IMPACT | REGULATORY_THREAT | TRADE_DEAL | NEUTRAL
signal_strength: HIGH (direct endorsement / >$1B contract / major executive order) | MEDIUM | LOW
has_stock_signal: false if no specific company is mentioned or clearly implied
expected_move_pct: estimated % move based on signal strength (can be null)

Be precise. Only mark has_stock_signal=true if a real company/stock is specifically named or unmistakably implied."""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=20,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        log.warning("Groq failed: %s", e)
        return None


def _fallback_analyze(full_text: str) -> dict | None:
    """Análisis sin IA: busca tickers explícitos y nombres de empresas conocidas."""
    tickers: list[str] = []
    companies: list[str] = []

    # 1. Explicit $TICKER pattern
    found = TICKER_RE.findall(full_text)
    tickers.extend(found[:4])

    # 2. Known company name matching
    text_lower = full_text.lower()
    for name, tk in KNOWN_TRUMP_TARGETS.items():
        if name in text_lower and tk and tk not in tickers:
            tickers.append(tk)
            companies.append(name.title())

    if not tickers:
        return None

    # Determine signal type from keywords
    sig_type = "BUY_SIGNAL"
    if any(k in text_lower for k in ["contract", "billion", "award", "pentagon", "dod"]):
        sig_type = "CONTRACT_AWARD"
    elif any(k in text_lower for k in ["tariff", "sanction", "fine", "ban"]):
        sig_type = "TARIFF_IMPACT"

    return {
        "has_stock_signal": True,
        "tickers": tickers[:4],
        "companies": companies[:3],
        "signal_type": sig_type,
        "signal_strength": "MEDIUM",
        "reasoning": f"Ticker/empresa detectada sin análisis IA: {', '.join(tickers)}",
        "expected_move_pct": None,
    }


def _get_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="1d")
        return round(float(hist["Close"].iloc[-1]), 2) if not hist.empty else None
    except Exception:
        return None


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
        log.info("Telegram sent OK")
    except Exception as e:
        log.error("Telegram failed: %s", e)


def _format_alert(item: dict, analysis: dict) -> str:
    icons = {
        "BUY_SIGNAL": "🚀", "SELL_SIGNAL": "🔴", "CONTRACT_AWARD": "💰",
        "TARIFF_IMPACT": "⚠️", "REGULATORY_THREAT": "🚫",
        "TRADE_DEAL": "🤝", "NEUTRAL": "📢",
    }
    strength_icons = {"HIGH": "🔥🔥🔥", "MEDIUM": "🟡🟡", "LOW": "⚪"}
    sig      = analysis.get("signal_type", "NEUTRAL")
    strength = analysis.get("signal_strength", "LOW")
    tickers  = analysis.get("tickers", [])
    companies= analysis.get("companies", [])
    reasoning= analysis.get("reasoning", "")
    expected = analysis.get("expected_move_pct")

    price_lines = []
    for tk in tickers[:4]:
        price = _get_price(tk)
        price_lines.append(f"  <b>${tk}</b>: {'$' + str(price) if price else 'N/A'}")

    lines = [
        f"{icons.get(sig, '📢')} <b>TRUMP SIGNAL</b> {strength_icons.get(strength, '')}",
        "",
        f"<b>Tipo:</b> {sig}",
        f"<b>Fuerza:</b> {strength}",
    ]
    if companies:
        lines.append(f"<b>Empresa:</b> {', '.join(companies[:3])}")
    if tickers:
        lines.append(f"<b>Tickers:</b> {' '.join('$' + t for t in tickers[:4])}")
    if expected:
        lines.append(f"<b>Movimiento esperado:</b> ~{expected}%")
    if price_lines:
        lines += ["", "<b>Precio actual:</b>"] + price_lines
    lines += [
        "",
        f"📝 {reasoning}",
        "",
        f"<i>{item.get('title', '')[:250]}</i>",
        "",
        f"📰 {item.get('source', '?')} | {item.get('published', '')[:16]}",
    ]
    if item.get("link"):
        lines.append(f"🔗 {item['link']}")
    return "\n".join(lines)


def _fetch_rss(url: str) -> list[dict]:
    try:
        import feedparser
        feed = feedparser.parse(url, request_headers=HEADERS)
        return [
            {
                "title":   getattr(e, "title", ""),
                "summary": getattr(e, "summary", "") or getattr(e, "description", ""),
                "link":    getattr(e, "link", ""),
                "published": getattr(e, "published", "") or datetime.now(timezone.utc).isoformat(),
            }
            for e in feed.entries[:25]
        ]
    except Exception as ex:
        log.warning("RSS failed %s: %s", url, ex)
        return []


def _fetch_truthsocial() -> list[dict]:
    """Scrape Trump's Truth Social posts looking for stock mentions."""
    try:
        r = requests.get(
            "https://truthsocial.com/api/v1/accounts/107780257626128497/statuses?limit=20",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        posts = r.json()
        items = []
        for p in posts:
            content = re.sub(r"<[^>]+>", " ", p.get("content", ""))
            items.append({
                "title": content[:200],
                "summary": content,
                "link": p.get("url", ""),
                "published": p.get("created_at", ""),
            })
        return items
    except Exception as e:
        log.warning("Truth Social API failed: %s", e)
        return []


def _item_hash(item: dict) -> str:
    key = (item.get("link") or item.get("title", ""))[:200]
    return hashlib.md5(key.encode()).hexdigest()


def _load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text())
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
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
    if len(existing) > 2000:
        items = sorted(existing.items(), key=lambda kv: kv[1])
        existing = dict(items[-1000:])
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
    signals.insert(0, signal)
    SIGNALS_PATH.write_text(json.dumps(signals[:500], indent=2, default=str))


def _is_trump_related(text: str, source_type: str) -> bool:
    if source_type == "primary":
        return True
    return any(kw in text.lower() for kw in [
        "trump", "president trump", "white house", "maga",
        "truth social", "mar-a-lago", "donald trump",
    ])


def _has_stock_keywords(text: str) -> bool:
    return any(kw in text.lower() for kw in STOCK_SIGNAL_KEYWORDS)


def _process_items(items: list[dict], source_name: str, source_type: str, seen: set[str]) -> tuple[int, set[str]]:
    new_signals = 0
    new_hashes: set[str] = set()

    for item in items:
        h = _item_hash(item)
        if h in seen:
            continue
        new_hashes.add(h)

        full_text = f"{item.get('title', '')} {item.get('summary', '')}"

        if not _is_trump_related(full_text, source_type):
            continue
        if not _has_stock_keywords(full_text) and not TICKER_RE.search(full_text):
            continue

        log.info("  Potential signal: %s", item.get("title", "")[:80])
        item["source"] = source_name

        analysis = _groq_analyze(full_text) or _fallback_analyze(full_text)
        if not analysis or not analysis.get("has_stock_signal"):
            continue

        signal = {
            "id": h,
            "source": source_name,
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "published": item.get("published", ""),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis,
            "tickers": analysis.get("tickers", []),
            "signal_type": analysis.get("signal_type", "NEUTRAL"),
            "signal_strength": analysis.get("signal_strength", "LOW"),
        }
        _save_signal(signal)
        _send_telegram(_format_alert(item, analysis))
        new_signals += 1
        log.info("  SIGNAL: %s %s", signal["signal_type"], signal["tickers"])
        time.sleep(1)

    return new_signals, new_hashes


def scan() -> int:
    seen = _load_seen()
    total_signals = 0
    all_new_hashes: set[str] = set()

    # Truth Social (direct API)
    log.info("Scanning Truth Social (API)...")
    ts_items = _fetch_truthsocial()
    log.info("  Got %d posts", len(ts_items))
    n, hashes = _process_items(ts_items, "Trump Truth Social", "primary", seen)
    total_signals += n
    all_new_hashes |= hashes
    seen |= hashes

    # RSS sources
    for src in RSS_SOURCES:
        log.info("Scanning %s ...", src["name"])
        items = _fetch_rss(src["url"])
        log.info("  Got %d items", len(items))
        n, hashes = _process_items(items, src["name"], src["type"], seen)
        total_signals += n
        all_new_hashes |= hashes
        seen |= hashes

    _save_seen(all_new_hashes)
    log.info("Scan complete — %d new signals", total_signals)
    return total_signals


def print_recent(n: int = 10) -> None:
    signals = _load_signals()
    if not signals:
        print("No signals recorded yet.")
        return
    print(f"\n{'='*60}\nTRUMP STOCK SIGNALS — last {min(n, len(signals))}\n{'='*60}")
    for s in signals[:n]:
        tks  = " ".join("$" + t for t in s.get("tickers", []))
        ts   = s.get("scanned_at", "?")[:16]
        sig  = s.get("signal_type", "?")
        stre = s.get("signal_strength", "?")
        ttl  = s.get("title", "")[:70]
        reas = s.get("analysis", {}).get("reasoning", "")
        print(f"  [{ts}] {sig} [{stre}] {tks}")
        print(f"         {ttl}")
        if reas:
            print(f"         => {reas}")
        print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        print_recent(20)
    else:
        count = scan()
        print(f"\nDone — {count} signals detected.")
        if count > 0:
            print_recent(count)
