"""
Telegram daily alerts — envía resumen del pipeline al terminar el análisis diario.

Contenido del mensaje:
  - Régimen de mercado actual
  - Top 5 VALUE por score (con ML probability si disponible)
  - Novedades del día (nuevas entradas, subidas/bajadas de score ≥5pts)
  - Alertas de earnings próximos en el top VALUE
"""
import json
import os
from pathlib import Path

import pandas as pd
import requests

DOCS = Path('docs')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID', '')

APP_URL = 'https://tantancansado.github.io/stock_analyzer_a/app/'


def _send(text: str):
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
        r.raise_for_status()
        print('  Telegram message sent')
    except Exception as e:
        print(f'  Telegram send failed: {e}')


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _regime_emoji(regime: str) -> str:
    mapping = {
        'CONFIRMED_UPTREND': '🟢',
        'UPTREND': '🟢',
        'UPTREND_PRESSURE': '🟡',
        'NEUTRAL': '🟡',
        'CORRECTION': '🔴',
        'BEAR': '🔴',
    }
    return mapping.get(regime.upper(), '⚪')


def _ml_label(label: str) -> str:
    if label == 'ALTA':
        return ' <b>ML↑</b>'
    if label == 'BAJA':
        return ' <i>ML↓</i>'
    return ''


def build_message() -> str:
    lines = []

    # ── Régimen ───────────────────────────────────────────────────────────────
    regime = 'UNKNOWN'
    try:
        val_df = pd.read_csv(DOCS / 'value_opportunities.csv')
        if 'market_regime' in val_df.columns and not val_df.empty:
            regime = str(val_df['market_regime'].iloc[0])
    except Exception:
        pass

    lines.append(f'📊 <b>Stock Analyzer — Daily Report</b>')
    lines.append(f'{_regime_emoji(regime)} Régimen: <b>{regime}</b>')
    lines.append('')

    # ── Top 5 VALUE ───────────────────────────────────────────────────────────
    try:
        df = pd.read_csv(DOCS / 'value_opportunities.csv')
        df['value_score'] = pd.to_numeric(df['value_score'], errors='coerce')
        top5 = df.nlargest(5, 'value_score')
        lines.append('🏆 <b>Top 5 VALUE</b>')
        for _, r in top5.iterrows():
            score = f"{r['value_score']:.0f}" if pd.notna(r['value_score']) else '—'
            upside = f"+{r['analyst_upside_pct']:.0f}%" if pd.notna(r.get('analyst_upside_pct')) else ''
            ml_lbl = _ml_label(str(r.get('ml_win_label', '')))
            earn = ' ⚠️earn' if r.get('earnings_warning') else ''
            lines.append(f'  • <b>{r["ticker"]}</b> {score}pts {upside}{ml_lbl}{earn}')
        lines.append('')
    except Exception as e:
        lines.append(f'  (error cargando VALUE: {e})')
        lines.append('')

    # ── Novedades del día ─────────────────────────────────────────────────────
    alerts_data = _load_json(DOCS / 'score_alerts.json')
    alerts = alerts_data.get('alerts', [])
    if alerts:
        new_entries = [a for a in alerts if a['type'] == 'NEW_ENTRY']
        score_up    = [a for a in alerts if a['type'] == 'SCORE_UP']
        score_down  = [a for a in alerts if a['type'] == 'SCORE_DOWN']

        if new_entries:
            lines.append('🆕 <b>Nuevas entradas</b>')
            for a in new_entries[:3]:
                lines.append(f'  + <b>{a["ticker"]}</b> {a["score_today"]:.0f}pts [{a["sector"]}]')
            lines.append('')

        if score_up:
            lines.append('⬆️ <b>Subidas de score</b>')
            for a in score_up[:3]:
                lines.append(f'  {a["ticker"]} {a["score_prev"]:.0f}→{a["score_today"]:.0f} (Δ{a["delta"]:+.1f})')
            lines.append('')

        if score_down:
            lines.append('⬇️ <b>Bajadas de score</b>')
            for a in score_down[:3]:
                lines.append(f'  {a["ticker"]} {a["score_prev"]:.0f}→{a["score_today"]:.0f} (Δ{a["delta"]:+.1f})')
            lines.append('')

    # ── Portfolio price alerts ────────────────────────────────────────────────
    port_data = _load_json(DOCS / 'portfolio_alerts.json')
    port_alerts = port_data.get('alerts', [])
    if port_alerts:
        stops   = [a for a in port_alerts if a['type'] == 'STOP_TRIGGERED']
        targets = [a for a in port_alerts if a['type'] == 'TARGET_REACHED']
        near    = [a for a in port_alerts if a['type'] == 'NEAR_TARGET']

        if stops:
            lines.append('🚨 <b>STOP ACTIVADO</b>')
            for a in stops:
                lines.append(f'  <b>{a["ticker"]}</b> {a["pct_change"]:+.1f}% · entry {a["entry"]} → {a["current"]}')
            lines.append('')

        if targets:
            lines.append('🎯 <b>Objetivo alcanzado</b>')
            for a in targets:
                lines.append(f'  <b>{a["ticker"]}</b> {a["pct_change"]:+.1f}% · target {a["target"]}')
            lines.append('')

        if near:
            lines.append('🔔 <b>Cerca del objetivo</b>')
            for a in near:
                ptt = f" ({a['pct_to_target']:.0f}% del camino)" if a.get('pct_to_target') else ''
                lines.append(f'  {a["ticker"]} {a["pct_change"]:+.1f}%{ptt}')
            lines.append('')

    # ── ML model stats ────────────────────────────────────────────────────────
    ml_data = _load_json(DOCS / 'ml_win_probability.json')
    if ml_data:
        preds = ml_data.get('predictions', {})
        n_alta = sum(1 for v in preds.values() if v.get('label') == 'ALTA')
        auc = ml_data.get('model_auc', 0)
        lines.append(f'🤖 ML: {n_alta} tickers ALTA prob · AUC {auc:.3f}')
        lines.append('')

    # ── Link ──────────────────────────────────────────────────────────────────
    lines.append(f'🔗 <a href="{APP_URL}">Abrir app</a>')

    return '\n'.join(lines)


def main():
    print('[Telegram] Building daily alert...')
    msg = build_message()
    _send(msg)


if __name__ == '__main__':
    main()
