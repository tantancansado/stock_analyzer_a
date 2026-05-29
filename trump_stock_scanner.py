#!/usr/bin/env python3
"""
Trump Stock Scanner — captura TODOS los posts de Truth Social + noticias RSS,
analiza con IA (Claude o Groq) si tienen relevancia de mercado, y guarda el
feed completo en docs/trump_signals.json.

Todos los posts se guardan. Los que tienen impacto de mercado llevan
market_relevant=true y el análisis de tickers/sectores.

Problema 403 en GitHub Actions: Truth Social bloquea IPs de AWS/cloud.
Solución: rotación de User-Agent + headers de browser real.
Si sigue fallando, el scanner usa las fuentes RSS como fallback.
"""
from __future__ import annotations

import json, os, re, time, hashlib, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

DOCS       = Path("docs")
DOCS.mkdir(exist_ok=True)
SIGNALS_PATH = DOCS / "trump_signals.json"
SEEN_PATH    = DOCS / ".trump_seen_hashes.json"

BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID      = os.environ.get("TELEGRAM_CHAT_ID", "")
GROQ_KEY     = os.environ.get("GROQ_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Varios User-Agents para rotar y evitar 403
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

TRUTHSOCIAL_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://truthsocial.com/@realDonaldTrump",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}

RSS_SOURCES = [
    {
        "name": "Google News: Trump stock company",
        "url": "https://news.google.com/rss/search?q=%22trump%22+%22stock%22+%22company%22&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "name": "Google News: Trump contract billion",
        "url": "https://news.google.com/rss/search?q=%22trump%22+%22contract%22+%22billion%22&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "name": "Google News: Trump tariff trade",
        "url": "https://news.google.com/rss/search?q=%22trump%22+%22tariff%22+OR+%22executive+order%22&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "name": "Reuters Politics",
        "url": "https://feeds.reuters.com/Reuters/politicsNews",
    },
    {
        "name": "MarketWatch Top Stories",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
    },
]

KNOWN_COMPANIES: dict[str, str] = {
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA", "amazon": "AMZN",
    "google": "GOOGL", "alphabet": "GOOGL", "meta": "META", "tesla": "TSLA",
    "dell": "DELL", "dell technologies": "DELL", "intel": "INTC",
    "boeing": "BA", "lockheed": "LMT", "lockheed martin": "LMT",
    "raytheon": "RTX", "northrop": "NOC", "general dynamics": "GD",
    "palantir": "PLTR", "exxon": "XOM", "exxonmobil": "XOM",
    "chevron": "CVX", "ford": "F", "general motors": "GM",
    "us steel": "X", "micron": "MU", "qualcomm": "QCOM",
    "trump media": "DJT", "truth social": "DJT",
    "jpmorgan": "JPM", "jp morgan": "JPM", "goldman": "GS",
    "bank of america": "BAC", "citigroup": "C",
    "pfizer": "PFE", "moderna": "MRNA", "johnson": "JNJ",
    "walmart": "WMT", "home depot": "HD", "disney": "DIS",
    "netflix": "NFLX", "at&t": "T", "verizon": "VZ",
    "first solar": "FSLR", "nextera": "NEE",
    "halliburton": "HAL", "schlumberger": "SLB",
    "leidos": "LDOS", "booz allen": "BAH", "saic": "SAIC",
}

TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b")


# ─── AI analysis ─────────────────────────────────────────────────────────────

AI_PROMPT = """You are a financial analyst. Analyze this text from Trump (Truth Social post or news headline) for stock market impact.

TEXT: {text}

Return ONLY valid JSON — no markdown, no explanation:
{{
  "market_relevant": true,
  "tickers": ["AAPL"],
  "companies": ["Apple"],
  "sectors": ["Technology"],
  "signal_type": "BUY_SIGNAL",
  "signal_strength": "HIGH",
  "sentiment": "BULLISH",
  "reasoning": "Trump endorsed Apple directly",
  "expected_move_pct": 5
}}

Rules:
- market_relevant: true ONLY if a specific publicly-traded company, sector, or financial policy (tariff, rate, regulation) is mentioned
- signal_type: BUY_SIGNAL | SELL_SIGNAL | CONTRACT_AWARD | TARIFF_IMPACT | REGULATORY_THREAT | TRADE_DEAL | CRYPTO | SECTOR_ROTATION | NEUTRAL
- signal_strength: HIGH (direct mention/endorsement, >$1B contract, major tariff) | MEDIUM (indirect, sector-level) | LOW (vague reference)
- sentiment: BULLISH | BEARISH | NEUTRAL
- tickers: only real NYSE/NASDAQ tickers you are confident about, empty array if none
- sectors: affected sectors even if no specific ticker (e.g. ["Defense", "Semiconductors"])
- expected_move_pct: realistic % move estimate, null if uncertain
- If purely political with zero market impact → market_relevant: false, everything else empty/null"""


def _analyze_with_claude(text: str) -> dict | None:
    if not ANTHROPIC_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": AI_PROMPT.format(text=text[:1500])}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        content = resp.json()["content"][0]["text"].strip()
        # Strip markdown code fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        return json.loads(content)
    except Exception as e:
        log.warning("Claude analysis failed: %s", e)
        return None


def _analyze_with_groq(text: str) -> dict | None:
    if not GROQ_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": AI_PROMPT.format(text=text[:1500])}],
                "max_tokens": 400,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=20,
        )
        resp.raise_for_status()
        return json.loads(resp.json()["choices"][0]["message"]["content"])
    except Exception as e:
        log.warning("Groq analysis failed: %s", e)
        return None


