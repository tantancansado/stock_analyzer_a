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
  4. El mercado, SOLO el día que la caída del S&P llega a otro tramo del 5 %
  5. El acierto de Prioridad contra el S&P, cuando haya medida suficiente

Los rebotes siguen avisando por su cuenta: son de 1-5 días y esperar al
briefing les quita el valor.
"""
from __future__ import annotations

import csv
import html
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from groq_utils import claude_chat

DOCS = Path('docs')
TRACKER = DOCS / 'portfolio_tracker'
MODEL = 'claude-sonnet-5'

MAX_CANDIDATOS = 8
MAX_VIGILAR = 5
# Como la conclusión de la tesis (thesis_generator._conclusion_value_us).
RESULTADOS_CERCA_DIAS = 14
# Por debajo, un porcentaje de aciertos es ruido.
MIN_MEDIDAS = 20


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


def _grupos(ruta: Path) -> dict[str, str] | None:
    """{ticker: grupo} de una lista de Value; None si no hay fichero."""
    if not ruta.exists():
        return None
    return {r['ticker']: r.get('value_grupo') or '' for r in _rows(ruta) if r.get('ticker')}


def _grupos_de_la_base(base: set) -> dict[str, str] | None:
    """Los grupos del día que `base_de_comparacion` usó de base: el más reciente,
    hasta tres días atrás, cuya Prioridad es exactamente esa."""
    from new_value_alerts import HISTORY, _load_value_csv
    for delta in (1, 2, 3):
        dia = (date.today() - timedelta(days=delta)).isoformat()
        for ruta in (HISTORY / dia / 'value_opportunities_filtered.csv', HISTORY / dia / 'value_opportunities.csv'):
            if ruta.exists() and _load_value_csv(ruta) == base:
                return _grupos(ruta)
    return None


def con_su_grupo(entran: list[str], salen: list[str], ayer: dict | None,
                 hoy: dict | None) -> tuple[list[str], list[str]]:
    """Las que entran y salen de Prioridad, con dónde estaban o dónde quedan.

    El 20-nov-2026 el briefing llamó «nuevas en la lista» a Autodesk y First
    Citizens, que ayer ya estaban en Observar: lo que pasaba en el texto era
    «entran» sin decir de dónde. Sin el grupo de ayer no se dice nada, porque
    «nueva en la lista» sería inventarlo."""
    def de_donde(t):
        if ayer is None:
            return t
        return f'{t} (ayer en Observar)' if ayer.get(t) == 'OBSERVAR' else f'{t} (nueva en la lista)'

    def a_donde(t):
        if hoy is None:
            return t
        return f'{t} (sigue en Observar)' if hoy.get(t) == 'OBSERVAR' else f'{t} (sale de la lista)'

    return [de_donde(t) for t in entran], [a_donde(t) for t in salen]


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


TRAMO_CAIDA = 5.0
RECUPERADO = 2.5


def mercado_hoy(cierres=None) -> dict | None:
    """Cuánto están el S&P y el Nasdaq bajo su máximo de un año, solo el día que la
    caída del S&P llega a un tramo más hondo (5, 10, 15 %...) que los de esa misma
    caída, y el día que vuelve a menos de un 2,5 % del máximo.

    Hasta el 20-nov-2026 se comparaba el régimen de `market_regime.json` con el de
    ayer, pero ese fichero no se archiva (está en .gitignore): sin «ayer», nunca
    salía, y el mensaje calló una caída del 15 % del Nasdaq. Ahora sale del precio
    y no depende de ningún fichero. Sin precios, nada: no se inventa una caída. El
    Nasdaq no decide cuándo: con tramos en los dos, salía 55 días al año. Y no
    lleva predicción ni consejo: medido el mismo día, la Prioridad comprada con el
    S&P un 8 % o más bajo su máximo le sacó +16 puntos a 12 meses en 2021-25 (el
    resto del tiempo, -3).
    """
    try:
        if cierres is None:
            import yfinance as yf
            cierres = yf.download(['SPY', 'QQQ'], period='26mo', auto_adjust=True,
                                  progress=False)['Close']
        cierres = cierres[['SPY', 'QQQ']].dropna()
    except Exception as exc:
        print(f'  [warn] sin precios del mercado: {exc}')
        return None
    caida = ((1 - cierres / cierres.rolling(252, min_periods=200).max()) * 100).dropna()
    if caida.empty:
        return None
    hondo, hoy = 0, None
    for v in caida['SPY']:
        tramo = int(v // TRAMO_CAIDA)
        if tramo > hondo:
            hondo, hoy = tramo, 'cae'
        elif hondo and v < RECUPERADO:
            hondo, hoy = 0, 'vuelve'
        else:
            hoy = None
    if hoy is None:
        return None
    ultimo = caida.iloc[-1]
    return {'sp500_bajo_su_maximo_pct': round(float(ultimo['SPY']), 1),
            'nasdaq_bajo_su_maximo_pct': round(float(ultimo['QQQ']), 1),
            'maximo_del_sp500': cierres['SPY'].iloc[-252:].idxmax().date().isoformat(),
            'vuelve_cerca_de_maximos': hoy == 'vuelve'}


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
    # El CSV FILTRADO, que es el que ha pasado el gate de Claude. Antes leía
    # `value_opportunities.csv` —el universo entero, sin verificar— y anunciaba
    # como «comprables» picks que el gate nunca había validado.
    #
    # El 16-sep-2026 el briefing mandó NUE (score 35,2) como comprable: no fue
    # rechazada por el gate, es que ni llegó a evaluarse. El gate es
    # fail-CLOSED por diseño —«si Claude no lo valida, no se muestra»— y este
    # camino lo abría de par en par, precisamente en el mensaje que el usuario
    # sí lee todos los días.
    #
    # El filtrado tiene las 164 columnas del otro y 12 más, así que no se
    # pierde ningún campo.
    rows = _rows(DOCS / 'value_opportunities_filtered.csv')

    def _respaldado(detalle):
        # earnings_details es un dict impreso como texto; False = el BPA crece
        # mucho más que el resultado operativo (efecto contable, no negocio).
        txt = str(detalle or '')
        if "'crecimiento_respaldado': False" in txt:
            return False
        if "'crecimiento_respaldado': True" in txt:
            return True
        return None

    def ficha(r):
        f = _ficha(r)
        if r.get('value_grupo'):
            # En Value US el timing es dato de la ficha, no ordena ni veta. Pasado
            # al briefing, la IA lo convertía en «mejor esperar» sobre una de
            # Prioridad (INTU, 11-nov-2026), y un «no puede doblar» en «vale para
            # sumar en caídas». Lo que no está, no se cuenta.
            del f['timing'], f['rs_6m']
            dias = f['dias_a_resultados']
            if dias is None or not 0 <= dias <= RESULTADOS_CERCA_DIAS:
                del f['dias_a_resultados']
            # Una sola cifra de recorrido: la que enseña la fila de Value US. Con
            # cuatro (analistas, triangulado, P/E y DCF) la IA escogía la que quería:
            # el 23-nov, Autodesk «hasta un 50,5 %» (el P/E) con la fila en 26,6, y
            # Paychex «entre 21 y 42 %». Lo que dice puede doblar es el recorrido de
            # nuestros modelos, así que ese va solo con ella.
            f['potencial_pct'] = (f['upside_triangulado'] if f['upside_triangulado'] is not None
                                  else f['upside_analista'])
            if any((f[k] or 0) < 0 for k in ('objetivo_por_pe_pct', 'objetivo_dcf_pct')):
                f['un_modelo_propio_ve_caida'] = True
            for k in ('upside_analista', 'upside_triangulado', 'divergencia',
                      'objetivo_por_pe_pct', 'objetivo_dcf_pct'):
                del f[k]
            # «Viene de un -23,6 % por una guía floja»: era la distancia al máximo del
            # año, y la caída por la guía, según su propio estudio, del 20-22 %.
            f['bajo_su_maximo_del_ultimo_anio_pct'] = f.pop('del_maximo_pct')
            if not f['puede_doblar']:
                del f['puede_doblar'], f['recorrido_de_nuestros_modelos_pct']
        return f

    def _ficha(r):
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
            'dias_a_resultados': _f(r.get('days_to_earnings')),
            'objetivo_por_pe_pct': _f(r.get('target_price_pe_upside_pct')),
            'objetivo_dcf_pct': _f(r.get('target_price_dcf_upside_pct')),
            'beneficio_respaldado_por_negocio': _respaldado(r.get('earnings_details')),
            'grupo': r.get('value_grupo') or '',
            'per_contra_su_historia_sigma': _f(r.get('per_z')),
            'ventas_ultimo_anio_pct': _f(r.get('ventas_anual_pct')),
            'que_le_falta': r.get('value_falta') or '',
            'avisos': r.get('value_avisos') or '',
            'puede_doblar': str(r.get('value_dobla')).strip().lower() == 'true',
            'recorrido_de_nuestros_modelos_pct': _f(r.get('recorrido_propio_pct')),
        }

    if any(r.get('value_grupo') for r in rows):
        # Comprables: el grupo PRIORIDAD (value_bands.nota_value), caiga o no. Dentro de
        # la puerta, lo que cae bajo su media descendente es lo que mejor ha salido;
        # exigir ENTRADA dejaba fuera justo eso. Solo se aparta si la investigación de
        # por qué cae dice que es deterioro.
        comprables = [ficha(r) for r in rows
                      if r.get('value_grupo') == 'PRIORIDAD' and (r.get('why_cheap') or '') != 'DETERIORO']
        comprables.sort(key=lambda x: -(x['score'] or 0))
        # Vigilar: las más baratas de las que aún no tienen la combinación.
        vigilar = [ficha(r) for r in rows if r.get('value_grupo') == 'OBSERVAR']
        vigilar.sort(key=lambda x: -(x['score'] or 0))
    else:
        # Lista anterior a la nota de grupos.
        comprables = [ficha(r) for r in rows
                      if r.get('entry_readiness') == 'ENTRADA'
                      and (r.get('upside_divergence') or '') != 'ALTA'
                      and (r.get('why_cheap') or '') != 'DETERIORO']
        comprables.sort(key=lambda x: -(x['score'] or 0))
        vigilar = [ficha(r) for r in rows
                   if r.get('entry_readiness') in ('ESPERAR', 'VIGILAR')
                   and (_f(r.get('proximity_to_52w_high')) or 0) < -10
                   and (_f(r.get('value_score')) or 0) >= 50]
        vigilar.sort(key=lambda x: x['rs_6m'] or 0)

    drift = _json(TRACKER / 'thesis_drift_alerts.json', {})
    _todas = [
        {'ticker': a.get('ticker'), 'motivo': (a.get('reason') or a.get('motivo') or '')[:160],
         'severidad': a.get('severity') or a.get('severidad') or ''}
        for a in (drift.get('alerts') or drift.get('alertas') or [])
    ]

    # El JSON lleva TODAS las alertas a propósito, porque la página Thesis
    # Drift las muestra. Pero son señales del tracker con status ACTIVE (o
    # sea, de menos de 30 días), NO la cartera del usuario. Sin este filtro el
    # briefing decía "toca cerrar posiciones... TU precio de salida... sal, no
    # esperes" sobre tickers que a lo mejor no tiene — justo el ruido que ya
    # se corrigió en thesis_drift_monitor con el feedback "me llega todos los
    # días y ni la tengo, sobra", pero que aquí seguía colándose.
    en_cartera = None
    try:
        from supabase_positions import fetch_position_rows
        _filas = fetch_position_rows('ticker')
        if _filas is not None:
            en_cartera = {str(f.get('ticker', '')).upper() for f in _filas if f.get('ticker')}
    except Exception as e:
        print(f'  cartera real no disponible ({e}) — las tesis rotas irán sin confirmar')

    if en_cartera is None:
        # No se ha podido comprobar qué tiene: se informa igual, pero el
        # prompt las llamará "señales", no "tus posiciones".
        tesis_rotas, rotas_son_tuyas = _todas[:5], False
    else:
        tesis_rotas = [t for t in _todas if str(t['ticker']).upper() in en_cartera][:5]
        rotas_son_tuyas = True
        print(f'  Tesis rotas: {len(tesis_rotas)}/{len(_todas)} son de posiciones que tienes')

    # El acierto de lo que la app da HOY para comprar: el grupo Prioridad, que
    # existe desde el 7-nov-2026, y contra el S&P. Hasta el 11-nov se contaba
    # `overall` —señales de abril y mayo con la regla anterior y Europa dentro—
    # y el mensaje decía «acierta el 74 % a 180 días, +9 %, cifra definitiva»
    # de una regla que ya no se usa. Sin Europa era igual de alto (74,1 %), pero
    # en esas fechas el S&P subió un 10,1 % y ellas un 11,2 %: un punto. Sin
    # medida suficiente, no se dice nada.
    prioridad = (_json(TRACKER / 'summary.json').get('value_grupos') or {}).get('PRIORIDAD') or {}
    medida = next(({'horizonte': h, 'acierto_pct': s.get('win_rate'),
                    'retorno_medio': s.get('avg_return'), 'contra_sp500': s.get('contra_sp500'),
                    'n': s.get('count')}
                   for h in ('365d', '180d', '90d')
                   for s in [prioridad.get(h) or {}]
                   if (s.get('count') or 0) >= MIN_MEDIDAS), None)

    # Qué acaba de aparecer y qué se ha caído.
    #
    # El paso «New VALUE Picks Alert» del workflow está silenciado
    # delegando en este briefing —«silenciado → daily_briefing»— y es lo
    # correcto, un solo mensaje al día. Pero el briefing nunca recogió esta
    # parte: mandaba la lista entera sin decir cuál es nueva, y saber qué
    # acaba de entrar es justo lo que se le pedía a esa alerta. La
    # funcionalidad se perdió en la consolidación.
    #
    # `base_de_comparacion` devuelve None cuando no hay contra qué comparar
    # —o cuando el día anterior el pipeline no terminó—, y entonces no se
    # dice nada: sin base, «nuevo» no significa nada.
    nuevos, se_van = [], []
    try:
        from new_value_alerts import _load_value_csv, base_de_comparacion
        _base = base_de_comparacion()
        if _base:
            _hoy = _load_value_csv(DOCS / 'value_opportunities_filtered.csv')
            nuevos, se_van = con_su_grupo(sorted(_hoy - _base), sorted(_base - _hoy),
                                          _grupos_de_la_base(_base),
                                          _grupos(DOCS / 'value_opportunities_filtered.csv'))
    except Exception as exc:
        print(f'  [warn] no se pudo comparar con ayer: {exc}')

    return {
        'fecha': date.today().isoformat(),
        'total_lista': len(rows),
        'datos_incompletos': datos_incompletos(rows),
        'picks_nuevos': nuevos,
        'picks_que_se_van': se_van,
        'comprables': comprables[:MAX_CANDIDATOS],
        'vigilar': vigilar[:MAX_VIGILAR],
        # Sin el total, «para vigilar quedan [las cinco]» decía que no había más (había 20).
        'vigilar_total': len(vigilar),
        'tesis_rotas': tesis_rotas,
        'rotas_son_tuyas': rotas_son_tuyas,
        'mercado': mercado_hoy(),
        **({'rendimiento_prioridad': medida} if medida else {}),
    }


SYSTEM = """Escribes el briefing diario de inversión de una sola persona, que lo lee
en el móvil. Es inversor value estilo Lynch: busca buenas empresas castigadas por
razones que no sean deterioro del negocio, con ideas de convicción a 12 meses; vende a precio
objetivo, no a un porcentaje. Prefiere que no le digas nada antes que decirle algo dudoso.

