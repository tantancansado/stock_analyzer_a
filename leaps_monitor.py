#!/usr/bin/env python3
"""
LEAPS MONITOR — vigila las posiciones LEAPS guardadas y avisa por Telegram.

Lee las opciones del usuario de Supabase (personal_portfolio_positions con
asset_type='option', option_type='call') y, para cada LEAPS:
  - precio actual de la opción (cadena en vivo) y P&L vs prima pagada
  - días a vencimiento, break-even, tesis (target del analista vs break-even)
  - señales de acción y las manda a Telegram (con dedup para no repetir)

Alertas:
  🟢 TAKE-PROFIT   P&L >= +{TAKE_PROFIT_PCT}%   → asegura parte
  🔴 STOP / REVISAR P&L <= {STOP_PCT}%          → reevalúa la tesis
  🟡 ROLAR         quedan < {ROLL_DTE}d         → rola antes de que el valor temporal se acelere
  🔴 TESIS ROTA    target <= break-even, o deterioro fundamental

Escribe docs/leaps_positions_status.json para que el frontend muestre el estado.

Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_MONITOR_USER_ID (opcional),
     TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import html
import json
import os
import urllib.request
from datetime import date, datetime
from pathlib import Path

import leaps_analyzer as la

DOCS = Path('docs')
STATUS_OUT = DOCS / 'leaps_positions_status.json'
SENT_LOG = DOCS / '.leaps_alerts_sent.json'

ROLL_DTE        = 270     # < 9 meses → conviene rolar
TAKE_PROFIT_PCT = 50.0
STOP_PCT        = -40.0
DEDUP_DAYS      = 5
FUND_COLLAPSE   = 45.0    # fundamental_score por debajo → deterioro
DELTA_FLOOR     = 0.65    # delta por debajo → ya no es stock-replacement,
                          # es apuesta direccional (el subyacente cayó hacia
                          # el strike); decide: añadir, rolar de strike o cerrar

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID', '')


# ── Supabase ──────────────────────────────────────────────────────────────────

def load_option_positions() -> list[dict]:
    """Lee las posiciones de opciones (calls) del usuario desde Supabase."""
    from supabase_positions import fetch_position_rows
    cols = 'ticker,shares,avg_price,asset_type,option_type,option_strike,option_expiry'
    rows = fetch_position_rows(cols, extra_filter='&asset_type=eq.option')
    if rows is None:
        print('  Supabase no configurado / no responde — nada que vigilar')
        return []
    out = []
    for r in rows:
        if (r.get('option_type') or '').lower() != 'call':
            continue
        if not r.get('ticker') or not r.get('option_strike') or not r.get('option_expiry'):
            continue
        out.append({
            'ticker': str(r['ticker']).upper(),
            'strike': float(r['option_strike']),
            'expiry': str(r['option_expiry'])[:10],
            'contracts': float(r.get('shares') or 1),
            'avg_price': float(r['avg_price']) if r.get('avg_price') else None,
        })
    print(f'  Supabase: {len(out)} posiciones LEAPS (call) cargadas')
    return out


# ── Precio en vivo del contrato ──────────────────────────────────────────────

def current_option_price(ticker: str, strike: float, expiry: str):
    """Devuelve (mid, bid, ask, last, iv) del contrato concreto, o (None,...)."""
    import yfinance as yf
    try:
        t = yf.Ticker(ticker)
        chain = la._fetch_with_retry(lambda: t.option_chain(expiry))
        if chain is None or chain.calls is None or chain.calls.empty:
            return None, None, None, None, None
        row = chain.calls[chain.calls['strike'] == strike]
        if row.empty:
            return None, None, None, None, None
        r = row.iloc[0]
        bid = float(r['bid'] or 0); ask = float(r['ask'] or 0); last = float(r['lastPrice'] or 0)
        mid = (bid + ask) / 2 if (bid > 0 and ask > 0) else last
        iv = float(r.get('impliedVolatility', 0) or 0) or None
        return mid, bid, ask, last, iv
    except Exception as e:
        print(f'    {ticker}: error precio opción — {e}')
        return None, None, None, None, None


# ── Análisis de una posición ─────────────────────────────────────────────────

def analyze_position(pos: dict, signals: dict) -> dict:
    import yfinance as yf
    t = yf.Ticker(pos['ticker'])
    spot = la._get_spot(t)
    mid, bid, ask, last, iv = current_option_price(pos['ticker'], pos['strike'], pos['expiry'])
    dte = (datetime.strptime(pos['expiry'], '%Y-%m-%d').date() - date.today()).days

    # Delta actual: si cayó bajo DELTA_FLOOR ya no replica la acción
    delta = None
    if spot and iv and dte > 0:
        try:
            delta = la.bs_call_delta(spot, pos['strike'], dte / 365.0,
                                     la.FALLBACK_RF, iv,
                                     la._get_dividend_yield(t))
        except Exception:
            delta = None
    avg = pos['avg_price']
    pnl_pct = ((mid - avg) / avg * 100) if (mid and avg) else None
    breakeven = pos['strike'] + avg if avg else None
    sig = signals.get(pos['ticker'], {})
    target = la._get_analyst_target(t, sig)
    fund = sig.get('fundamental_score')
    fund_ok = not (fund is not None and fund != 50.0 and fund < FUND_COLLAPSE)

    alerts = []
    if pnl_pct is not None and pnl_pct >= TAKE_PROFIT_PCT:
        alerts.append(('TAKE_PROFIT', f'+{pnl_pct:.0f}% de ganancia — considera asegurar parte'))
    if pnl_pct is not None and pnl_pct <= STOP_PCT:
        alerts.append(('STOP', f'{pnl_pct:.0f}% — pérdida grande, reevalúa la tesis'))
    if 0 <= dte < ROLL_DTE:
        alerts.append(('ROLL', f'quedan {dte}d (<9 meses) — rola a un vencimiento más largo antes de que el valor temporal se acelere'))
    if breakeven and target and target <= breakeven:
        alerts.append(('THESIS_BREAK', f'el target del analista (${target:.0f}) ya no supera tu break-even (${breakeven:.2f}) — sin recorrido'))
    if not fund_ok:
        alerts.append(('THESIS_BREAK', f'fundamental_score se ha deteriorado a {fund:.0f} — vigila el negocio'))
    if delta is not None and delta < DELTA_FLOOR:
        alerts.append(('DELTA_DRIFT',
                       f'delta {delta:.2f} < {DELTA_FLOOR} — el LEAPS ya no replica la acción, '
                       f'es apuesta direccional: añade, rola de strike o cierra'))

    return {
        'ticker': pos['ticker'], 'strike': pos['strike'], 'expiry': pos['expiry'],
        'contracts': pos['contracts'], 'avg_price': avg,
        'spot': round(spot, 2) if spot else None,
        'current_price': round(mid, 2) if mid else None,
        'pnl_pct': round(pnl_pct, 1) if pnl_pct is not None else None,
        'delta': round(delta, 3) if delta is not None else None,
        'dte': dte, 'breakeven': round(breakeven, 2) if breakeven else None,
        'analyst_target': round(target, 2) if target else None,
        'alerts': alerts,
    }


# ── Telegram + dedup ─────────────────────────────────────────────────────────

def _load_sent() -> dict:
    try:
        return json.loads(SENT_LOG.read_text()) if SENT_LOG.exists() else {}
    except Exception:
        return {}


def _save_sent(d: dict) -> None:
    try:
        SENT_LOG.write_text(json.dumps(d, indent=2))
    except Exception as e:
        print(f'  no se pudo guardar el log de alertas: {e}')


def _send_telegram(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print('  Sin credenciales Telegram — dry run:\n' + text)
        return
    import requests
    try:
        r = requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML',
                  'disable_web_page_preview': 'true'}, timeout=10)
        if r.ok:
            print('  Telegram enviado')
        else:
            print(f'  Telegram falló: {r.status_code} {r.text}')
    except Exception as e:
        print(f'  Telegram falló: {e}')


EMOJI = {'TAKE_PROFIT': '🟢', 'STOP': '🔴', 'ROLL': '🟡', 'THESIS_BREAK': '🔴'}


def main():
    print('=' * 60)
    print('LEAPS MONITOR — seguimiento de posiciones')
    print(f'  {datetime.now():%Y-%m-%d %H:%M}')
    print('=' * 60)

    positions = load_option_positions()
    if not positions:
        STATUS_OUT.write_text(json.dumps(
            {'generated_at': datetime.now().isoformat(), 'positions': []}, indent=2))
        return

    signals = la.load_app_signals()
    sent = _load_sent()
    today = date.today().isoformat()
    statuses, fresh_alerts = [], []

    for pos in positions:
        st = analyze_position(pos, signals)
        statuses.append(st)
        tag = f"{st['ticker']}-{st['strike']:.0f}-{st['expiry']}"
        for atype, msg in st['alerts']:
            key = f"{tag}:{atype}"
            last_sent = sent.get(key)
            if last_sent and (date.today() - date.fromisoformat(last_sent)).days < DEDUP_DAYS:
                continue                      # ya avisado hace poco
            fresh_alerts.append((st, atype, msg))
            sent[key] = today

    if fresh_alerts:
        lines = ['<b>🚀 LEAPS — alertas de seguimiento</b>', '']
        for st, atype, msg in fresh_alerts:
            head = f"{EMOJI.get(atype, '•')} <b>{html.escape(st['ticker'])} ${st['strike']:.0f} {st['expiry']}</b>"
            pnl = f" · P&amp;L {st['pnl_pct']:+.0f}%" if st['pnl_pct'] is not None else ''
            lines.append(f"{head}{pnl}")
            lines.append(f"   {html.escape(msg)}")
            lines.append('')
        _send_telegram('\n'.join(lines).strip())
        _save_sent(sent)
    else:
        print('  Sin alertas nuevas')

    STATUS_OUT.write_text(json.dumps(
        {'generated_at': datetime.now().isoformat(), 'positions': statuses},
        indent=2, ensure_ascii=False, default=str))
    print(f'  {len(statuses)} posiciones · {len(fresh_alerts)} alertas nuevas → {STATUS_OUT}')


if __name__ == '__main__':
    main()
