#!/usr/bin/env python3
"""
check_alerts.py — Daily alert checker
Reads price_alerts from Supabase, checks conditions via yfinance, sends emails via Resend.
Runs as part of the daily pipeline (~8:30 AM Spain time via GitHub Actions).

Required GitHub secrets:
  RESEND_API_KEY          — Resend API key
  SUPABASE_URL            — https://<project>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY — service role key (bypasses RLS)
"""

import os
import requests
import yfinance as yf
from datetime import datetime, date

# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL      = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY      = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
RESEND_API_KEY    = os.environ.get('RESEND_API_KEY', '')
FROM_EMAIL        = 'Stock Analyzer <onboarding@resend.dev>'  # Change to verified domain when available

# ── Supabase REST helpers ─────────────────────────────────────────────────────

def _sb_headers():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }

def sb_select(table: str, filters: str = '') -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filters}"
    r = requests.get(url, headers=_sb_headers(), timeout=15)
    r.raise_for_status()
    return r.json()

def sb_patch(table: str, match_col: str, match_val: str, data: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    requests.patch(url, headers=_sb_headers(), json=data, timeout=10)

# ── Price data ────────────────────────────────────────────────────────────────

def get_price_data(ticker: str) -> dict:
    """Returns current_price, pct_change_today, earnings_date (date|None)."""
    try:
        info = yf.Ticker(ticker).info
        current   = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        prev      = info.get('previousClose') or current
        pct       = ((current - prev) / prev * 100) if prev else 0
        earnings_ts = info.get('earningsTimestamp') or info.get('earningsTimestampStart')
        earnings_dt = date.fromtimestamp(earnings_ts) if earnings_ts else None
        return {'current': current, 'pct': pct, 'earnings': earnings_dt}
    except Exception as e:
        print(f"  ⚠️  yfinance error for {ticker}: {e}")
        return {}

# ── Condition evaluation ──────────────────────────────────────────────────────

def evaluate(alert: dict, data: dict) -> tuple[bool, str]:
    """Returns (triggered, human_reason)."""
    if not data:
        return False, ''

    t         = alert['ticker']
    threshold = alert.get('threshold')
    current   = data.get('current', 0)
    pct       = data.get('pct', 0)
    earnings  = data.get('earnings')

    match alert['alert_type']:
        case 'price_below':
            if threshold and current and current < threshold:
                return True, f"{t} cotiza a ${current:.2f}, por debajo de tu umbral de ${threshold:.2f}"
        case 'price_above':
            if threshold and current and current > threshold:
                return True, f"{t} cotiza a ${current:.2f}, por encima de tu umbral de ${threshold:.2f}"
        case 'drop_pct':
            if threshold and pct <= -abs(threshold):
                return True, f"{t} ha caído un {abs(pct):.1f}% hoy (umbral: -{abs(threshold):.1f}%)"
        case 'earnings_soon':
            if earnings:
                days = (earnings - date.today()).days
                if 0 <= days <= 7:
                    return True, f"{t} tiene earnings el {earnings.strftime('%d/%m/%Y')} — faltan {days} días"

    return False, ''

# ── Email ─────────────────────────────────────────────────────────────────────

TYPE_EMOJI = {
    'price_below': '📉',
    'price_above': '📈',
    'drop_pct':    '⚠️',
    'earnings_soon': '📅',
}

def send_email(to: str, ticker: str, reason: str, current: float, alert_type: str) -> bool:
    if not RESEND_API_KEY:
        print(f"  ⚠️  RESEND_API_KEY not set — would send: {reason}")
        return False

    emoji   = TYPE_EMOJI.get(alert_type, '🔔')
    subject = f"[Stock Analyzer] {emoji} {ticker} — alerta activada"

    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0f1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:520px;margin:40px auto;padding:0 16px;">
    <div style="background:#1a1d2e;border:1px solid #2d3748;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:24px 28px;">
        <h1 style="margin:0;font-size:20px;font-weight:800;color:#fff;">📊 Stock Analyzer</h1>
        <p style="margin:4px 0 0;font-size:13px;color:rgba(255,255,255,.7);">Alerta activada — {ticker}</p>
      </div>
      <div style="padding:28px;">
        <div style="display:inline-block;padding:4px 12px;background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.3);border-radius:6px;font-size:12px;color:#818cf8;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px;">
          {ticker}
        </div>
        <p style="font-size:16px;font-weight:600;color:#e2e8f0;margin:0 0 8px;">{emoji} {reason}</p>
        <p style="font-size:13px;color:#94a3b8;margin:0 0 24px;">
          Precio actual: <strong style="color:#e2e8f0;">${current:.2f}</strong>
        </p>
        <a href="https://tantancansado.github.io/stock_analyzer_a/app/"
           style="display:inline-block;padding:10px 20px;background:#6366f1;color:#fff;text-decoration:none;border-radius:8px;font-size:13px;font-weight:600;">
          Ver en Stock Analyzer →
        </a>
      </div>
      <div style="padding:16px 28px;border-top:1px solid #2d3748;">
        <p style="margin:0;font-size:11px;color:#4a5568;">
          Gestionado desde Stock Analyzer · Puedes desactivar la alerta en la app
        </p>
      </div>
    </div>
  </div>
</body>
</html>"""

    try:
        r = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {RESEND_API_KEY}', 'Content-Type': 'application/json'},
            json={'from': FROM_EMAIL, 'to': [to], 'subject': subject, 'html': html},
            timeout=10,
        )
        if r.status_code in (200, 201):
            print(f"  ✅ Email sent to {to}")
            return True
        print(f"  ❌ Resend {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"  ❌ Email exception: {e}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🔔 check_alerts.py — starting")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY — skipping")
        return

    # Load active alerts
    alerts = sb_select('price_alerts', 'active=eq.true&select=*')
    print(f"   {len(alerts)} active alert(s) found")
    if not alerts:
        return

    # Batch-fetch price data per unique ticker
    tickers = list({a['ticker'] for a in alerts})
    price_data = {}
    for t in tickers:
        print(f"   Fetching {t}...")
        price_data[t] = get_price_data(t)

    # Evaluate each alert
    fired = 0
    for alert in alerts:
        ticker = alert['ticker']
        data   = price_data.get(ticker, {})
        triggered, reason = evaluate(alert, data)

        if not triggered:
            print(f"   ✓ {ticker} ({alert['alert_type']}) — not triggered (price={data.get('current', '?')})")
            continue

        print(f"   🚨 TRIGGERED: {ticker} ({alert['alert_type']}) → {alert['email']}")
        sent = send_email(
            to=alert['email'],
            ticker=ticker,
            reason=reason,
            current=data.get('current', 0),
            alert_type=alert['alert_type'],
        )
        if sent:
            sb_patch('price_alerts', 'id', alert['id'], {
                'last_fired': datetime.utcnow().isoformat() + 'Z'
            })
            fired += 1

    print(f"\n✅ Done — {fired} alert(s) fired")

if __name__ == '__main__':
    main()