def _analyze_fallback(text: str) -> dict:
    """Análisis sin IA: regex + diccionario de empresas conocidas."""
    tickers: list[str] = list(dict.fromkeys(TICKER_RE.findall(text)))
    companies: list[str] = []
    text_lower = text.lower()

    for name, tk in KNOWN_COMPANIES.items():
        if name in text_lower and tk not in tickers:
            tickers.append(tk)
            companies.append(name.title())

    market_relevant = bool(tickers)
    sig_type = "NEUTRAL"
    if tickers:
        if any(k in text_lower for k in ["contract", "billion", "pentagon", "dod", "award"]):
            sig_type = "CONTRACT_AWARD"
        elif any(k in text_lower for k in ["tariff", "sanction", "ban", "fine"]):
            sig_type = "TARIFF_IMPACT"
        elif any(k in text_lower for k in ["buy", "great company", "beautiful", "recommend"]):
            sig_type = "BUY_SIGNAL"

    return {
        "market_relevant": market_relevant,
        "tickers": tickers[:5],
        "companies": companies[:3],
        "sectors": [],
        "signal_type": sig_type,
        "signal_strength": "MEDIUM" if tickers else "LOW",
        "sentiment": "BULLISH" if sig_type == "BUY_SIGNAL" else "NEUTRAL",
        "reasoning": f"Fallback (no AI): {', '.join(tickers) if tickers else 'no tickers found'}",
        "expected_move_pct": None,
    }


def _analyze(text: str) -> dict:
    """Try Claude → Groq → fallback."""
    result = _analyze_with_claude(text) or _analyze_with_groq(text) or _analyze_fallback(text)
    # Normalize: ensure all keys exist
    result.setdefault("market_relevant", False)
    result.setdefault("tickers", [])
    result.setdefault("sectors", [])
    result.setdefault("signal_type", "NEUTRAL")
    result.setdefault("signal_strength", "LOW")
    result.setdefault("sentiment", "NEUTRAL")
    result.setdefault("reasoning", "")
    result.setdefault("expected_move_pct", None)
    return result


# ─── Truth Social fetch ───────────────────────────────────────────────────────

