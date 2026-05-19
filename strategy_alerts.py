#!/usr/bin/env python3
"""
Strategy Alerts — vigila docs/portfolio_strategies.json y dispara avisos
Telegram cuando el precio actual cruza un trim_at_price o add_at_price.

Diseño: idempotente. Cada (ticker, level_type, scan_date) se marca como
"seen" para no enviar el mismo aviso dos veces el mismo día. Si el precio
vuelve a cruzar al día siguiente con un nuevo plan, sí avisa de nuevo.

EXECUTION HOOK (deshabilitado por defecto):
Hay un punto de extensión _maybe_execute_order(...) que el día de mañana
puede llamar a IBKR. Por ahora siempre devuelve False. La señal solo
viaja por Telegram.

Ejecutar: python3 strategy_alerts.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DOCS = Path('docs')
SEEN_PATH = DOCS / '.strategy_alerts_seen.json'

# ── Feature flag para ejecución automática (mantener False) ──────────────────
EXECUTE_ORDERS = os.environ.get('STRATEGY_AUTO_EXECUTE', '').lower() == 'true'


def _load_seen() -> dict:
    if not SEEN_PATH.exists():
        return {}
    try:
        return json.loads(SEEN_PATH.read_text())
    except Exception:
        return {}


def _save_seen(seen: dict) -> None:
    # Mantener máximo 200 entradas (rolling window de ~30 días)
    if len(seen) > 200:
        items = sorted(seen.items(), key=lambda kv: kv[1])
        seen = dict(items[-100:])
    SEEN_PATH.write_text(json.dumps(seen, indent=2))


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _maybe_execute_order(ticker: str, action: str, price: float, qty_pct: float) -> bool:
    """
    Hook preparado para ejecución automática vía IBKR (u otro broker).

    Por ahora siempre devuelve False — solo envía Telegram. Cuando el usuario
    valide que el sistema da señales fiables, se conecta aquí ib_insync u
    otro cliente.

    Args:
        ticker: símbolo
        action: 'TRIM' | 'ADD'
        price: límite a usar en la orden
        qty_pct: % de la posición sobre la cual operar

    Returns:
        True si se ejecutó orden, False si solo notificación.
    """
    if not EXECUTE_ORDERS:
        return False
    # FUTURE: integrar ib_insync. Algo como:
    #   from ib_insync import IB, Stock, LimitOrder
    #   ib = IB(); ib.connect('127.0.0.1', 7497, clientId=1)
    #   contract = Stock(ticker, 'SMART', 'USD')
    #   side = 'SELL' if action == 'TRIM' else 'BUY'
    #   shares = compute_shares_from_pct(ticker, qty_pct)
    #   order = LimitOrder(side, shares, price)
    #   ib.placeOrder(contract, order)
    return False


def _format_alert(ticker: str, strategy: dict, level_type: str, current_price: float) -> str:
    company = strategy.get('company') or ticker
    avg = strategy.get('avg_price')
    pl_pct = strategy.get('pl_pct')

    if level_type == 'TRIM':
        target = strategy.get('trim_at_price')
        pct = strategy.get('trim_pct') or 0
        reason = strategy.get('trim_reason') or '-'
        emoji = '🟢'
        verb = 'TRIM'
        if target is None:
            return ''
        action_msg = f'Vender {pct:.0f}% a ${target:.2f} (precio actual ${current_price:.2f})'
    else:  # ADD
        target = strategy.get('add_at_price')
        pct = strategy.get('add_pct') or 0
        reason = strategy.get('add_reason') or '-'
        emoji = '🔵'
        verb = 'ADD'
        if target is None:
            return ''
        action_msg = f'Comprar +{pct:.0f}% a ${target:.2f} (precio actual ${current_price:.2f})'

    lines = [
        f'{emoji} <b>{verb}: {ticker}</b> <i>({company})</i>',
        '',
        action_msg,
        f'<i>{reason}</i>',
        '',
    ]
    if avg is not None and pl_pct is not None:
        lines.append(f'P&L abierto: {pl_pct:+.1f}% (avg ${avg:.2f})')

    triggers = strategy.get('triggers_sell') if level_type == 'TRIM' else strategy.get('triggers_buy')
    if triggers:
        lines.append('')
        lines.append('<b>Triggers</b>:')
        for t in triggers[:3]:
            lines.append(f'• {t}')

    stop = strategy.get('stop_loss_price')
    if stop:
        lines.append('')
        lines.append(f'Stop loss: ${stop:.2f}')

    return '\n'.join(lines)


def _send_telegram(text: str) -> bool:
    bot = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not bot or not chat:
        print('  TELEGRAM_BOT_TOKEN/CHAT_ID no configurado — skip')
        return False
    try:
        import requests
        resp = requests.post(
            f'https://api.telegram.org/bot{bot}/sendMessage',
            json={
                'chat_id': chat,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        print(f'  Telegram error {resp.status_code}: {resp.text[:120]}')
    except Exception as exc:
        print(f'  Telegram failed: {exc}')
    return False


def _level_crossed(level_type: str, target: float, current: float) -> bool:
    """
    TRIM: alerta cuando current >= target (tocamos el nivel para vender)
    ADD:  alerta cuando current <= target (tocamos el nivel para comprar)
    """
    if level_type == 'TRIM':
        return current >= target
    return current <= target


def _load_active_tickers() -> set[str] | None:
    """
    Fetches current positions from Supabase.
    Returns set of uppercase ticker strings, or None if unavailable (no env vars).
    Used to filter strategy alerts to only positions still held.
    """
    supabase_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    service_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    user_id = os.environ.get('SUPABASE_MONITOR_USER_ID', '')
    if not supabase_url or not service_key:
        return None
    try:
        import urllib.request
        url = f"{supabase_url}/rest/v1/personal_portfolio_positions?select=ticker"
        if user_id:
            url += f"&user_id=eq.{user_id}"
        req = urllib.request.Request(url, headers={
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read().decode())
            tickers = {r['ticker'].upper().strip() for r in rows if r.get('ticker')}
            print(f'  Supabase active tickers: {sorted(tickers) or "(empty portfolio)"}')
            return tickers
    except Exception as exc:
        print(f'  Supabase ticker load failed: {exc} — skipping filter')
        return None


def run_alerts() -> dict:
    strategies_path = DOCS / 'portfolio_strategies.json'
    if not strategies_path.exists():
        print('No hay portfolio_strategies.json — nada que vigilar.')
        return {'sent': 0, 'checked': 0}

    data = json.loads(strategies_path.read_text())
    strategies = data.get('strategies') or {}
    if not strategies:
        return {'sent': 0, 'checked': 0}

    # Filter to only tickers still held in Supabase portfolio
    active = _load_active_tickers()
    if active is not None:
        stale = [t for t in strategies if t.upper() not in active]
        if stale:
            print(f'  Skipping {len(stale)} removed positions: {stale}')
        strategies = {t: v for t, v in strategies.items() if t.upper() in active}
    if not strategies:
        print('  No active positions to alert on.')
        return {'sent': 0, 'checked': 0}

    seen = _load_seen()
    today = datetime.now().strftime('%Y-%m-%d')
    sent = 0
    checked = 0

    for ticker, strat in strategies.items():
        current = _safe_float(strat.get('current_price'))
        if current is None:
            continue
        checked += 1

        for level_type, price_key, pct_key in (
            ('TRIM', 'trim_at_price', 'trim_pct'),
            ('ADD',  'add_at_price',  'add_pct'),
        ):
            target = _safe_float(strat.get(price_key))
            qty_pct = _safe_float(strat.get(pct_key))
            if target is None or qty_pct is None or qty_pct <= 0:
                continue

            if not _level_crossed(level_type, target, current):
                continue

            # Idempotencia: una alerta por (ticker, level_type, plan_target_price, day)
            key = f'{ticker}:{level_type}:{target:.2f}:{today}'
            if key in seen:
                continue

            text = _format_alert(ticker, strat, level_type, current)
            if not text:
                continue
            if _send_telegram(text):
                sent += 1
                seen[key] = datetime.now(timezone.utc).isoformat()
                # Hook IBKR (deshabilitado por defecto)
                _maybe_execute_order(ticker, level_type, target, qty_pct)

    if seen:
        _save_seen(seen)

    print(f"Strategy alerts: {sent} avisos enviados sobre {checked} posiciones revisadas.")
    return {'sent': sent, 'checked': checked}


if __name__ == '__main__':
    run_alerts()