Recibes hechos ya calculados y verificados. REDACTAS, NO ANALIZAS: no inventes ni
estimes un solo número, usa solo los que te doy. Si un dato no está, no lo menciones.

Estructura, en este orden y omitiendo lo que esté vacío:
0. Si "datos_incompletos" trae algo, ESA es la primera línea y en negrita: el
   pipeline no terminó y los datos están a medias. No digas "no hay nada que
   comprar" en ese caso — no lo sabes. Di que el análisis no está completo y qué
   falta. Aun así, informa de las tesis rotas si las hay: esas sí son fiables.
1. Qué comprar hoy: las de "comprables", que son las del grupo Prioridad de la app.
   Ese es el veredicto de la casa y no lo cambias: son comprables. NUNCA escribas
   «mejor esperar», «no hay prisa», «espera a los resultados» ni «sumar en caídas»,
   ni pongas condiciones o precios de entrada, stops o soportes. Si la lista de
   comprables viene vacía Y los datos están completos, la PRIMERA línea es que hoy
   no hay nada, sin rodeos ni consuelo.
2. Si hay tesis rotas, van justo después: es lo que más urge. OJO con cómo las
   llamas: si `rotas_son_tuyas` es true son posiciones que el usuario TIENE y
   puedes decir "sal" o "cierra"; si es false NO se ha podido confirmar que las
   tenga, así que di "la señal de X se ha roto" y nunca "tu posición" ni "sal".
   En cada comprable di, si vienen, como hechos y en media frase: que presenta
   resultados en N días ("dias_a_resultados"), sus "avisos", si
   "un_modelo_propio_ve_caida" (uno de nuestros dos modelos le ve caída), y si
   "beneficio_respaldado_por_negocio" es false (el beneficio crece más que el
   negocio: no lo vendas como calidad). Son datos que debe saber; no cambian el
   veredicto.
   Su recorrido es "potencial_pct", el mismo que enseña la app: di ese y ningún
   otro, sin rangos ni cuentas. En las que pueden doblar, el que lo dice es
   "recorrido_de_nuestros_modelos_pct".
   "bajo_su_maximo_del_ultimo_anio_pct" es cuánto está por debajo de su máximo del
   año, no lo que cayó por la causa: no los juntes en una cifra. De
   "por_que_cae_detalle" cuenta la causa, no sus números.
