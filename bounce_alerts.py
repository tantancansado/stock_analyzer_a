#!/usr/bin/env python3
"""
BOUNCE ALERTS — Telegram cuando aparece un setup de rebote (es raro: ~1/semana).

Lee las dos fuentes de rebotes y avisa SOLO si hay setups nuevos:
  - docs/bounce_setups_broad.json      (S&P 500 no-curado, bounce_scanner_broad)
  - docs/mean_reversion_opportunities.csv  (curado, strategy == 'Oversold Bounce')

Dedup: docs/bounce_alerts_seen.json — un ticker no se repite en DEDUP_DAYS días
(el horizonte del setup es 1-5 días; re-avisar cada día del mismo setup es ruido).
Sin credenciales de Telegram hace dry-run (imprime el mensaje).

Corre en daily-analysis.yml justo después de los dos scanners.
"""
import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from data_integrity import check_row

DOCS = Path('docs')
BROAD_JSON = DOCS / 'bounce_setups_broad.json'
MR_CSV     = DOCS / 'mean_reversion_opportunities.csv'
SEEN_PATH  = DOCS / 'bounce_alerts_seen.json'

DEDUP_DAYS = 3
MAX_ALERTS = 6
APP_URL = 'https://tantancansado.github.io/stock_analyzer_a/app/#/bounce'

# Umbrales de calidad del universo curado — espejo de los filtros de la UI en
# frontend/src/pages/BounceTrader.tsx (allSetups + hideEarnings, activo por
# defecto). Si la app no lo pinta, no se alerta: avisar de un setup que al abrir
# el link no aparece es peor que no avisar. Un dato ausente descarta el setup
# igual que en la UI (`?? 0`), no se rellena con un valor inventado.
MIN_RR              = 1.0
MAX_RSI             = 30
MIN_CONFIDENCE      = 30
MIN_CONF_IF_DISTRIB = 60
MIN_PRICE           = 1.0
MIN_DIST_SUPPORT    = -5


def _send_telegram(text: str) -> bool:
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id   = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not bot_token or not chat_id:
        print('  Telegram: sin credenciales — dry run:\n')
        print(text)
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
    except urllib.error.HTTPError as e:
        print(f"  Telegram send failed: {e} — {e.read().decode('utf-8', 'replace')}")
        return False
    except Exception as e:
        print(f"  Telegram send failed: {e}")
        return False


def load_broad_setups() -> list[dict]:
    """Setups del scanner ampliado (ya vienen filtrados y ordenados)."""
    try:
        data = json.loads(BROAD_JSON.read_text())
        out = []
        for s in data.get('setups', []):
            out.append({
                'ticker':  str(s.get('ticker', '')).upper(),
                'source':  'BROAD',
                'price':   s.get('price'),
                'target':  s.get('target'),
                'stop':    s.get('stop'),
                'rr':      s.get('rr'),
                'rsi':     s.get('rsi2'),
                'note':    f"RSI2 ayer {s.get('rsi2')} · vol {s.get('vol_ratio')}x",
            })
        return out
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f'  No se pudo leer {BROAD_JSON}: {e}')
        return []


def _num(v):
    """Float del CSV, o None si falta/no es número (sin inventar valores)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _truthy(v) -> bool:
    """Flag del CSV ('True'/'False'/NaN). Ausente = sin aviso, como en la UI."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return False
    if isinstance(v, str):
        return v.strip().upper() in ('TRUE', '1', 'YES')
    return bool(v)


def passes_quality_filters(r) -> tuple[bool, str]:
    """¿La UI pintaría este setup curado? Devuelve (pasa, motivo del rechazo)."""
    # Antes que nada, que los números sean posibles (data_integrity). Un setup
    # no lleva value_score, así que no se le exigen los campos de VALUE.
    integrity = check_row(dict(r), require_value_fields=False)
    if not integrity['ok']:
        return False, integrity['blocking'][0]['reason']

    rsi = _num(r.get('rsi'))
    if rsi is None or rsi >= MAX_RSI or rsi == 0:
        return False, f'RSI {rsi} (necesita <{MAX_RSI} y != 0)'

    price = _num(r.get('current_price'))
    if price is None or price < MIN_PRICE:
        return False, f'precio {price} (penny stock)'

    dist = _num(r.get('distance_to_support_pct'))
    if dist is not None and dist < MIN_DIST_SUPPORT:
        return False, f'soporte perdido ({dist}%)'

    conf = _num(r.get('bounce_confidence')) or 0
    if conf < MIN_CONFIDENCE:
        return False, f'confianza {conf} (<{MIN_CONFIDENCE})'

    if r.get('dark_pool_signal') == 'DISTRIBUTION' and conf < MIN_CONF_IF_DISTRIB:
        return False, f'dark pool DISTRIBUTION con confianza {conf}'

    rr = _num(r.get('risk_reward'))
    if rr is not None and rr < MIN_RR:
        return False, f'R:R {rr} (<{MIN_RR}: se arriesga más de lo que se gana)'

    if _truthy(r.get('earnings_warning')):
        return False, 'earnings dentro del horizonte del setup'

    return True, ''


