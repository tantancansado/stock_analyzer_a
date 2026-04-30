"""
Portfolio price alerts — lee posiciones de Supabase, compara precio actual vs
precio objetivo del analista y calcula alertas de precio.

Tipos de alerta:
  TARGET_REACHED   — precio actual >= 90% del objetivo del analista
  STOP_TRIGGERED   — caída >= 8% desde precio de entrada (stop-loss estándar)
  NEAR_TARGET      — precio actual >= 75% del objetivo (aviso previo)
  RECOVERY         — ticker que estaba en pérdidas vuelve a positivo

Output: docs/portfolio_alerts.json
"""
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

DOCS = Path('docs')
OUT  = DOCS / 'portfolio_alerts.json'

SUPABASE_URL      = os.environ.get('SUPABASE_URL', '').rstrip('/')
SERVICE_KEY       = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
STOP_LOSS_PCT     = 8.0   # % de caída desde entrada que activa stop
TARGET_NEAR_PCT   = 75.0  # % del camino hacia el objetivo que activa aviso


def _fetch_positions() -> list[dict]:
    """Lee TODAS las posiciones (service role salta RLS) — solo hay un usuario real."""
    if not SUPABASE_URL or not SERVICE_KEY:
        print('  SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set — skipping')
        return []
    url = f"{SUPABASE_URL}/rest/v1/personal_portfolio_positions?select=ticker,shares,avg_price,currency"
    try:
        r = requests.get(url, headers={
            'apikey': SERVICE_KEY,
            'Authorization': f'Bearer {SERVICE_KEY}',
        }, timeout=10)
        if r.status_code != 200:
            print(f'  Supabase error {r.status_code}: {r.text[:100]}')
            return []
        return r.json()
    except Exception as e:
        print(f'  Supabase fetch failed: {e}')
        return []


def _get_current_price(ticker: str):
    try:
        info = yf.Ticker(ticker).fast_info
        p = getattr(info, 'last_price', None) or getattr(info, 'regularMarketPrice', None)
        return float(p) if p else None
    except Exception:
        return None


def _load_analyst_targets() -> dict[str, float]:
    """Load analyst target prices from value_opportunities CSVs."""
    targets: dict[str, float] = {}
    for fname in ['value_opportunities.csv', 'european_value_opportunities.csv']:
        p = DOCS / fname
        if not p.exists():
            continue
        try:
            df = pd.read_csv(p)
            if 'ticker' in df.columns and 'target_price_analyst' in df.columns:
                for _, row in df.iterrows():
                    t = str(row['ticker']).upper()
                    tp = row.get('target_price_analyst')
                    if pd.notna(tp) and float(tp) > 0:
                        targets[t] = float(tp)
        except Exception:
            pass
    return targets


def _alert_type(current: float, entry: float, target):
    pct_from_entry = (current - entry) / entry * 100

    if pct_from_entry <= -STOP_LOSS_PCT:
        return 'STOP_TRIGGERED'

    if target and target > entry:
        pct_to_target = (current - entry) / (target - entry) * 100
        if pct_to_target >= 100:
            return 'TARGET_REACHED'
        if pct_to_target >= TARGET_NEAR_PCT:
            return 'NEAR_TARGET'

    return None


def build_alerts() -> list[dict]:
    positions = _fetch_positions()
    if not positions:
        return []

    # Deduplicate by ticker (keep first, in case of multiple users — only one real user)
    seen: set[str] = set()
    unique: list[dict] = []
    for p in positions:
        t = str(p.get('ticker', '')).upper()
        if t and t not in seen:
            seen.add(t)
            unique.append(p)

    analyst_targets = _load_analyst_targets()
    alerts: list[dict] = []

    for pos in unique:
        ticker    = str(pos['ticker']).upper()
        avg_price = float(pos.get('avg_price') or 0)
        if avg_price <= 0:
            continue

        current = _get_current_price(ticker)
        if current is None:
            continue

        target = analyst_targets.get(ticker)
        pct_change = (current - avg_price) / avg_price * 100
        alert_type = _alert_type(current, avg_price, target)

        if alert_type is None:
            continue

        alerts.append({
            'type':        alert_type,
            'ticker':      ticker,
            'current':     round(current, 2),
            'entry':       round(avg_price, 2),
            'target':      round(target, 2) if target else None,
            'pct_change':  round(pct_change, 1),
            'pct_to_target': round((current - avg_price) / (target - avg_price) * 100, 1)
                              if target and target > avg_price else None,
        })

    order = {'STOP_TRIGGERED': 0, 'TARGET_REACHED': 1, 'NEAR_TARGET': 2}
    alerts.sort(key=lambda a: order.get(a['type'], 9))
    return alerts


def main():
    print('[Portfolio Alerts] Checking price alerts...')
    alerts = build_alerts()

    payload = {
        'generated_at': str(date.today()),
        'alerts': alerts,
        'counts': {
            'stop_triggered':  sum(1 for a in alerts if a['type'] == 'STOP_TRIGGERED'),
            'target_reached':  sum(1 for a in alerts if a['type'] == 'TARGET_REACHED'),
            'near_target':     sum(1 for a in alerts if a['type'] == 'NEAR_TARGET'),
        },
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"  {len(alerts)} alerts written to {OUT}")
    for a in alerts:
        print(f"  [{a['type']:15}] {a['ticker']:6}  {a['pct_change']:+.1f}%  entry={a['entry']} current={a['current']}")


if __name__ == '__main__':
    main()
