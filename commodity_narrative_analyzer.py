#!/usr/bin/env python3
"""
Commodity Narrative Analyzer — reemplaza el texto de ciclo fijo por lo que de
verdad está moviendo el precio de cada materia prima ahora mismo.

Hasta el 5-ago-2026 `commodity_scanner.py` describía el ciclo con un párrafo
estático por tipo de commodity (CYCLE_CONTEXT), y ese párrafo era genérico o
directamente incorrecto — la ficha de gas natural describía el mercado del
petróleo porque ambos comparten `commodity_type = "Energy"`. Arreglar esa
tabla (hecho aparte) resuelve lo incorrecto; esto añade lo que una tabla fija
nunca puede dar: qué está pasando ESTA semana con ESE commodity en concreto.

Mismo patrón que why_cheap_analyzer para acciones: Claude con búsqueda web real
(claude_research.py), las fuentes salen de la herramienta — no de lo que el
modelo escriba — y sin búsquedas detrás el veredicto degrada a SIN_DATOS.

Añade, además, la respuesta a la pregunta práctica de "¿esto se puede comprar
en IBKR Ireland?": el dato ya existe determinista en el propio CSV
(`eu_alternative`), aquí se limita a citarlo en el veredicto en vez de dejar
que el usuario tenga que cruzarlo él mismo.
"""
from __future__ import annotations

from claude_research import ask_with_search, parse_json

MAX_COMMODITIES = 10   # universo entero cabe de sobra en el presupuesto
PRESUPUESTO_SEG = 300  # 5 min como mucho — enrichment opcional, no crítico

VEREDICTOS = ('OPORTUNIDAD_ESTRUCTURAL', 'MINIMO_CICLICO', 'TRAMPA_DE_VALOR', 'SIN_DATOS')

SYSTEM = """Eres un analista de materias primas. Te preguntan por una en concreto y
tienes que explicar qué está moviendo su precio ESTA semana — no el driver genérico
de su categoría, sino la noticia o el dato real detrás del nivel actual.

Busca antes de responder: inventarios, producción, demanda, clima si aplica,
decisiones de política (OPEP para petróleo, no aplica a gas natural ni a metales).
No afirmes nada que no hayas encontrado buscando.

Clasifica en una de estas categorías:
- OPORTUNIDAD_ESTRUCTURAL: el precio bajo responde a un factor temporal
  (estacional, sobreoferta puntual, sentimiento) mientras la demanda de fondo
  aguanta — el patrón que busca un inversor value.
- MINIMO_CICLICO: está barato dentro de un ciclo bajista que aún no ha tocado
  fondo — puede seguir cayendo antes de girar.
- TRAMPA_DE_VALOR: el precio bajo refleja un cambio estructural de demanda u
  oferta que no se va a revertir (sustitución tecnológica, exceso de
  capacidad permanente).
- SIN_DATOS: no encuentras información suficiente y reciente. Es una
  respuesta válida, mejor que forzar una categoría.

Responde SOLO con este JSON, sin markdown alrededor:
{"veredicto": "OPORTUNIDAD_ESTRUCTURAL|MINIMO_CICLICO|TRAMPA_DE_VALOR|SIN_DATOS",
 "resumen": "<máximo dos frases en español: qué está pasando y por qué mueve el precio>",
 "confianza": 0-100}"""

PROMPT = """{sector} ({ticker}) cotiza a {price} {currency}, un {pct_from_high:.1f}% por
debajo de su máximo de 52 semanas y un {pct_vs_2y:.1f}% respecto a su media de 2 años.

¿Qué está pasando con {sector} ahora mismo que explique este precio?"""


def analyze_commodity(ticker: str, sector: str, price: float, currency: str,
                      pct_from_high: float, pct_vs_2y_avg: float) -> dict:
    """Devuelve {veredicto, resumen, confianza, fuentes}. SIN_DATOS si no puede."""
    vacio = {'veredicto': 'SIN_DATOS', 'resumen': '', 'confianza': 0, 'fuentes': []}

    texto, fuentes = ask_with_search(
        PROMPT.format(sector=sector, ticker=ticker, price=price or 0,
                      currency=currency or 'USD', pct_from_high=pct_from_high or 0,
                      pct_vs_2y=pct_vs_2y_avg or 0),
        system=SYSTEM, max_tokens=4000, max_searches=4,
    )
    data = parse_json(texto)
    if not data:
        return vacio

    veredicto = str(data.get('veredicto', '')).upper().strip()
    if veredicto not in VEREDICTOS:
        veredicto = 'SIN_DATOS'
    if not fuentes:
        veredicto = 'SIN_DATOS'

    try:
        confianza = max(0, min(100, int(data.get('confianza', 0))))
    except (TypeError, ValueError):
        confianza = 0

    return {
        'veredicto': veredicto,
        'resumen': str(data.get('resumen', ''))[:300],
        'confianza': confianza,
        'fuentes': fuentes[:3],
    }


def enrich(rows: list[dict], max_commodities: int = MAX_COMMODITIES) -> dict[str, dict]:
    """Analiza el universo priorizando lo que ya parece atractivo por precio.

    No tiene sentido gastar una búsqueda en explicar algo que ya está CARO —
    el ranking prioriza value_rating ATRACTIVO/MUY_ATRACTIVO primero.
    """
    import time

    def _f(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    orden = {'MUY_ATRACTIVO': 0, 'ATRACTIVO': 1, 'NEUTRAL': 2, 'CARO': 3}
    candidatos = sorted(rows, key=lambda r: orden.get(r.get('value_rating', ''), 4))

    out: dict[str, dict] = {}
    inicio = time.monotonic()
    for r in candidatos[:max_commodities]:
        if time.monotonic() - inicio > PRESUPUESTO_SEG:
            print(f'   ⏱️  Presupuesto agotado — {len(out)}/{len(candidatos[:max_commodities])} analizados')
            break
        ticker = str(r.get('ticker', '')).upper()
        if not ticker:
            continue
        res = analyze_commodity(
            ticker, str(r.get('sector', '')), _f(r.get('price')) or 0,
            str(r.get('currency', 'USD')), _f(r.get('pct_from_high')) or 0,
            _f(r.get('pct_vs_2y_avg')) or 0,
        )
        out[ticker] = res
        icono = {'OPORTUNIDAD_ESTRUCTURAL': '🟢', 'MINIMO_CICLICO': '🟡',
                 'TRAMPA_DE_VALOR': '🔴', 'SIN_DATOS': '❓'}.get(res['veredicto'], '❓')
        eu = r.get('eu_alternative') or ''
        compra = f" · comprable en IBKR Ireland vía {eu}" if eu else " · sin equivalente UCITS conocido"
        print(f"   {icono} {ticker} ({r.get('sector')}): {res['veredicto']}{compra}")
        if res['resumen']:
            print(f"      {res['resumen'][:100]}")
    return out