def load_curated_setups() -> list[dict]:
    """Oversold Bounce del detector curado (mean reversion), filtrado como la UI."""
    try:
        df = pd.read_csv(MR_CSV)
        if df.empty or 'strategy' not in df.columns:
            return []
        ob = df[df['strategy'] == 'Oversold Bounce']
        out = []
        for _, r in ob.iterrows():
            t = str(r.get('ticker', '')).upper()
            if not t:
                continue
            ok, why = passes_quality_filters(r)
            if not ok:
                print(f'  {t}: descartado — {why}')
                continue
            score = r.get('reversion_score')
            out.append({
                'ticker':  t,
                'source':  'CURADO',
                'price':   r.get('current_price'),
                'target':  r.get('target'),
                'stop':    r.get('stop_loss'),
                'rr':      r.get('risk_reward'),
                'rsi':     r.get('rsi'),
                'note':    f"RSI {r.get('rsi')} · score MR {score}" if pd.notna(score) else f"RSI {r.get('rsi')}",
            })
        return out
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f'  No se pudo leer {MR_CSV}: {e}')
        return []


def _load_seen() -> dict:
    try:
        return json.loads(SEEN_PATH.read_text()) if SEEN_PATH.exists() else {}
    except Exception:
        return {}


def _save_seen(seen: dict) -> None:
    try:
        SEEN_PATH.write_text(json.dumps(seen, indent=2))
    except Exception as e:
        print(f'  No se pudo guardar el estado de dedup: {e}')


def filter_new(setups: list[dict], seen: dict, today: str) -> list[dict]:
    """Quita tickers ya avisados hace menos de DEDUP_DAYS. Marca los nuevos en seen."""
    fresh = []
    today_d = date.fromisoformat(today)
    for s in setups:
        t = s['ticker']
        last = seen.get(t)
        if last:
            try:
                if (today_d - date.fromisoformat(last)).days < DEDUP_DAYS:
                    continue
            except ValueError:
                pass
        fresh.append(s)
        seen[t] = today
    return fresh


def _fmt(v, prefix='$') -> str:
    try:
        return f'{prefix}{float(v):.2f}'
    except (TypeError, ValueError):
        return '—'


def build_message(setups: list[dict], today: str) -> str:
    lines = [f'🎯 <b>Setup de Rebote detectado</b> — {today}',
             '<i>Es raro (~1/semana): merece un vistazo hoy, horizonte 1-5 días</i>', '']
    for s in setups[:MAX_ALERTS]:
        tag = '🔬' if s['source'] == 'CURADO' else '📡'
        rr = f" · R:R {float(s['rr']):.1f}" if s.get('rr') is not None and not pd.isna(s['rr']) else ''
        lines.append(
            f"{tag} <b>{s['ticker']}</b> [{s['source']}] {_fmt(s.get('price'))}\n"
            f"   Target {_fmt(s.get('target'))} · Stop {_fmt(s.get('stop'))}{rr}\n"
            f"   {s.get('note', '')}"
        )
        lines.append('')

    # Un link por pestaña presente: la página abre en 'curado' y los BROAD viven
    # en otra pestaña — sin el parámetro el link cae donde el setup no está.
    sources = {s['source'] for s in setups[:MAX_ALERTS]}
    if 'CURADO' in sources:
        lines.append(f'🔗 <a href="{APP_URL}?mode=curated">Ver en la app — universo curado</a>')
    if 'BROAD' in sources:
        lines.append(f'🔗 <a href="{APP_URL}?mode=broad">Ver en la app — universo ampliado</a>')
    return '\n'.join(lines).strip()


def main() -> None:
    print('[bounce_alerts] Buscando setups de rebote nuevos...')
    today = date.today().isoformat()

    setups = load_broad_setups() + load_curated_setups()
    if not setups:
        print('  0 setups en ambos universos — nada que avisar (normal la mayoría de días)')
        return

    seen = _load_seen()
    fresh = filter_new(setups, seen, today)
    if not fresh:
        print(f'  {len(setups)} setups pero todos avisados hace <{DEDUP_DAYS} días — sin re-aviso')
        return

    msg = build_message(fresh, today)
    if _send_telegram(msg):
        print(f'  ✓ Telegram enviado: {len(fresh)} setup(s)')
        _save_seen(seen)   # solo se marca como avisado si el envío llegó
    else:
        print('  Envío fallido/dry-run — el dedup NO se guarda (se reintenta en la próxima corrida)')


if __name__ == '__main__':
    main()
