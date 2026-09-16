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
from bounce_catalyst_check import filter_setups

DOCS = Path('docs')
BROAD_JSON = DOCS / 'bounce_setups_broad.json'
MR_CSV     = DOCS / 'mean_reversion_opportunities.csv'
SEEN_PATH  = DOCS / 'bounce_alerts_seen.json'
CATALYST_FLAGS_PATH = DOCS / 'bounce_catalyst_flags.json'

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

    # Si la IA lo rechazó, no se avisa. No estaba comprobado en ningún filtro:
    # CBOE salió el 16-sep-2026 con `ai_confirmation: NO` («RSI >25 y R:R
    # bajo») y aun así llegó una notificación diciendo «merece un vistazo hoy».
    # CAUTION sí pasa —es una advertencia, no un rechazo— y se marca en el
    # mensaje para que se vea.
    if str(r.get('ai_confirmation') or '').upper() == 'NO':
        return False, f"la IA lo rechaza: {r.get('ai_reason') or 'sin motivo'}"

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
            # El objetivo que se anuncia tiene que ser el mismo contra el que
            # se calculó el R:R. El detector guarda DOS: `target` es la
            # resistencia (optimista) y `bounce_target` es min(precio×1.07,
            # resistencia) — y `risk_reward` se calcula contra el SEGUNDO.
            # Publicarlos juntos daba avisos incoherentes: CBOE salió el
            # 16-sep-2026 como «Target $308,62 · R:R 1,1», cuando con ese
            # objetivo el R:R es 2,25 y el 1,1 corresponde a 289,37. Los dos
            # números eran correctos por separado y el par era falso.
            #
            # Desde el 16-sep-2026 el detector publica un solo objetivo —el de
            # rebote— y la resistencia va aparte en `techo_tecnico`. Se sigue
            # leyendo `bounce_target` primero para que un CSV antiguo, generado
            # antes de ese cambio, no vuelva a anunciar la resistencia.
            objetivo = r.get('bounce_target')
            if objetivo is None or pd.isna(objetivo):
                objetivo = r.get('target')
            # El R:R sale del techo de la zona de entrada, que es el precio que
            # la ficha manda pagar, no del precio de pantalla. Si el aviso
            # enseñara el precio de pantalla junto a ese R:R volveríamos al
            # mismo par falso, solo que por el otro lado.
            entrada = r.get('entry_ref')
            if entrada is None or pd.isna(entrada):
                entrada = r.get('current_price')
            techo = r.get('techo_tecnico')
            if techo is None or pd.isna(techo):
                techo = r.get('resistance_level')
            if techo is None or pd.isna(techo):
                # CSV anterior al cambio: allí la resistencia vivía en `target`.
                viejo_target = r.get('target')
                if viejo_target is not None and not pd.isna(viejo_target) \
                   and objetivo is not None and float(viejo_target) > float(objetivo):
                    techo = viejo_target
            out.append({
                'ticker':  t,
                'source':  'CURADO',
                'price':   entrada,
                'precio_pantalla': r.get('current_price'),
                'target':  objetivo,
                'techo':   techo,                # la resistencia, como contexto
                'stop':    r.get('stop_loss'),
                'rr':      r.get('risk_reward'),
                'rsi':     r.get('rsi'),
                'regimen_ok': r.get('market_ok'),
                'regimen':    r.get('market_regime'),
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


def _save_catalyst_flags(descartados: list[dict], today: str,
                         limpios: list[dict] | None = None) -> None:
    """Persiste el resultado de la comprobación para que el frontend lo vea.

    Se guardan los PELIGRO **y también los LIMPIO**, y eso es el punto. Antes
    solo se guardaban los descartados, así que «sin flag» quería decir dos
    cosas incompatibles:

        - se comprobó y no hay catalizador grave  → se puede enseñar
        - NO se comprobó                          → no se sabe

    y la app las trataba igual. Los caminos por los que no se comprueba son
    reales y silenciosos: si todos los setups ya se avisaron hace menos de
    DEDUP_DAYS, `main()` sale antes de llamar al veto; si no hay saldo o la API
    falla, `ask_with_search` devuelve vacío y el veredicto sale SIN_DATOS; y el
    paso entero lleva `continue-on-error` en el workflow.

    En los tres casos el setup aparecía como si hubiera pasado el filtro. Es el
    mismo «no lo sé» disfrazado de «no hay nada» que había en la carga de datos
    del frontend — y aquí es peor, porque lo que se salta es un veto de
    seguridad.

    Expira a DEDUP_DAYS, igual que el propio dedup de avisos.
    """
    try:
        flags = json.loads(CATALYST_FLAGS_PATH.read_text()).get('flags', {}) if CATALYST_FLAGS_PATH.exists() else {}
    except Exception:
        flags = {}
    today_d = date.fromisoformat(today)
    flags = {
        t: f for t, f in flags.items()
        if f.get('checked_at') and (today_d - date.fromisoformat(f['checked_at'])).days < DEDUP_DAYS
    }
    for c in (limpios or []):
        flags[c['ticker']] = {
            'veredicto': 'LIMPIO',
            'motivo': c.get('catalyst_motivo', ''),
            'fuentes': c.get('catalyst_fuentes', []),
            'checked_at': today,
        }
    for d in descartados:
        flags[d['ticker']] = {
            'veredicto': 'PELIGRO',
            'motivo': d.get('catalyst_motivo', ''),
            'fuentes': d.get('catalyst_fuentes', []),
            'checked_at': today,
        }
    try:
        CATALYST_FLAGS_PATH.write_text(json.dumps(
            {'generated_at': datetime.now().isoformat(), 'flags': flags}, indent=2))
    except Exception as e:
        print(f'  No se pudo guardar bounce_catalyst_flags.json: {e}')


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
    # El régimen, arriba del todo y una sola vez. El detector ya lo calcula
    # («SPY < MA50 → rebotes de alto riesgo») y el aviso lo ignoraba: CBOE se
    # avisó el 16-sep-2026 con `market_regime: CORRECCIÓN` y `market_ok: False`
    # sin mencionarlo. Va como AVISO y no como filtro a propósito: los rebotes
    # aparecen precisamente cuando el mercado cae, así que filtrar por régimen
    # dejaría la sección vacía justo los días que tiene algo que decir.
    malos = [s for s in setups[:MAX_ALERTS] if s.get('regimen_ok') is False]
    if malos:
        reg = next((s.get('regimen') for s in malos if s.get('regimen')), None)
        lines.append(f"⚠️ <b>Régimen {reg or 'adverso'}</b> — el sistema marca los rebotes "
                     f"como de alto riesgo hoy")
        lines.append('')

    for s in setups[:MAX_ALERTS]:
        tag = '🔬' if s['source'] == 'CURADO' else '📡'
        rr = f" · R:R {float(s['rr']):.1f}" if s.get('rr') is not None and not pd.isna(s['rr']) else ''
        # El techo (la resistencia) va como contexto, separado del objetivo del
        # R:R, para que no se confundan otra vez.
        techo = ''
        try:
            if s.get('techo') is not None and not pd.isna(s['techo']) and \
               float(s['techo']) > float(s.get('target') or 0):
                techo = f" · techo {_fmt(s['techo'])}"
        except (TypeError, ValueError):
            pass
        # El precio que encabeza la línea es el de ENTRADA (contra el que se
        # calcula el R:R). Si cotiza más abajo se dice, porque entonces la
        # entrada es una orden a la espera, no una compra de ahora.
        cotiza = ''
        try:
            pantalla = s.get('precio_pantalla')
            entrada = float(s.get('price') or 0)
            if pantalla is not None and not pd.isna(pantalla) and entrada > 0 \
               and abs(float(pantalla) / entrada - 1) > 0.005:
                cotiza = f" (cotiza {_fmt(pantalla)})"
        except (TypeError, ValueError):
            pass
        lines.append(
            f"{tag} <b>{s['ticker']}</b> [{s['source']}] entrada {_fmt(s.get('price'))}{cotiza}\n"
            f"   Target {_fmt(s.get('target'))} · Stop {_fmt(s.get('stop'))}{rr}{techo}\n"
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

    # La purga de flags caducados va ANTES de los early return, no al final.
    #
    # `_save_catalyst_flags` ya los expiraba a DEDUP_DAYS, pero solo se llamaba
    # al final de main() — y main() sale antes seis días de cada siete (sin
    # setups, o todos ya avisados). Así que el fichero se quedaba sin tocar y
    # los veredictos viejos seguían dentro pareciendo vigentes: el 16-sep-2026
    # `bounce_catalyst_flags.json` llevaba 36 días con un único flag del 11 de
    # agosto, y la app lo leía como si fuera de hoy.
    #
    # Un veredicto de catalizador es una lectura de noticias, no un dato
    # estructural: «limpio» hace cinco semanas no dice nada de hoy.
    _save_catalyst_flags([], today)

    setups = load_broad_setups() + load_curated_setups()
    if not setups:
        print('  0 setups en ambos universos — nada que avisar (normal la mayoría de días)')
        return

    seen = _load_seen()
    fresh = filter_new(setups, seen, today)
    if not fresh:
        print(f'  {len(setups)} setups pero todos avisados hace <{DEDUP_DAYS} días — sin re-aviso')
        return

    # Un RSI2 de 1.7 puede ser una goma estirada o el primer día de un desplome:
    # desde los indicadores se ven igual. Se comprueba si hay un catalizador
    # negativo grave detrás antes de avisar de nada (bounce_catalyst_check).
    fresh, descartados = filter_setups(fresh)
    # Se guarda SIEMPRE, aunque no se descarte nada: registrar que un ticker se
    # comprobó y salió limpio es tan importante como registrar el peligro. Sin
    # eso, «sin flag» significa a la vez «limpio» y «no comprobado».
    _save_catalyst_flags(descartados, today, limpios=fresh)
    if not fresh:
        print(f'  {len(descartados)} setup(s) descartados por catalizador negativo — nada que avisar')
        return

    # Última puerta antes de enviar. Los filtros de arriba comprueban si la
    # idea es buena; esto comprueba que el MENSAJE no se contradiga a sí mismo.
    # Son cosas distintas y hacía falta la segunda: el 16-sep-2026 salió CBOE
    # como «Target $308,62 · R:R 1,1» con los tres números correctos por
    # separado y el conjunto falso. Un aviso con precios es una propuesta de
    # operación: si no cuadra consigo misma, no sale.
    import alerta_coherente
    precios = {str(s_.get('ticker', '')).upper(): _num(s_.get('price')) for s_ in fresh}
    fresh, incoherentes = alerta_coherente.filtrar(fresh, precios)
    for problema in incoherentes:
        print(f'  🛑 NO se avisa — {problema}')
    if not fresh:
        print('  Ningún setup pasa la revisión de coherencia — sin aviso')
        return

    msg = build_message(fresh, today)
    if _send_telegram(msg):
        print(f'  ✓ Telegram enviado: {len(fresh)} setup(s)')
        _save_seen(seen)   # solo se marca como avisado si el envío llegó
    else:
        print('  Envío fallido/dry-run — el dedup NO se guarda (se reintenta en la próxima corrida)')


if __name__ == '__main__':
    main()