def _fetch_truthsocial() -> list[dict]:
    import random
    ua = random.choice(USER_AGENTS)
    headers = {**TRUTHSOCIAL_HEADERS, "User-Agent": ua}

    for attempt in range(3):
        try:
            r = requests.get(
                "https://truthsocial.com/api/v1/accounts/107780257626128497/statuses?limit=40",
                headers=headers,
                timeout=15,
            )
            if r.status_code == 403:
                log.warning("Truth Social 403 (attempt %d) — IP blocked by server", attempt + 1)
                time.sleep(2)
                continue
            if r.status_code != 200:
                log.warning("Truth Social HTTP %d", r.status_code)
                return []
            posts = r.json()
            items = []
            for p in posts:
                # Strip HTML tags from content
                raw = re.sub(r"<[^>]+>", " ", p.get("content", ""))
                raw = re.sub(r"\s+", " ", raw).strip()
                if not raw:
                    continue
                items.append({
                    "id": p["id"],
                    "title": raw[:280],
                    "full_text": raw,
                    "link": p.get("url", ""),
                    "published": p.get("created_at", ""),
                    "source": "Trump Truth Social",
                    "is_repost": p.get("reblog") is not None,
                    "replies": p.get("replies_count", 0),
                    "reposts": p.get("reblogs_count", 0),
                    "likes": p.get("favourites_count", 0),
                })
            log.info("Truth Social: %d posts fetched", len(items))
            return items
        except Exception as e:
            log.warning("Truth Social fetch error (attempt %d): %s", attempt + 1, e)
            time.sleep(2)
    return []


# ─── RSS fetch ────────────────────────────────────────────────────────────────

def _fetch_rss(url: str, source_name: str) -> list[dict]:
    try:
        import feedparser
        feed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENTS[0]})
        items = []
        for e in feed.entries[:20]:
            title = getattr(e, "title", "")
            summary = re.sub(r"<[^>]+>", " ", getattr(e, "summary", "") or "")
            full = f"{title}. {summary}".strip()
            items.append({
                "id": None,
                "title": title,
                "full_text": full[:800],
                "link": getattr(e, "link", ""),
                "published": getattr(e, "published", datetime.now(timezone.utc).isoformat()),
                "source": source_name,
                "is_repost": False,
                "replies": 0, "reposts": 0, "likes": 0,
            })
        return items
    except Exception as e:
        log.warning("RSS %s failed: %s", source_name, e)
        return []


# ─── Persistence ─────────────────────────────────────────────────────────────

def _item_hash(item: dict) -> str:
    key = item.get("id") or (item.get("link") or item.get("title", ""))[:200]
    return hashlib.md5(str(key).encode()).hexdigest()[:16]


def _load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text())
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        return {h for h, ts in data.items() if ts > cutoff}
    except Exception:
        return set()


