#!/usr/bin/env python3
"""
TELEGRAM DAILY BRIEFING — compact ~8-line morning summary
Runs after the full pipeline. Sends one clean message with the key signals.
"""
import os
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, date

DOCS = Path(__file__).parent / 'docs'
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID', '')


def send(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print('No Telegram credentials — printing only:\n')
        print(text)
        return
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    resp = requests.post(url, data={
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': 'true',
    }, timeout=15)
    if resp.ok:
        print('Briefing sent OK')
    else:
        print(f'Telegram error: {resp.status_code} {resp.text}')


def _regime() -> str:
    try:
        mr_path = DOCS / 'macro_radar.json'
        with open(mr_path) as f:
            d = json.load(f)
        regime = d.get('regime', {}).get('name') or d.get('regime_name', '?')
        score  = d.get('composite_score') or d.get('composite', {}).get('score', '?')
        color  = {'CALM': '🟢', 'ALERT': '🟡', 'CRISIS': '🔴'}.get(str(regime).upper(), '⚪')
        return f"{color} Macro: <b>{regime}</b> (score {score})"
    except Exception:
        return '⚪ Macro: sin datos'


def _portfolio() -> str:
    try:
        sp_path = DOCS / 'smart_portfolio.json'
        with open(sp_path) as f:
            d = json.load(f)
        picks   = d.get('total_picks', 0)
        invested = d.get('invested_pct', 0)
        cash    = d.get('cash_pct', 0)
        tickers = ', '.join(p['ticker'] for p in d.get('picks', [])[:5])
        return (
            f"💼 Portfolio: <b>{picks} picks</b> ({invested:.0f}% inv · {cash:.0f}% cash)\n"
            f"   {tickers}"
        )
    except Exception:
        return '💼 Portfolio: sin datos'


def _value_count() -> str:
    try:
        df = pd.read_csv(DOCS / 'value_opportunities_filtered.csv')
        total = len(df)
        if 'conviction_grade' in df.columns:
            ab = len(df[df['conviction_grade'].isin(['A+', 'A', 'B'])])
            return f"💎 VALUE filtrado: <b>{total} oportunidades</b> ({ab} grado A/B)"
        return f"💎 VALUE filtrado: <b>{total} oportunidades</b>"
    except Exception:
        return '💎 VALUE: sin datos'


def _earnings_soon() -> str:
    try:
        df = pd.read_csv(DOCS / 'value_opportunities_filtered.csv')
        if 'days_to_earnings' not in df.columns:
            return ''
        soon = df[df['days_to_earnings'].between(1, 10, inclusive='both')]
        if soon.empty:
            return ''
        tickers = ', '.join(soon['ticker'].tolist()[:4])
        return f"⚠️ Earnings <10d: {tickers}"
    except Exception:
        return ''


def _insiders() -> str:
    try:
        df = pd.read_csv(DOCS / 'recurring_insiders.csv')
        n = len(df)
        if n == 0:
            return ''
        top = ', '.join(df.head(3)['ticker'].tolist())
        return f"🐋 Insiders recurrentes: <b>{n}</b> ({top}...)"
    except Exception:
        return ''


def main() -> None:
    today = date.today().strftime('%d %b %Y')
    lines = [f"<b>📊 Briefing diario — {today}</b>", '']

    lines.append(_regime())
    lines.append(_portfolio())
    lines.append(_value_count())

    earnings = _earnings_soon()
    if earnings:
        lines.append(earnings)

    insiders = _insiders()
    if insiders:
        lines.append(insiders)

    lines.append('')
    lines.append('<i>Stock Analyzer · pipeline automatizado</i>')

    send('\n'.join(lines))


if __name__ == '__main__':
    main()
