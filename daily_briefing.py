#!/usr/bin/env python3
"""
Daily Briefing — un solo mensaje al día, escrito por Claude, que sustituye a la
docena de alertas sueltas.

El problema que resuelve: 19 scripts distintos mandaban a Telegram por su
cuenta, cada uno convencido de que lo suyo merecía interrumpir. Roturas de
índices, flujo de opciones, cerebro, insiders... El resultado era ruido
fragmentado del que ninguna pieza cambiaba una decisión.

Aquí se invierte el flujo: los scripts publican sus CSV/JSON (ya lo hacían) y
este paso, al final del pipeline, lee lo que ya está verificado y le pide a
Claude que lo cuente. Claude REDACTA, NO ANALIZA — recibe hechos ya calculados y
escribe el texto. Ni un número que no venga de los datos, igual que en todo lo
demás (ver claude_research, data_integrity, currency_normalizer).

Qué lleva, por orden de lo que cambia una decisión:
  1. Qué comprar hoy — y si no hay nada, decirlo en la primera línea
  2. Tesis rota en algo que YA tienes comprado (lo que más urge saber)
  3. Qué vigilar: barato pero aún cayendo
  4. Régimen de mercado, SOLO si cambió respecto a ayer
  5. El win rate real del sistema como recordatorio de tamaño de posición

Los rebotes siguen avisando por su cuenta: son de 1-5 días y esperar al
briefing les quita el valor.
"""
from __future__ import annotations

import csv
import json
import os
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from groq_utils import claude_chat

DOCS = Path('docs')
TRACKER = DOCS / 'portfolio_tracker'
MODEL = 'claude-sonnet-5'

MAX_CANDIDATOS = 8
MAX_VIGILAR = 5


def _json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default if default is not None else {}


def _rows(path: Path) -> list[dict]:
    try:
        with path.open(newline='') as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _regime_cambio() -> str | None:
    """Régimen de hoy solo si difiere del de ayer — si no, no se menciona."""
    hoy = _json(DOCS / 'market_regime.json').get('regime')
    if not hoy:
        return None
    ayer = None
    hist = sorted((DOCS / 'history').glob('*/market_regime.json'), reverse=True)
    for p in hist[:3]:
        prev = _json(p).get('regime')
        if prev:
            ayer = prev
            break
    return hoy if (ayer and ayer != hoy) else None


def datos_incompletos(rows: list[dict]) -> list[str]:
    """Columnas que el pipeline debía haber rellenado y no están.

    Sin esto, un scoring a medias se cuenta como un día tranquilo: el 3-ago-2026
    core-scoring murió antes de calcular el timing de entrada y el briefing
    anunció "0 comprables" con 56 tickers en lista. "No hay nada" y "no lo sé"
    son cosas distintas y el mensaje tiene que distinguirlas.
    """
    if not rows:
        return ['la lista VALUE está vacía']
    fallos = []
    for col, desc in (('entry_readiness', 'el timing de entrada'),
                      ('value_score', 'el score'),
                      ('current_price', 'el precio')):
        if not any((r.get(col) or '').strip() for r in rows):
            fallos.append(f'falta {desc} ({col}) en las {len(rows)} filas')
    return fallos


def gather_facts() -> dict:
    """Hechos ya verificados por el resto del pipeline. Nada se calcula aquí."""
    rows = _rows(DOCS / 'value_opportunities.csv')

    def ficha(r):
        return {
            'ticker': r.get('ticker'),
            'empresa': (r.get('company_name') or '')[:30],
            'score': _f(r.get('value_score')),
            'precio': _f(r.get('current_price')),
            'upside_analista': _f(r.get('analyst_upside_pct')),
            'upside_triangulado': _f(r.get('upside_triangulated_pct')),
            'divergencia': r.get('upside_divergence') or '',
            'fcf_yield': _f(r.get('fcf_yield_pct')),
            'del_maximo_pct': _f(r.get('proximity_to_52w_high')),
            'rs_6m': _f(r.get('relative_strength_6m')),
            'timing': r.get('entry_readiness'),
            'por_que_cae': r.get('why_cheap') or '',
            'por_que_cae_detalle': (r.get('why_cheap_resumen') or '')[:180],
        }

    # Comprables: timing a favor y sin que los modelos propios desmientan el precio
    comprables = [ficha(r) for r in rows
                  if r.get('entry_readiness') == 'ENTRADA'
                  and (r.get('upside_divergence') or '') != 'ALTA'
                  and (r.get('why_cheap') or '') != 'DETERIORO']
    comprables.sort(key=lambda x: -(x['score'] or 0))

    # Vigilar: baratos de verdad pero todavía cayendo
    vigilar = [ficha(r) for r in rows
               if r.get('entry_readiness') in ('ESPERAR', 'VIGILAR')
               and (_f(r.get('proximity_to_52w_high')) or 0) < -10
               and (_f(r.get('value_score')) or 0) >= 50]
    vigilar.sort(key=lambda x: x['rs_6m'] or 0)

    drift = _json(TRACKER / 'thesis_drift_alerts.json', {})
    tesis_rotas = [
        {'ticker': a.get('ticker'), 'motivo': (a.get('reason') or a.get('motivo') or '')[:160],
         'severidad': a.get('severity') or a.get('severidad') or ''}
        for a in (drift.get('alerts') or drift.get('alertas') or [])
    ][:5]

    # El horizonte de juicio para VALUE es 180d — a 90 días una tesis todavía es
    # ruido. Pero la muestra de 180d no existe hasta finales de agosto (la señal
    # más antigua es del 26-feb), así que hasta entonces se informa del 90d
    # DICIENDO que es provisional, en vez de venderlo como el veredicto.
    resumen = _json(TRACKER / 'summary.json')
    overall = (resumen.get('overall') or {})
    h180, h90 = (overall.get('180d') or {}), (overall.get('90d') or {})
    definitivo = bool(h180.get('count'))
    horizonte = h180 if definitivo else h90

    return {
        'fecha': date.today().isoformat(),
        'total_lista': len(rows),
        'datos_incompletos': datos_incompletos(rows),
        'comprables': comprables[:MAX_CANDIDATOS],
        'vigilar': vigilar[:MAX_VIGILAR],
        'tesis_rotas': tesis_rotas,
        'regimen_cambio': _regime_cambio(),
        'rendimiento_sistema': {
            'horizonte': '180d' if definitivo else '90d',
            'es_horizonte_definitivo': definitivo,
            'nota': None if definitivo else
                    'A 180 días aún no hay muestra (la señal más antigua es de feb-2026); '
                    'este 90d es provisional, no el veredicto',
            'acierto_pct': horizonte.get('win_rate'),
            'retorno_medio': horizonte.get('avg_return'),
            'n': horizonte.get('count'),
        },
    }