def _save_seen(hashes: set[str]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    existing: dict = {}
    if SEEN_PATH.exists():
        try:
            existing = json.loads(SEEN_PATH.read_text())
        except Exception:
            pass
    for h in hashes:
        existing[h] = now
    if len(existing) > 2000:
        existing = dict(sorted(existing.items(), key=lambda kv: kv[1])[-1000:])
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
    ids = {s["id"] for s in signals}
    if signal["id"] not in ids:
        signals.insert(0, signal)
    SIGNALS_PATH.write_text(json.dumps(signals[:500], indent=2, default=str))


# ─── Telegram ────────────────────────────────────────────────────────────────

SIGNAL_ICONS = {
    "BUY_SIGNAL": "🚀", "SELL_SIGNAL": "🔴", "CONTRACT_AWARD": "💰",
    "TARIFF_IMPACT": "⚠️", "REGULATORY_THREAT": "🚫",
    "TRADE_DEAL": "🤝", "CRYPTO": "₿", "SECTOR_ROTATION": "🔄", "NEUTRAL": "📢",
}
SENTIMENT_ICONS = {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}
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
    analysis = signal.get("analysis", {})
    sig = analysis.get("signal_type", "NEUTRAL")
    strength = analysis.get("signal_strength", "LOW")
    sentiment = analysis.get("sentiment", "NEUTRAL")
    tickers = analysis.get("tickers", [])
    sectors = analysis.get("sectors", [])
    reasoning = analysis.get("reasoning", "")
    expected = analysis.get("expected_move_pct")

    lines = [
        f"{SIGNAL_ICONS.get(sig, '📢')} <b>TRUMP SIGNAL</b> {STRENGTH_ICONS.get(strength, '')} {SENTIMENT_ICONS.get(sentiment, '')}",
        f"<b>Tipo:</b> {sig} | <b>Fuerza:</b> {strength}",
    ]
    if tickers:
        lines.append(f"<b>Tickers:</b> {' '.join('$' + t for t in tickers[:5])}")
    if sectors:
        lines.append(f"<b>Sectores:</b> {', '.join(sectors[:3])}")
    if expected:
        lines.append(f"<b>Movimiento est.:</b> ~{expected}%")
    lines += [
        "",
        f"💬 <i>{signal.get('title', '')[:300]}</i>",
        "",
        f"📝 {reasoning[:200]}",
        f"📰 {signal.get('source', '?')} | {str(signal.get('published', ''))[:16]}",
    ]
    if signal.get("link"):
        lines.append(f"🔗 {signal['link']}")
    return "\n".join(lines)


# ─── Main scan ────────────────────────────────────────────────────────────────

def scan() -> int:
    seen = _load_seen()
    new_hashes: set[str] = set()
    new_signals = 0
    ai_used = "Claude" if ANTHROPIC_KEY else ("Groq" if GROQ_KEY else "Fallback")
    log.info("AI backend: %s", ai_used)

    # Collect all items from all sources
    all_items: list[dict] = []

    log.info("=== Truth Social ===")
    ts_items = _fetch_truthsocial()
    all_items.extend(ts_items)
    if not ts_items:
        log.warning("Truth Social returned 0 posts — likely 403 from cloud IP. Using RSS only.")

    log.info("=== RSS Sources ===")
    for src in RSS_SOURCES:
        items = _fetch_rss(src["url"], src["name"])
        log.info("  %s: %d items", src["name"], len(items))
        # For RSS, only keep Trump-related items
        filtered = [i for i in items if "trump" in i["full_text"].lower()]
        all_items.extend(filtered)

    log.info("Total items to process: %d", len(all_items))

    for item in all_items:
        h = _item_hash(item)
        if h in seen:
            continue
        new_hashes.add(h)

        # Analyze with AI — ALL posts go through analysis
        analysis = _analyze(item["full_text"])

        signal = {
            "id": h,
            "source": item["source"],
            "title": item["title"],
            "full_text": item.get("full_text", ""),
            "link": item.get("link", ""),
            "published": item.get("published", ""),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "is_repost": item.get("is_repost", False),
            "engagement": {
                "replies": item.get("replies", 0),
                "reposts": item.get("reposts", 0),
                "likes": item.get("likes", 0),
            },
            "analysis": analysis,
            # Top-level shortcuts for the API/frontend
            "market_relevant": analysis.get("market_relevant", False),
            "tickers": analysis.get("tickers", []),
            "sectors": analysis.get("sectors", []),
            "signal_type": analysis.get("signal_type", "NEUTRAL"),
            "signal_strength": analysis.get("signal_strength", "LOW"),
            "sentiment": analysis.get("sentiment", "NEUTRAL"),
        }

        _save_signal(signal)
        new_signals += 1

        # Telegram only for market-relevant HIGH/MEDIUM signals
        if analysis.get("market_relevant") and analysis.get("signal_strength") in ("HIGH", "MEDIUM"):
            _send_telegram(_format_alert(signal))
            time.sleep(0.5)

        log.info(
            "  [%s] market=%s type=%s tickers=%s | %s",
            item["source"][:20],
            analysis.get("market_relevant"),
            analysis.get("signal_type"),
            analysis.get("tickers", []),
            item["title"][:60],
        )
        time.sleep(0.3)  # rate limit AI calls

    _save_seen(new_hashes)
    log.info("Scan complete — %d new signals (%d total sources)", new_signals, len(all_items))
    return new_signals


def print_recent(n: int = 15) -> None:
    signals = _load_signals()
    if not signals:
        print("No signals yet.")
        return
    print(f"\n{'='*70}\nTRUMP SIGNALS — last {min(n, len(signals))}\n{'='*70}")
    for s in signals[:n]:
        relevant = "🟢" if s.get("market_relevant") else "⚪"
        tks = " ".join("$" + t for t in s.get("tickers", [])[:4]) or s.get("sectors", ["?"])[0] if s.get("sectors") else ""
        dt = str(s.get("published", "?"))[:16]
        print(f"  {relevant} [{dt}] {s.get('signal_type','?')} {tks}")
        print(f"     {s.get('title','')[:90]}")
        if s.get("analysis", {}).get("reasoning"):
            print(f"     → {s['analysis']['reasoning'][:80]}")
        print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        print_recent(20)
    else:
        count = scan()
        print(f"\nDone — {count} new signals.")
        if count > 0:
            print_recent(min(count, 10))
