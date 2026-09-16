#!/usr/bin/env python3
"""Caché de veredictos del gate de datos.

El gate pregunta a Claude si las cifras de un pick son plausibles, y lo hacía
UNA VEZ POR TICKER Y POR DÍA. Pero los picks de valor no rotan a diario:
medido sobre septiembre de 2026, de 422 verificaciones **363 eran tickers ya
vistos el día anterior — el 86% era trabajo repetido**. Y los datos que audita
(ROE, margen, deuda, crecimiento) solo cambian cuando hay resultados, o sea una
vez por trimestre.

Peor que el coste: el gate es fail-CLOSED. Cuando se acababa el presupuesto,
`claude_chat` devolvía None, el pick salía como "no verificado" y
value_opportunities_filtered.csv se quedaba VACÍO. Value US — la página
principal — lleva sin datos desde el 11-sep por eso.

La caché arregla las dos cosas:

  · si el dato no ha cambiado, no se vuelve a preguntar
  · si no hay saldo, el veredicto anterior sobre ESE MISMO dato sigue siendo
    válido, así que la app no se vacía

Lo segundo no es una trampa: un veredicto dice "estas cifras son plausibles".
Si las cifras son idénticas, el veredicto lo sigue siendo. Lo que caduca no es
la respuesta, es el dato — y por eso la clave es una huella del dato, no el
ticker.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ESTADO = Path(__file__).parent / 'docs' / 'ai_verdicts_cache.json'

# Aunque el dato no cambie, nada se da por verificado más de esto. Un trimestre
# sería el ciclo natural (los fundamentales cambian con los resultados), pero
# 30 días fuerza un repaso mensual por si el criterio del auditor cambia o la
# empresa hace algo que no se refleja en estas cifras.
TTL_DIAS = 30

# ── Cómo se agrupa cada campo ────────────────────────────────────────────────
#
# Medido sobre los 32 días de `docs/history` (1.488 pares ticker-día), el
# acierto real de esta caché era del **16%**, no del 86% que decía el diseño.
# Ese 86% contaba TICKERS que se repetían; lo que decide es que se repita la
# HUELLA, y casi nunca se repetía.
#
# El culpable, campo a campo:
#
#     analyst_upside_pct   cambiaba de banda el 75% de los días
#     pct_from_52w_high                       el 69%
#     fcf_yield_pct                           el 39%
#     current_price                           el 21%
#     roe / margen / deuda                  el 0-1%   ← como estaba previsto
#
# El fallo estaba en aplicar una banda RELATIVA del 5% a magnitudes que ya son
# porcentajes. Un 5% relativo sobre un precio de 267 son 13 puntos —el precio
# casi nunca los cruza—, pero sobre un upside de 16,7 son 0,8 puntos, que los
# cruza cualquier movimiento diario. Cuanto más pequeño el número, más sensible
# la banda: exactamente al revés de lo que hace falta.
#
# Y no era solo dinero. La caché existe sobre todo para que el gate fail-closed
# no vacíe la página cuando falla la API o se acaba el saldo: con un 16% de
# acierto, el 84% de los picks no tenía veredicto al que caer. Por ahí se cayó
# MCO el 16-sep-2026 —score 83,1, el más alto de la lista— que había pasado el
# gate el día anterior.
#
# Con bandas ABSOLUTAS para los porcentajes el acierto sube al 55%. Los cortes
# del upside caen además en 10/25/30, que son las fronteras que de verdad
# significan algo (`value_bands`), así que un pick no puede cambiar de banda
# dorada sin invalidar su veredicto.

# Bandas absolutas, en las unidades del propio campo (puntos porcentuales,
# salvo deuda/capital que es un ratio).
_CAMPOS_EN_BANDAS_ABSOLUTAS = {
    'roe': 5.0,
    'profit_margin': 5.0,
    'debt_to_equity': 0.5,
    'rev_growth': 5.0,
    'fcf_yield_pct': 1.0,
    'analyst_upside_pct': 5.0,
    'pct_from_52w_high': 5.0,
}

# Precios: aquí sí, una banda relativa del 5%. Un precio no tiene escala
# natural —hay acciones a 17 y a 2.800— y lo que importa es el movimiento
# proporcional.
_CAMPOS_EN_BANDAS = ('current_price', 'target_price_analyst')
BANDA_PCT = 5.0


def _num(v):
    try:
        f = float(v)
        return None if f != f else f     # NaN fuera
    except (TypeError, ValueError):
        return None


def _banda(v):
    """Índice de la banda del 5% en la que cae un número.

    Rejilla FIJA en escala logarítmica, no un paso derivado del propio valor:
    con `floor(f / (f*0.05))` cada número caía en su propia banda —el paso se
    encogía con él— y la caché no acertaba nunca. Con log, dos precios dentro
    del mismo 5% dan el mismo índice sea cual sea su magnitud.

    Devuelve un entero (el índice), no el valor redondeado: lo único que
    importa es si dos filas caen en la misma banda.
    """
    f = _num(v)
    if f is None:
        return None
    if f == 0:
        return 0
    import math
    signo = -1 if f < 0 else 1
    return signo * math.floor(math.log(abs(f)) / math.log(1 + BANDA_PCT / 100))


def _banda_absoluta(v, paso: float):
    """Índice de la banda de ancho `paso` en las unidades del propio campo.

    Un ROE del 26,3% y otro del 27,1% caen en la misma (paso 5), y el auditor
    diría lo mismo de los dos. La banda RELATIVA que había antes los separaba,
    porque un 5% de 26,3 es 1,3 puntos.
    """
    f = _num(v)
    if f is None:
        return None
    import math
    return int(math.floor(f / paso))


def huella(ticker_data: dict) -> str:
    """Identidad del DATO auditado, no del ticker.

    Si dos filas dan la misma huella, el auditor vería exactamente el mismo
    prompt, así que su veredicto sería el mismo. Los campos son los que entran
    en `_prompt_data_check`: cambiar ese prompt obliga a revisar esto.
    """
    partes = [str(ticker_data.get('ticker', '')).upper().strip(),
              str(ticker_data.get('sector', '') or '').strip()]
    for c, paso in _CAMPOS_EN_BANDAS_ABSOLUTAS.items():
        v = _banda_absoluta(ticker_data.get(c), paso)
        partes.append('n/d' if v is None else str(v))
    for c in _CAMPOS_EN_BANDAS:
        v = _banda(ticker_data.get(c))
        partes.append('n/d' if v is None else str(v))
    n = _num(ticker_data.get('analyst_count'))
    partes.append('n/d' if n is None else str(int(n)))
    return '|'.join(partes)


def _cargar() -> dict:
    if not ESTADO.exists():
        return {}
    try:
        d = json.loads(ESTADO.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _guardar(d: dict) -> None:
    try:
        ESTADO.parent.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps(d, indent=1, sort_keys=True))
    except Exception as e:
        print(f'   ⚠️  No se pudo guardar la caché de veredictos: {e}')


def buscar(ticker_data: dict, ahora: datetime | None = None):
    """(verificado, aviso, fecha) si hay veredicto vigente; None si no."""
    entrada = _cargar().get(huella(ticker_data))
    if not entrada:
        return None
    try:
        visto = datetime.fromisoformat(entrada['fecha'])
    except Exception:
        return None
    if visto.tzinfo is None:
        visto = visto.replace(tzinfo=timezone.utc)
    ahora = ahora or datetime.now(timezone.utc)
    if ahora - visto > timedelta(days=TTL_DIAS):
        return None
    return bool(entrada.get('ok')), entrada.get('aviso') or None, entrada['fecha'][:10]


def guardar(ticker_data: dict, ok: bool, aviso: str | None,
            ahora: datetime | None = None) -> None:
    """Registra un veredicto recién obtenido.

    Solo se guardan los veredictos REALES. Un "no se pudo verificar" por falta
    de saldo o por API caída no es un veredicto: guardarlo congelaría el fallo
    durante 30 días y dejaría el pick fuera sin que nadie volviera a mirarlo.
    """
    d = _cargar()
    d[huella(ticker_data)] = {
        'ticker': str(ticker_data.get('ticker', '')).upper().strip(),
        'ok': bool(ok),
        'aviso': aviso or '',
        'fecha': (ahora or datetime.now(timezone.utc)).isoformat(),
    }
    _purgar(d, ahora)
    _guardar(d)


def _purgar(d: dict, ahora: datetime | None = None) -> None:
    """Fuera lo caducado, para que el fichero no crezca sin fin."""
    ahora = ahora or datetime.now(timezone.utc)
    for k in [k for k, v in d.items() if _caducada(v, ahora)]:
        d.pop(k, None)


def _caducada(entrada: dict, ahora: datetime) -> bool:
    try:
        visto = datetime.fromisoformat(entrada['fecha'])
        if visto.tzinfo is None:
            visto = visto.replace(tzinfo=timezone.utc)
        return ahora - visto > timedelta(days=TTL_DIAS)
    except Exception:
        return True


def resumen() -> str:
    d = _cargar()
    ok = sum(1 for v in d.values() if v.get('ok'))
    return f'{len(d)} veredictos en caché ({ok} verificados)'