3. Qué vigilar: las de "vigilar", del grupo Observar: baratas a las que les falta
   algo para Prioridad ("que_le_falta"). Una sola línea para todas, con lo que les
   falta en pocas palabras. No digas que «siguen cayendo»: no es el motivo.
   Son las más baratas de "vigilar_total": si este es mayor, dilo («las cinco más
   baratas de las 20 en Observar») y nunca «quedan» ni «solo», que dan a entender
   que no hay más. Lo que les falta, dilo de las que lo tienen en común; no
   atribuyas a todas lo de unas pocas.
4. Lo que ha ENTRADO hoy en Prioridad (`picks_nuevos`) y lo que ha SALIDO de ella
   (`picks_que_se_van`), si los hay. Cada uno dice entre paréntesis de dónde viene
   o dónde queda: «ayer en Observar» es que sube de grupo («sube a Prioridad», nunca
   «nueva en la lista», porque ya estaba en ella); «nueva en la lista» es que no
   estaba; «sigue en Observar» es que baja de grupo; «sale de la lista», que sale.
   Una línea, sin repetir lo que ya has dicho arriba: es lo que cambia respecto a
   ayer y por eso importa. Si las dos
   listas vienen vacías, no menciones el tema — que no haya movimiento no es
   noticia. Si el campo no viene, tampoco: significa que no había con qué
   comparar, no que nada se haya movido.