SYSTEM = """Escribes el briefing diario de inversión de una sola persona, que lo lee
en el móvil. Es inversor value estilo Lynch: busca buenas empresas castigadas por
razones que no sean deterioro del negocio, con ganancias del 5-10% y alta tasa de
acierto. Prefiere que no le digas nada antes que decirle algo dudoso.

Recibes hechos ya calculados y verificados. REDACTAS, NO ANALIZAS: no inventes ni
estimes un solo número, usa solo los que te doy. Si un dato no está, no lo menciones.

Estructura, en este orden y omitiendo lo que esté vacío:
0. Si "datos_incompletos" trae algo, ESA es la primera línea y en negrita: el
   pipeline no terminó y los datos están a medias. No digas "no hay nada que
   comprar" en ese caso — no lo sabes. Di que el análisis no está completo y qué
   falta. Aun así, informa de las tesis rotas si las hay: esas sí son fiables.
1. Qué comprar hoy. Si la lista de comprables viene vacía Y los datos están
   completos, la PRIMERA línea es que hoy no hay nada, sin rodeos ni consuelo.
2. Si hay tesis rotas en posiciones abiertas, van justo después: es lo que más urge.
3. Qué vigilar: baratas que aún caen. Una línea cada una, con el porqué de su caída
   si lo tienes.
4. El régimen de mercado SOLO si te lo paso (significa que cambió hoy).
5. Cierra con el acierto real del sistema como recordatorio de tamaño de posición.

Reglas de escritura — esto importa tanto como el contenido:
- Escribe como le hablarías a un colega por teléfono, en frases completas. NO como
  un informe ni un volcado de campos.
- NUNCA uses nombres de campos técnicos. Traduce lo que significan:
    "fundamental_score se hundió a 44"  →  "ha perdido calidad fundamental"
    "analyst_upside saltó a 31%"        →  "los analistas le ven un 31% de subida,
                                            y ese salto es señal de trampa"
    "rompió el stop en 8140,16"         →  "ha caído por debajo del precio al que
                                            decidiste salirte"
  El dato numérico va después, como apoyo, no como sujeto de la frase.
- Explica la CONSECUENCIA, no solo el hecho: qué significa para él y qué puede hacer.
- Español de España, tono directo. Nada de "¡Buenos días!", emojis decorativos ni
  disclaimers.
- Máximo 12 líneas. Es un móvil.
- HTML de Telegram para el énfasis: <b>negrita</b>. Nada de markdown.
- Si algo está barato pero cayendo, dilo así: barato todavía no es comprable.
- Con el rendimiento del sistema: si "es_horizonte_definitivo" es false, di que la
  cifra es provisional y por qué — no la presentes como el veredicto del sistema."""


def build_message(facts: dict) -> str | None:
    """Texto del briefing. None si Claude no está disponible."""
    prompt = (
        'Escribe el briefing de hoy con estos hechos:\n\n'
        + json.dumps(facts, ensure_ascii=False, indent=1, default=str)
    )
    texto = claude_chat([{'role': 'user', 'content': prompt}],
                        model=MODEL, system=SYSTEM, max_tokens=1200)
    return texto.strip() if texto else None


def _send(text: str) -> bool:
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        print('  Sin credenciales de Telegram — dry run:\n')
        print(text)
        return False
    try:
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=json.dumps({'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML',
                             'disable_web_page_preview': True}).encode(),
            headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=15)
        return True
    except urllib.error.HTTPError as e:
        print(f'  Envío fallido: {e} — {e.read().decode("utf-8", "replace")[:200]}')
        return False
    except Exception as e:
        print(f'  Envío fallido: {e}')
        return False


def main() -> None:
    print('[daily_briefing] Componiendo el briefing del día...')
    facts = gather_facts()
    print(f"  {facts['total_lista']} en lista · {len(facts['comprables'])} comprables · "
          f"{len(facts['vigilar'])} a vigilar · {len(facts['tesis_rotas'])} tesis rotas"
          + (f" · régimen → {facts['regimen_cambio']}" if facts['regimen_cambio'] else ''))

    texto = build_message(facts)
    if not texto:
        print('  Claude no disponible — no se manda nada (el briefing sin redactar no sirve)')
        return

    (DOCS / 'daily_briefing.json').write_text(json.dumps(
        {'fecha': facts['fecha'], 'texto': texto, 'hechos': facts},
        ensure_ascii=False, indent=2, default=str))

    if _send(texto):
        print(f'  ✓ Briefing enviado ({len(texto)} caracteres)')


if __name__ == '__main__':
    main()
