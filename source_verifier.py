#!/usr/bin/env python3
"""
Verificador de campos contra la fuente.

Nace del 10-sep-2026. El gate de Claude rechaza picks diciendo cosas como
"el crecimiento del 39,7% es implausible para Broadridge" — y de los 15
rechazos de ese día, 14 nombraban un campo CONCRETO. Pero el gate no podía
comprobarlo: opinaba desde su memoria y ahí acababa. Eso costaba caro en las
dos direcciones:

  · Cuando acertaba (el 39,7% ERA un bug del pipeline, un off-by-one en el
    interanual), se perdía el pick igual y nadie se enteraba de que el
    cálculo estaba roto. Llevaba meses así.
  · Cuando fallaba (el máximo de 52 semanas de BR, un 2,3% de desvío que
    venía del propio yfinance), se perdía un pick con score 86 por nada.

Esto cierra el bucle: dado un ticker y el campo que el gate señala, vuelve a
la fuente, recalcula y dice si el dato publicado se sostiene. Sin LLM — el
veredicto de plausibilidad ya está pagado; esto es aritmética.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Tolerancias por campo. Dos familias:
#   'pp'  → el campo YA es un porcentaje; se compara en puntos porcentuales.
#   'rel' → magnitud (precio, ratio, conteo); se compara en % relativo.
#
# Calibradas contra los dos casos reales que motivaron esto: el máximo de 52
# semanas de BR (255,74 publicado vs 250,03 real = 2,3%) tiene que CONFIRMAR,
# y su crecimiento (39,7% vs 7,5% = 32,2pp) tiene que CONTRADECIR.
TOLERANCIAS: dict[str, tuple[str, float]] = {
    'rev_growth_yoy':        ('pp',  5.0),
    'roe':                   ('pp',  5.0),
    'profit_margin':         ('pp',  5.0),
    'fcf_yield_pct':         ('pp',  2.0),
    'pct_from_52w_high':     ('pp',  5.0),
    'current_price':         ('rel', 3.0),
    'fifty_two_week_high':   ('rel', 5.0),
    'debt_to_equity':        ('rel', 25.0),
    'analyst_count':         ('rel', 40.0),
}


def _info(t) -> dict:
    try:
        return t.info or {}
    except Exception:
        return {}


def _valor_en_fuente(ticker: str, campo: str) -> float | None:
    """El valor real del campo, recalculado desde yfinance. None si no se puede."""
    import yfinance as yf
    t = yf.Ticker(ticker)

    if campo == 'current_price':
        h = t.history(period='5d')['Close'].dropna()
        return float(h.iloc[-1]) if len(h) else None

    if campo in ('fifty_two_week_high', 'pct_from_52w_high'):
        h = t.history(period='1y')['High'].dropna()
        if not len(h):
            return None
        maximo = float(h.max())
        if campo == 'fifty_two_week_high':
            return maximo
        c = t.history(period='5d')['Close'].dropna()
        return (float(c.iloc[-1]) / maximo - 1) * 100 if len(c) else None

    if campo == 'rev_growth_yoy':
        qf = t.quarterly_financials
        if qf is None or qf.empty or 'Total Revenue' not in qf.index:
            return None
        # Mismo criterio que fundamental_scorer tras el arreglo del 10-sep:
        # el trimestre del año anterior está 4 posiciones atrás, y la serie
        # se ordena explícitamente en vez de fiarse de yfinance.
        rev = qf.loc['Total Revenue'].dropna().sort_index(ascending=False)
        if len(rev) < 5 or not rev.iloc[4]:
            return None
        return (rev.iloc[0] - rev.iloc[4]) / abs(rev.iloc[4]) * 100

    i = _info(ticker if isinstance(ticker, dict) else t)
    if campo == 'roe':
        v = i.get('returnOnEquity')
        return v * 100 if v is not None else None
    if campo == 'profit_margin':
        v = i.get('profitMargins')
        return v * 100 if v is not None else None
    if campo == 'debt_to_equity':
        # yfinance lo da en PORCENTAJE (123.9 = 1,239x). El pipeline lo
        # guarda como ratio, así que se normaliza antes de comparar.
        v = i.get('debtToEquity')
        return v / 100 if v is not None else None
    if campo == 'analyst_count':
        v = i.get('numberOfAnalystOpinions')
        return float(v) if v is not None else None
    if campo == 'fcf_yield_pct':
        mc = i.get('marketCap')
        try:
            fcf = t.cashflow.loc['Free Cash Flow'].dropna().iloc[0]
        except Exception:
            return None
        return (fcf / mc * 100) if mc else None
    return None


def verificar_campo(ticker: str, campo: str, valor_publicado) -> dict:
    """¿Se sostiene `valor_publicado` contra la fuente?

    Devuelve {'estado', 'valor_fuente', 'detalle'} con estado en:
      'confirma'    — el dato publicado cuadra: la duda del gate era infundada
      'contradice'  — no cuadra: hay un bug en el pipeline, y se dice cuál
      'sin_fuente'  — no se ha podido comprobar (campo no soportado, red, etc.)

    Nunca lanza: un verificador que revienta es peor que uno que no sabe.
    """
    vacio = {'estado': 'sin_fuente', 'valor_fuente': None, 'detalle': ''}
    if campo not in TOLERANCIAS:
        return {**vacio, 'detalle': f'campo "{campo}" sin verificador'}
    try:
        publicado = float(valor_publicado)
    except (TypeError, ValueError):
        return {**vacio, 'detalle': 'el valor publicado no es un número'}

    try:
        real = _valor_en_fuente(ticker, campo)
    except Exception as exc:
        logger.warning('verificar_campo(%s, %s): %s', ticker, campo, exc)
        return {**vacio, 'detalle': f'la fuente falló: {str(exc)[:60]}'}
    if real is None:
        return {**vacio, 'detalle': 'la fuente no tiene ese dato'}

    modo, tol = TOLERANCIAS[campo]
    if modo == 'pp':
        desvio = abs(publicado - real)
        cuadra = desvio <= tol
        txt = f'{publicado:.1f} publicado vs {real:.1f} real ({desvio:.1f}pp de desvío)'
    else:
        if real == 0:
            return {**vacio, 'detalle': 'la fuente da 0, no se puede comparar en relativo'}
        desvio = abs(publicado - real) / abs(real) * 100
        cuadra = desvio <= tol
        txt = f'{publicado:.2f} publicado vs {real:.2f} real ({desvio:.1f}% de desvío)'

    return {
        'estado': 'confirma' if cuadra else 'contradice',
        'valor_fuente': round(real, 4),
        'detalle': txt,
    }
