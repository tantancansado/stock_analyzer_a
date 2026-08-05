#!/usr/bin/env python3
"""
Coherence Check — cruza lo que el pipeline acaba de publicar consigo mismo.

Por qué existe: los tests de este repo comprueban que cada pieza hace lo que su
autor pensó, y por eso los tres bugs graves del 5-ago-2026 pasaron desapercibidos
durante meses. Ninguno estaba DENTRO de una pieza; los tres estaban ENTRE piezas:

  - la app mostraba ENTRA en 11 valores cuyo propio timing decía VIGILAR
  - el filtro de score dejaba pasar tickers por debajo del umbral elegido
  - los ratios de los ADR mezclaban la divisa del flujo con la de la cotización

Un test unitario no encuentra una contradicción entre dos fuentes. Esto sí:
compara los ficheros publicados unos con otros y sale con código 1 si algo no
cuadra, para que el fallo se vea en el pipeline en vez de llegar a la app.

Se ejecuta al final de daily-analysis.yml. No arregla nada: informa. Arreglar
automáticamente escondería el problema, que es justo cómo llegamos aquí.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

DOCS = Path('docs')


def _rows(nombre: str) -> list[dict]:
    p = DOCS / nombre
    if not p.exists():
        return []
    try:
        with p.open(newline='') as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def _json(nombre: str):
    p = DOCS / nombre
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _f(x):
    try:
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


# ── Comprobaciones ────────────────────────────────────────────────────────────
# Cada una devuelve una lista de problemas. Lista vacía = todo cuadra.

def entry_verdicts_vs_timing(value: list[dict], verdicts: list[dict]) -> list[str]:
    """Un ENTRY del badge no puede contradecir el timing de la propia ficha."""
    timing = {r['ticker']: (r.get('entry_readiness') or '').strip()
              for r in value if r.get('ticker')}
    malos = []
    for v in verdicts:
        if v.get('verdict') != 'ENTRY':
            continue
        t = v.get('ticker', '')
        if timing.get(t) and timing[t] != 'ENTRADA':
            malos.append(f'{t}: el badge dice ENTRY y su timing dice {timing[t]}')
    return malos


def entry_verdicts_vs_valoracion(value: list[dict], verdicts: list[dict]) -> list[str]:
    """Un ENTRY no puede llevar la valoración triangulada en negativo."""
    tri = {r['ticker']: (r.get('upside_divergence'), _f(r.get('upside_triangulated_pct')))
           for r in value if r.get('ticker')}
    malos = []
    for v in verdicts:
        if v.get('verdict') != 'ENTRY':
            continue
        div, t = tri.get(v.get('ticker', ''), (None, None))
        if div == 'ALTA' and t is not None and t < 0:
            malos.append(f"{v['ticker']}: ENTRY con valoración triangulada {t:.0f}%")
    return malos


def score_bajo_el_corte(value: list[dict], minimo: float) -> list[str]:
    """Nada por debajo del corte de calidad debería estar publicado."""
    return [f"{r['ticker']}: score {_f(r.get('value_score')):.1f} < {minimo:.0f}"
            for r in value
            if (_f(r.get('value_score')) or 999) < minimo]


def ratios_imposibles(value: list[dict]) -> list[str]:
    """FCF yield de dos dígitos altos = divisa sin convertir (caso ATLKY)."""
    return [f"{r['ticker']}: FCF yield {_f(r.get('fcf_yield_pct')):.1f}%"
            for r in value
            if (_f(r.get('fcf_yield_pct')) or 0) > 20]


def etiqueta_ml_vs_probabilidad(value: list[dict]) -> list[str]:
    """Una etiqueta ALTA con menos del 55% de probabilidad miente."""
    return [f"{r['ticker']}: etiqueta ALTA con probabilidad {_f(r.get('ml_win_probability')):.2f}"
            for r in value
            if r.get('ml_win_label') == 'ALTA'
            and (_f(r.get('ml_win_probability')) or 1) < 0.55]


def leaps_vs_why_cheap(value: list[dict], leaps: list[dict]) -> list[str]:
    """Dos IAs distintas opinando lo contrario del mismo negocio.

    leaps_analyzer.py clasifica `situation` con la misma escala que
    why_cheap_analyzer.py: DETERIORO significa "el negocio empeora, no es
    ciclo" en ambos. Si LEAPS publica un ticker como CAIDA_CIRCUNSTANCIAL/
    CALIDAD_RAZONABLE/DIP_GANADOR (negocio intacto) mientras VALUE, para el
    MISMO ticker, dice why_cheap=DETERIORO, una de las dos IAs está mal o
    trabajando con datos distintos — no debería publicarse sin más.
    """
    why_cheap_por_ticker = {
        (r.get('ticker') or '').upper(): (r.get('why_cheap') or '').upper()
        for r in value if r.get('ticker')
    }
    no_deterioro = {'CAIDA_CIRCUNSTANCIAL', 'CALIDAD_RAZONABLE', 'DIP_GANADOR'}
    problemas = []
    for o in leaps:
        ticker = (o.get('ticker') or '').upper()
        situation = (o.get('situation') or '').upper()
        why_cheap = why_cheap_por_ticker.get(ticker)
        if situation in no_deterioro and why_cheap == 'DETERIORO':
            problemas.append(
                f"{ticker}: LEAPS dice {situation} pero VALUE dice why_cheap=DETERIORO")
    return problemas


def postmortem_vs_tracker_summary(postmortem: dict | None, summary: dict | None,
                                  tolerancia_pts: float = 5.0) -> list[str]:
    """El win rate que reporta el postmortem debe coincidir con el del tracker.

    Ambos analizan, en teoría, la misma pregunta ("¿cuánto acierta el sistema
    a este horizonte?"). El 5-ago-2026 signal_postmortem.py no aplicaba el
    corte CLEAN_FROM que portfolio_tracker.py sí aplica en 'overall' —
    analizaba 1489 señales (con el periodo contaminado pre-abril) y publicaba
    55.1% de acierto, contradiciendo el 35.8%/134 oficial del tracker para la
    misma ventana. Ver signal_postmortem.py y portfolio_tracker.py CLEAN_FROM.
    """
    if not postmortem or not summary:
        return []
    resumen = postmortem.get('resumen') or {}
    horizonte = str(resumen.get('horizonte') or '')  # 'return_90d' → '90d'
    if not horizonte.startswith('return_'):
        return []
    clave = horizonte.removeprefix('return_')
    tracker_win = ((summary.get('overall') or {}).get(clave) or {}).get('win_rate')
    pm_win = resumen.get('win_rate')
    if tracker_win is None or pm_win is None:
        return []
    diff = abs(float(pm_win) - float(tracker_win))
    if diff > tolerancia_pts:
        return [f'postmortem dice {pm_win}% de acierto a {clave}, '
                f'el tracker dice {tracker_win}% — diferencia de {diff:.1f}pts']
    return []


def leaps_precio_vs_value(value: list[dict], value_eu: list[dict], leaps: list[dict],
                          umbral_pct: float = 8.0) -> list[str]:
    """El spot de LEAPS y el current_price de VALUE deberían ser casi el mismo precio.

    OJO con el ticker: LEAPS solo opera sobre el listing US con opciones
    (p.ej. 'SAP', el ADR en NYSE) — nunca sobre el listing europeo ('SAP.DE',
    Fráncfort, cotiza en EUR). Comparar 'SAP' de LEAPS contra 'SAP.DE' de la
    lista EU no es un dato obsoleto, es una divisa distinta (verificado:
    spot LEAPS 193.57 vs SAP.DE 167.38 = básicamente el tipo de cambio
    EUR/USD, no un desajuste real). Por eso el cruce es SOLO por ticker
    exacto — si no hay ese ticker exacto en ninguna de las dos listas
    VALUE, no se compara nada en vez de adivinar con el ticker equivocado.
    """
    precio_value = {r['ticker']: _f(r.get('current_price'))
                    for r in (value + value_eu) if r.get('ticker')}
    problemas = []
    for o in leaps:
        ticker = o.get('ticker') or ''
        spot = _f(o.get('spot'))
        precio = precio_value.get(ticker)
        if spot is None or precio is None or precio <= 0:
            continue
        diff_pct = abs(spot - precio) / precio * 100
        if diff_pct > umbral_pct:
            problemas.append(
                f'{ticker}: LEAPS spot {spot:.2f} vs VALUE current_price {precio:.2f} '
                f'({diff_pct:.1f}% de diferencia)')
    return problemas


def commodity_rating_vs_narrativa(commodities: list[dict]) -> list[str]:
    """value_rating (determinista) contra ai_narrative_veredicto (Claude+búsqueda).

    Un commodity CARO no debería salir con veredicto OPORTUNIDAD_ESTRUCTURAL,
    ni uno MUY_ATRACTIVO/ATRACTIVO con TRAMPA_DE_VALOR — mismo modelo de
    contradicción que ya cazaba `entry_verdicts_vs_valoracion`, aplicado a
    `enrich_commodity_narrative.py`.
    """
    problemas = []
    for r in commodities:
        ticker = r.get('ticker') or r.get('sector') or '?'
        rating = (r.get('value_rating') or '').upper()
        veredicto = (r.get('ai_narrative_veredicto') or '').upper()
        if not veredicto or veredicto == 'SIN_DATOS':
            continue
        if rating == 'CARO' and veredicto == 'OPORTUNIDAD_ESTRUCTURAL':
            problemas.append(f'{ticker}: value_rating=CARO pero ai_narrative_veredicto=OPORTUNIDAD_ESTRUCTURAL')
        elif rating in ('MUY_ATRACTIVO', 'ATRACTIVO') and veredicto == 'TRAMPA_DE_VALOR':
            problemas.append(f'{ticker}: value_rating={rating} pero ai_narrative_veredicto=TRAMPA_DE_VALOR')
    return problemas


def columnas_obligatorias(value: list[dict], nombre_csv: str = 'value_opportunities.csv') -> list[str]:
    """Un scoring a medias no puede publicarse como si estuviera completo.

    El 5-ago-2026 esto solo se comprobaba en la lista US: las 36 filas de la
    europea llevaban meses sin entry_readiness/ma_filter_pass/tech_stage y
    nadie lo veía porque este guard no la miraba.
    """
    if not value:
        return [f'{nombre_csv} está vacío']
    obligatorias = ('ticker', 'value_score', 'current_price', 'entry_readiness')
    return [f'{nombre_csv}: la columna {c} está vacía en las {len(value)} filas'
            for c in obligatorias
            if not any((r.get(c) or '').strip() for r in value)]


def run() -> int:
    print('[coherence_check] Cruzando lo publicado consigo mismo...')

    value = _rows('value_opportunities.csv')
    value_eu = _rows('european_value_opportunities.csv')
    verdicts = _rows('entry_verdicts.csv')
    leaps_data = _json('leaps_opportunities.json')
    leaps = leaps_data.get('opportunities', []) if isinstance(leaps_data, dict) else []
    commodities = _rows('commodity_opportunities.csv')
    postmortem = _json('signal_postmortem.json')
    tracker_summary = _json('portfolio_tracker/summary.json')

    try:
        from value_bands import VALUE_SCORE_MIN
    except ImportError:
        VALUE_SCORE_MIN = 30.0

    comprobaciones = [
        ('badge ENTRY contra el timing de la ficha (US)', entry_verdicts_vs_timing(value, verdicts)),
        ('badge ENTRY contra el timing de la ficha (EU)', entry_verdicts_vs_timing(value_eu, verdicts)),
        ('badge ENTRY contra la valoración propia (US)',  entry_verdicts_vs_valoracion(value, verdicts)),
        ('badge ENTRY contra la valoración propia (EU)',  entry_verdicts_vs_valoracion(value_eu, verdicts)),
        ('corte de calidad (US)',                    score_bajo_el_corte(value, VALUE_SCORE_MIN)),
        ('corte de calidad (EU)',                    score_bajo_el_corte(value_eu, VALUE_SCORE_MIN)),
        ('ratios imposibles — divisa (US)',          ratios_imposibles(value)),
        ('ratios imposibles — divisa (EU)',          ratios_imposibles(value_eu)),
        ('etiqueta ML contra su probabilidad',       etiqueta_ml_vs_probabilidad(value)),
        ('columnas obligatorias (US)',                columnas_obligatorias(value, 'value_opportunities.csv')),
        ('columnas obligatorias (EU)',                columnas_obligatorias(value_eu, 'european_value_opportunities.csv')),
        ('LEAPS contra why_cheap de VALUE (US)',      leaps_vs_why_cheap(value, leaps)),
        ('LEAPS contra why_cheap de VALUE (EU)',      leaps_vs_why_cheap(value_eu, leaps)),
        ('commodities: rating contra narrativa IA',   commodity_rating_vs_narrativa(commodities)),
        ('postmortem contra el win rate del tracker', postmortem_vs_tracker_summary(postmortem, tracker_summary)),
        ('precio LEAPS contra precio VALUE',           leaps_precio_vs_value(value, value_eu, leaps)),
    ]

    total = 0
    for nombre, problemas in comprobaciones:
        if problemas:
            total += len(problemas)
            print(f'\n  ❌ {nombre}: {len(problemas)}')
            for p in problemas[:8]:
                print(f'       {p}')
            if len(problemas) > 8:
                print(f'       ...y {len(problemas) - 8} más')
        else:
            print(f'  ✓ {nombre}')

    informe = {
        'total_problemas': total,
        'detalle': {n: p for n, p in comprobaciones if p},
        'tickers_value': len(value),
        'tickers_verdicts': len(verdicts),
    }
    (DOCS / 'coherence_check.json').write_text(
        json.dumps(informe, ensure_ascii=False, indent=2))

    if total:
        print(f'\n🚨 {total} incoherencias entre lo que publica la app y sus propios datos')
        return 1
    print('\n✓ Sin contradicciones entre las fuentes publicadas')
    return 0


if __name__ == '__main__':
    sys.exit(run())
