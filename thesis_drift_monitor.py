#!/usr/bin/env python3
"""
THESIS DRIFT MONITOR — vigilancia de tesis para posiciones VALUE abiertas.

Hueco que cubre: cerebro.scan_thesis_drift sólo sigue tickers que SIGUEN en la
lista de oportunidades. Pero una recomendación VALUE activa puede romper su tesis
JUSTO cuando desaparece de la lista — y entonces nadie la vigila, aunque la
posición siga abierta. Este monitor cruza las recomendaciones ACTIVE de
recommendations.csv con el estado fundamental ACTUAL y alerta cuando la tesis que
justificó la compra se ha deteriorado.

Señales de drift (cada una con razón explícita, sin números inventados):
  THESIS_BROKEN   — el ticker dispara un hard-reject actual:
                      · negative_roe / fundamental_score colapsó (<45)
                      · analyst_upside_pct < 0 (ahora sobrevalorado)
                      · analyst_upside_pct >= 30 (ahora value-trap)
                      · earnings_warning activo
  FUND_DETERIORATING — fundamental_score cayó ≥10pts vs el de la recomendación
  STOP_BREACHED      — precio actual por debajo del stop_loss registrado

Filosofía del usuario: "0 señales > señales falsas". Solo alerta cuando hay una
razón fundamental concreta, nunca por ruido de precio aislado.

Salida:
  docs/portfolio_tracker/thesis_drift_alerts.json   (consumible por el frontend)
  Telegram (si TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID están definidos)

Dedup: no repite la misma alerta (ticker+tipo) en <DEDUP_DAYS días.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

DOCS = Path('docs')
TRACKER = DOCS / 'portfolio_tracker'
REC_CSV = TRACKER / 'recommendations.csv'
FUND_CSV = DOCS / 'fundamental_scores.csv'
OUT_JSON = TRACKER / 'thesis_drift_alerts.json'
SENT_LOG = TRACKER / 'thesis_drift_sent.json'

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
APP_URL = 'https://tantancansado.github.io/stock_analyzer_a/app/'

# Thresholds — calibrados con las reglas duras de CLAUDE.md
FUND_COLLAPSE = 45.0      # fundamental_score por debajo de esto = tesis rota
FUND_DROP_PTS = 10.0      # caída vs el score de la recomendación
UPSIDE_TRAP = 30.0        # analyst_upside_pct >= esto = value trap (hard reject)
DEDUP_DAYS = 5            # no repetir la misma alerta en N días


def _send_telegram(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print('  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — dry run')
        print(text)
        return
    try:
        r = requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML',
                  'disable_web_page_preview': 'true'},
            timeout=10,
        )
        if r.ok:
            print('  Telegram message sent')
        else:
            print(f'  Telegram send failed: {r.status_code} {r.text}')
    except Exception as e:
        # Network best-effort: log and continue, never crash the monitor.
        print(f'  Telegram send failed: {e}')


def _load_sent_log() -> dict:
    if not SENT_LOG.exists():
        return {}
    try:
        return json.loads(SENT_LOG.read_text())
    except Exception:
        return {}


def _save_sent_log(log: dict) -> None:
    SENT_LOG.write_text(json.dumps(log, indent=2))


def _num(series_val) -> float | None:
    """Coerce to float or None — never invent a number for missing data."""
    v = pd.to_numeric(series_val, errors='coerce')
    return None if pd.isna(v) else float(v)


def _active_value_positions() -> pd.DataFrame:
    if not REC_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(REC_CSV, low_memory=False)
    if 'status' not in df.columns or 'strategy' not in df.columns:
        return pd.DataFrame()
    active = df[(df['status'] == 'ACTIVE') & (df['strategy'].isin(['VALUE', 'EU_VALUE']))].copy()
    # Keep the most recent open signal per ticker (the live thesis)
    if 'signal_date' in active.columns:
        active['signal_date'] = pd.to_datetime(active['signal_date'], errors='coerce')
        active = active.sort_values('signal_date').drop_duplicates('ticker', keep='last')
    return active


def _fundamentals_now() -> dict[str, dict]:
    if not FUND_CSV.exists():
        return {}
    f = pd.read_csv(FUND_CSV, low_memory=False)
    if 'ticker' not in f.columns:
        return {}
    out: dict[str, dict] = {}
    for _, row in f.iterrows():
        out[str(row['ticker']).upper()] = row.to_dict()
    return out


def _stop_finding(position: dict) -> list[dict]:
    """Price below the registered stop — concrete, not noise."""
    stop = _num(position.get('stop_loss'))
    last_price = _num(position.get('price_30d')) or _num(position.get('price_14d')) \
        or _num(position.get('price_7d'))
    if stop is not None and last_price is not None and last_price < stop:
        return [{
            'type': 'STOP_BREACHED',
            'reason': f'Precio {last_price:.2f} por debajo del stop {stop:.2f}',
            'severity': 'HIGH',
        }]
    return []


def _fundamental_findings(position: dict, fund: dict) -> list[dict]:
    """Hard-reject conditions + gradual deterioration vs the score at recommendation."""
    findings: list[dict] = []
    fund_now = _num(fund.get('fundamental_score'))
    fund_at_signal = _num(position.get('value_score'))
    upside_now = _num(fund.get('analyst_upside_pct'))
    earnings_warn = fund.get('earnings_warning')

    if fund_now is not None and fund_now < FUND_COLLAPSE:
        findings.append({
            'type': 'THESIS_BROKEN',
            'reason': f'fundamental_score colapsó a {fund_now:.0f} (mín {FUND_COLLAPSE:.0f})',
            'severity': 'HIGH',
        })
    if upside_now is not None and upside_now < 0:
        findings.append({
            'type': 'THESIS_BROKEN',
            'reason': f'analyst_upside ahora {upside_now:.0f}% — sobrevalorado',
            'severity': 'HIGH',
        })
    if upside_now is not None and upside_now >= UPSIDE_TRAP:
        findings.append({
            'type': 'THESIS_BROKEN',
            'reason': f'analyst_upside saltó a {upside_now:.0f}% — value trap (0% win histórico)',
            'severity': 'HIGH',
        })
    if isinstance(earnings_warn, str) and earnings_warn.strip().lower() not in ('none', 'nan', ''):
        findings.append({
            'type': 'THESIS_BROKEN',
            'reason': f'earnings_warning activo: {earnings_warn}',
            'severity': 'MEDIUM',
        })
    if fund_now is not None and fund_at_signal is not None and (fund_at_signal - fund_now) >= FUND_DROP_PTS:
        drop = fund_at_signal - fund_now
        findings.append({
            'type': 'FUND_DETERIORATING',
            'reason': f'fundamental_score cayó {drop:.0f}pts ({fund_at_signal:.0f}→{fund_now:.0f}) desde la recomendación',
            'severity': 'MEDIUM',
        })
    return findings


def _evaluate(position: dict, fund: dict | None) -> list[dict]:
    """Return list of drift findings for one open position. Empty = thesis intact."""
    findings = _stop_finding(position)
    if fund is not None:
        # No current fundamentals → can't assess thesis; don't invent a verdict.
        findings += _fundamental_findings(position, fund)
    return findings


def build_alerts() -> dict:
    positions = _active_value_positions()
    funds = _fundamentals_now()

    alerts: list[dict] = []
    for _, pos in positions.iterrows():
        pos_d = pos.to_dict()
        ticker = str(pos_d.get('ticker', '')).upper()
        findings = _evaluate(pos_d, funds.get(ticker))
        for f in findings:
            alerts.append({
                'ticker': ticker,
                'company_name': pos_d.get('company_name', ticker),
                'strategy': pos_d.get('strategy'),
                'signal_date': str(pd.to_datetime(pos_d.get('signal_date')).date())
                    if pos_d.get('signal_date') is not None and not pd.isna(pos_d.get('signal_date')) else None,
                **f,
            })

    high = sum(1 for a in alerts if a['severity'] == 'HIGH')
    return {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'positions_checked': int(len(positions)),
        'total': len(alerts),
        'high_count': high,
        'alerts': alerts,
    }


def _notify_new(alerts: list[dict]) -> None:
    """Send Telegram only for alerts not sent within DEDUP_DAYS."""
    log = _load_sent_log()
    cutoff = date.today() - timedelta(days=DEDUP_DAYS)
    fresh = []
    for a in alerts:
        key = f"{a['ticker']}:{a['type']}"
        last = log.get(key)
        if last:
            try:
                if date.fromisoformat(last) >= cutoff:
                    continue
            except ValueError:
                pass
        fresh.append(a)
        log[key] = str(date.today())

    if not fresh:
        print('  No new thesis-drift alerts to send')
        return

    icon = {'HIGH': '🔴', 'MEDIUM': '🟠'}
    lines = ['⚠️ <b>DRIFT DE TESIS — posiciones abiertas</b>', '']
    for a in sorted(fresh, key=lambda x: 0 if x['severity'] == 'HIGH' else 1):
        lines.append(f"{icon.get(a['severity'], '⚪')} <b>{a['ticker']}</b> — {a['reason']}")
    lines += ['', f'<a href="{APP_URL}#/thesis-drift">Ver detalle →</a>']
    _send_telegram('\n'.join(lines))
    _save_sent_log(log)


def main() -> None:
    print('🔍 Thesis drift monitor — posiciones VALUE abiertas')
    result = build_alerts()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2))
    print(f"  {result['positions_checked']} posiciones · {result['total']} alertas "
          f"({result['high_count']} HIGH) → {OUT_JSON}")
    if result['alerts']:
        _notify_new(result['alerts'])


if __name__ == '__main__':
    main()