5. El mercado SOLO si viene `mercado` (hoy la caída del S&P desde su máximo llega a
   otro tramo del 5 %, o ha vuelto cerca de él): una frase con cuánto están por
   debajo y desde cuándo, y que la regla no cambia por eso: lo de Prioridad se compra
   igual. Ni predicciones, ni «esperar», ni «proteger capital».
6. Si viene "rendimiento_prioridad", cierra con él en una frase: aciertos y
   resultado medio de las de Prioridad a ese plazo, y cuánto le sacan al S&P 500
   ("contra_sp500"). Si no viene, no hables del acierto del sistema: la regla de
   hoy aún no tiene medición y cualquier otra cifra es de otra regla.

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
- Las cifras, como vienen o sin decimales; nada de «más de un 150 %» ni de cuentas
  tuyas («falla un 26 %» de un 73,5 % de acierto). Un porcentaje que no esté en los
  hechos hace que el mensaje no se mande.
- Máximo 12 líneas. Es un móvil.
- HTML de Telegram para el énfasis: <b>negrita</b>. Nada de markdown.
- Si un dato no viene, no lo deduzcas de que falta: que no venga "puede_doblar" no
  significa que no pueda doblar."""

# Lo que convierte un aviso en un «todavía no compres». La casa dice comprable y
# el mensaje no puede decir otra cosa, como la tesis
# (thesis_generator.tesis_contradice_a_la_casa). «No esperes» y el precio de
# salida sí valen: es lo que se dice de una tesis rota.
_CONTRADICE = re.compile(
    r'\b(?:mejor|conviene|toca|hay que|habría que)\s+esperar\b'
    r'|\bno hay prisa\b|\bsin prisa\b'
    r'|\besperar?\s+a\s+(?:ver|que|los resultados|el trimestre|la reacción)'
    r'|\ben (?:las )?caídas\b'
    r'|\bsoportes?\b|medias?\s+móvil', re.I)


def contradice_a_la_casa(texto: str) -> str | None:
    m = _CONTRADICE.search(texto or '')
    return f'«{m.group(0)}»' if m else None


# «No inventes ni estimes un solo número», y el 23-nov puso «PAYX entre 21 % y 42 %»
# y «Autodesk hasta un 50,5 %», cifras que no estaban en lo que la app enseña.
# Cada porcentaje del texto tiene que estar en los hechos, sin más cambio que
# quitarle decimales: «70 %» vale por un 70,8 o un -70,2.
_PORCENTAJE = re.compile(r'(\d+(?:[.,]\d+)?)\s*%')
_NUMERO = re.compile(r'\d+(?:[.,]\d+)?')


def _numeros(x) -> list[float]:
    if isinstance(x, bool) or x is None:
        return []
    if isinstance(x, (int, float)):
        return [abs(float(x))]
    if isinstance(x, dict):
        return [n for v in x.values() for n in _numeros(v)]
    if isinstance(x, (list, tuple)):
        return [n for v in x for n in _numeros(v)]
    return [float(m.replace(',', '.')) for m in _NUMERO.findall(str(x))]


def cifra_que_no_esta(texto: str, facts: dict) -> str | None:
    conocidos = _numeros(facts)
    for m in _PORCENTAJE.finditer(texto or ''):
        escrito = m.group(1).replace(',', '.')
        margen = 0.051 if '.' in escrito else 0.99
        if not any(abs(float(escrito) - v) <= margen for v in conocidos):
            return f'«{m.group(0)}» no está en los datos'
    return None


def _plantilla(facts: dict) -> str:
    """Sin redactar, para cuando lo redactado contradice a la lista."""
    def nombres(fichas):
        return ', '.join(html.escape(f.get('empresa') or f.get('ticker') or '') for f in fichas)

    lineas = []
    if facts['datos_incompletos']:
        lineas.append('<b>El análisis de hoy no está completo:</b> '
                      + html.escape('; '.join(facts['datos_incompletos'])) + '.')
    elif facts['comprables']:
        lineas.append(f"<b>Prioridad hoy:</b> {nombres(facts['comprables'])}.")
    else:
        lineas.append('<b>Hoy no hay nada que comprar.</b>')
    if facts['tesis_rotas']:
        quien = 'en tu cartera' if facts['rotas_son_tuyas'] else 'en las señales'
        lineas.append(f'Tesis rota {quien}: '
                      + ', '.join(html.escape(str(t['ticker'])) for t in facts['tesis_rotas']) + '.')
    if facts['vigilar']:
        total = facts.get('vigilar_total') or len(facts['vigilar'])
        de = f" ({len(facts['vigilar'])} de {total})" if total > len(facts['vigilar']) else ''
        lineas.append(f"Observar{de}: {nombres(facts['vigilar'])}.")
    if facts['picks_nuevos']:
        lineas.append('Entran en Prioridad: ' + ', '.join(map(html.escape, facts['picks_nuevos'])) + '.')
    if facts['picks_que_se_van']:
        lineas.append('Salen de Prioridad: ' + ', '.join(map(html.escape, facts['picks_que_se_van'])) + '.')
    return '\n'.join(linea.replace('..', '.') for linea in lineas)


def build_message(facts: dict) -> str | None:
    """Texto del briefing. None si ni Claude ni Groq están disponibles; la
    plantilla si lo que redactan contradice a la lista."""
    prompt = (
        'Escribe el briefing de hoy con estos hechos:\n\n'
        + json.dumps(facts, ensure_ascii=False, indent=1, default=str)
    )
    redactado = False
    for nombre, redacta in (('Claude', _con_claude), ('Groq', _con_groq)):
        texto = redacta(prompt)
        if not texto:
            continue
        redactado = True
        motivo = contradice_a_la_casa(texto) or cifra_que_no_esta(texto, facts)
        if not motivo:
            return texto
        print(f'  ⚠️  el briefing de {nombre} no vale ({motivo}): no se manda')
    return _plantilla(facts) if redactado else None


def _con_claude(prompt: str) -> str | None:
    # max_tokens cubre pensamiento + respuesta: con adaptive thinking (que
    # claude_chat activa en los modelos de la generación 5) un presupuesto
    # ajustado se lo come el pensamiento y el mensaje sale truncado.
    # `esencial=True`: es el único mensaje del día, así que pasa aunque quede
    # poco margen en el tope mensual (ver claude_budget.RESERVA_USD).
    texto = claude_chat([{'role': 'user', 'content': prompt}],
                        model=MODEL, system=SYSTEM, max_tokens=4000, esencial=True)
    return texto.strip() if texto else None


def _con_groq(prompt: str) -> str | None:
    # Sin Claude (tope agotado, API caída o sin key) el briefing NO se pierde:
    # esto es redacción sobre hechos que la app ya tiene calculados, no requiere
    # búsqueda web ni fuentes verificadas, así que Groq lo hace igual de bien y
    # gratis. Se reserva Claude para lo que solo Claude puede hacer.
    try:
        api_key = os.environ.get('GROQ_API_KEY', '')
        if not api_key:
            return None
        from groq import Groq
        from groq_utils import groq_chat
        texto = groq_chat(Groq(api_key=api_key),
                          [{'role': 'system', 'content': SYSTEM},
                           {'role': 'user', 'content': prompt}],
                          max_tokens=2000)
        return texto.strip() if texto else None
    except Exception as e:
        print(f'   ⚠️  Groq tampoco disponible para el briefing: {e}')
        return None


def publicable(texto: str, facts: dict) -> dict:
    """Lo que va a docs/, que es público. Las tesis rotas filtradas por la
    cartera real son posiciones del usuario, y el texto las nombra: ese día solo
    se publica cuántas hay."""
    if facts.get('tesis_rotas') and facts.get('rotas_son_tuyas') is not False:
        return {'fecha': facts['fecha'], 'texto': None,
                'hechos': {**facts, 'tesis_rotas': len(facts['tesis_rotas'])}}
    return {'fecha': facts['fecha'], 'texto': texto, 'hechos': facts}


def _send(text: str) -> bool:
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        # Sin imprimir el texto: nombra posiciones reales y los logs son públicos
        print(f'  Sin credenciales de Telegram — dry run ({len(text)} caracteres)')
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
          + (f" · mercado: S&P -{facts['mercado']['sp500_bajo_su_maximo_pct']} %, Nasdaq "
             f"-{facts['mercado']['nasdaq_bajo_su_maximo_pct']} %" if facts.get('mercado') else ''))

    # Va delante y fuera de Claude: es lo más urgente, ya viene redactado y
    # nombra posiciones reales, así que tampoco entra en daily_briefing.json,
    # que se publica. Sin briefing ese día, el aviso se manda solo.
    from portfolio_price_alerts import bloque_del_dia
    venta = bloque_del_dia()

    texto = build_message(facts)
    if not texto:
        print('  Ni Claude ni Groq disponibles — no se manda nada (el briefing sin redactar no sirve)')
        if venta and _send(venta):
            print('  ✓ Aviso de venta enviado solo')
        return

    # Aviso de saldo/tope AL FINAL del mensaje. Va aquí y no en un canal aparte
    # porque el briefing es lo único que el usuario lee a diario: un tope que se
    # agota en los logs de CI es un fallo silencioso, que es el patrón nº1 de
    # este repo. Solo habla cuando hay algo que contar (sin saldo, tope
    # alcanzado o >80%); en uso normal no añade ruido.
    try:
        from claude_budget import linea_para_briefing
        aviso = linea_para_briefing()
        if aviso:
            texto = f'{texto}\n\n{aviso}'
            print(f'  ⚠️  aviso de presupuesto añadido: {aviso[:60]}')
    except Exception as e:
        print(f'  (no se pudo leer el estado de presupuesto: {e})')

    (DOCS / 'daily_briefing.json').write_text(json.dumps(
        publicable(texto, facts), ensure_ascii=False, indent=2, default=str))

    if _send(f'{venta}\n\n{texto}' if venta else texto):
        print(f'  ✓ Briefing enviado ({len(texto)} caracteres)'
              + (' con aviso de venta' if venta else ''))


if __name__ == '__main__':
    main()
