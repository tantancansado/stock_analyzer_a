#!/usr/bin/env python3
"""
NEW VALUE ALERTS — Telegram alert for NEW high-score tickers
Compares today's value_opportunities.csv vs yesterday's archive.
Sends alert only for tickers that are NEW (not in yesterday) with grade A/B.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DOCS = Path('docs')
HISTORY = DOCS / 'history'

SCORE_THRESHOLD = 55   # minimum value_score to be considered "high quality"
MAX_ALERTS = 8         # max tickers to include in one message


def _send_telegram(text: str) -> bool:
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id   = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not bot_token or not chat_id:
        print("  Telegram: no credentials configured, skipping")
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = json.dumps({
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"  Telegram send failed: {e}")
        return False


def _load_value_csv(path: Path) -> set:
    """Load a value_opportunities.csv and return set of high-score tickers."""
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path)
        if 'value_score' not in df.columns or 'ticker' not in df.columns:
            return set()
        return set(df[df['value_score'] >= SCORE_THRESHOLD]['ticker'].tolist())
    except Exception:
        return set()


def _load_value_df(path: Path) -> pd.DataFrame:
    """Load value_opportunities.csv as DataFrame."""
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def run_new_value_alerts():
    print("=== NEW VALUE ALERTS ===")
    today = datetime.now().strftime('%Y-%m-%d')

    # ── Load today's data ────────────────────────────────────────────────
    today_path = DOCS / 'value_opportunities.csv'
    today_df = _load_value_df(today_path)
    if today_df.empty:
        print("No value_opportunities.csv found, skipping")
        return

    today_quality = today_df[today_df.get('value_score', pd.Series()).ge(SCORE_THRESHOLD)].copy() \
        if 'value_score' in today_df.columns else pd.DataFrame()

    if today_quality.empty:
        print(f"No tickers with value_score >= {SCORE_THRESHOLD} today")
        return

    today_tickers = set(today_quality['ticker'].tolist())

    # ── Load yesterday's data from history ───────────────────────────────
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    # Try yesterday, then 2 days ago (weekend fallback)
    yesterday_tickers = set()
    for delta in [1, 2, 3]:
        candidate = (datetime.now() - timedelta(days=delta)).strftime('%Y-%m-%d')
        hist_path = HISTORY / candidate / 'value_opportunities.csv'
        yesterday_tickers = _load_value_csv(hist_path)
        if yesterday_tickers:
            print(f"  Comparing vs {candidate} ({len(yesterday_tickers)} tickers)")
            break

    if not yesterday_tickers:
        print("  No historical data found for comparison — sending full top list instead")

    # ── Find NEW tickers ─────────────────────────────────────────────────
    new_tickers = today_tickers - yesterday_tickers
    print(f"  Today: {len(today_tickers)} quality picks | New: {len(new_tickers)}")

    if not new_tickers:
        print("  No new tickers vs yesterday — nothing to alert")
        return

    # ── Build message ────────────────────────────────────────────────────
    # Filter today_df to only new tickers, sorted by value_score desc
    new_df = today_quality[today_quality['ticker'].isin(new_tickers)].copy()
    new_df = new_df.sort_values('value_score', ascending=False).head(MAX_ALERTS)

    def sf(val, default=None):
        if val is None:
            return default
        try:
            f = float(val)
            return None if (f != f) else f  # NaN check
        except Exception:
            return default

    lines = []
    for _, row in new_df.iterrows():
        ticker  = str(row.get('ticker', ''))
        company = str(row.get('company_name', ticker))[:28]
        score   = sf(row.get('value_score'), 0)
        sector  = str(row.get('sector', ''))[:20]
        price   = sf(row.get('current_price'))
        upside  = sf(row.get('analyst_upside_pct'))
        fcf     = sf(row.get('fcf_yield_pct'))
        warn    = bool(row.get('earnings_warning', False))
        earn_d  = str(row.get('earnings_date', '')) or ''

        score_emoji = '⭐⭐⭐' if score >= 70 else ('⭐⭐' if score >= 60 else '⭐')

        extras = []
        if upside and upside > 0:
            extras.append(f"🎯 +{upside:.0f}%")
        if fcf and fcf >= 5:
            extras.append(f"FCF {fcf:.1f}%")
        if warn and earn_d:
            extras.append(f"⚠️ Earn {earn_d}")

        price_str = f" @ ${price:.2f}" if price else ""
        extras_str = "  " + " | ".join(extras) if extras else ""

        lines.append(
            f"{score_emoji} <b>{ticker}</b>{price_str} — {company}\n"
            f"   Score: <b>{score:.1f}</b> | {sector}{extras_str}"
        )

    header = (
        f"🆕 <b>Nuevas Oportunidades VALUE</b>\n"
        f"📅 {today} — {len(new_tickers)} ticker{'s' if len(new_tickers) != 1 else ''} nuevo{'s' if len(new_tickers) != 1 else ''}\n\n"
    )

    body = '\n\n'.join(lines)

    footer = (
        f"\n\n🔗 <a href=\"https://tantancansado.github.io/stock_analyzer_a/app/#/value-us\">Ver VALUE US</a>"
        f"\n<i>Solo para fines educativos, no consejo financiero.</i>"
    )

    message = header + body + footer

    if _send_telegram(message):
        print(f"  Telegram: alert sent for {len(new_df)} new tickers")
    else:
        print("  Preview of message that would be sent:")
        print(message[:500])


if __name__ == '__main__':
    run_new_value_alerts()
