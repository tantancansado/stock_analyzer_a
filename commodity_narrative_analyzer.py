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

import claude_research
from claude_research import ask_with_search, ask_with_search_lote, parse_json

MAX_COMMODITIES = 10   # universo entero cabe de sobra en el presupuesto
PRESUPUESTO_SEG = 300  # 5 min como mucho — enrichment opcional, no crítico

# PRECIO_EXIGENTE tiene que estar aquí, no solo en el system: `_interpretar`
# convierte a SIN_DATOS cualquier veredicto que no esté en esta tupla, así que
# añadir la categoría solo al prompt la habría hecho desaparecer en silencio.
VEREDICTOS = ('OPORTUNIDAD_ESTRUCTURAL', 'MINIMO_CICLICO', 'TRAMPA_DE_VALOR',
              'PRECIO_EXIGENTE', 'SIN_DATOS')

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
- PRECIO_EXIGENTE: NO está barato. Cotiza por encima de su rango normal y lo
  que sostiene el precio es un factor alcista concreto (sequía, recorte de
  producción, choque de oferta). Puede ser una historia interesante, pero no
  es una compra por precio.
- SIN_DATOS: no encuentras información suficiente y reciente. Es una
  respuesta válida, mejor que forzar una categoría.

Las tres primeras categorías describen un precio BAJO. Si la materia prima no
está barata, la respuesta es PRECIO_EXIGENTE — no metas un precio alto en
«oportunidad» porque la historia de fondo sea buena. Barato o caro se mide
contra la media de 2 años, no contra el máximo: caer desde un máximo no la hace
barata si sigue por encima de su media. Te damos abajo la
valoración cuantitativa: si tu conclusión se aparta de ella, dilo en el
resumen y explica por qué, que para eso buscas.

Responde SOLO con este JSON, sin markdown alrededor:
{"veredicto": "OPORTUNIDAD_ESTRUCTURAL|MINIMO_CICLICO|TRAMPA_DE_VALOR|PRECIO_EXIGENTE|SIN_DATOS",
 "resumen": "<máximo dos frases en español: qué está pasando y por qué mueve el precio>",
 "confianza": 0-100}"""

# El `value_rating` iba fuera del prompt, así que se le pedía a la IA que
# fuera coherente con un número que no veía. El 18-sep-2026 WEAT, CANE y BAL
# salieron con rating CARO y veredicto OPORTUNIDAD_ESTRUCTURAL, y el control
# de coherencia tumbó el pipeline. No era la IA contradiciéndose: era que
# ninguna de las categorías servía para un precio alto.
#
# El 9-nov-2026 volvió a pasar con COPX: un 13 % sobre su media de 2 años (CARO) y
# un 29 % bajo su máximo. El prompt decía «un -28.7% por debajo» y «un 13.1%
# respecto a su media», sin signo, así que no se sabía si estaba por encima o por
# debajo, y la IA tomó la caída desde el máximo por precio bajo. Ahora van los dos
# con signo, y lo que contradiga a la valoración no se publica (`contradice_al_precio`).
PROMPT = """{sector} ({ticker}) cotiza a {price} {currency}: {pct_vs_2y:+.1f}% contra su
media de 2 años y {pct_from_high:+.1f}% contra su máximo de 52 semanas.
Valoración cuantitativa de la app: {rating}.

¿Qué está pasando con {sector} ahora mismo que explique este precio?"""


def analyze_commodity(ticker: str, sector: str, price: float, currency: str,
                      pct_from_high: float, pct_vs_2y_avg: float,
                      value_rating: str = 'sin valorar') -> dict:
    """Devuelve {veredicto, resumen, confianza, fuentes}. SIN_DATOS si no puede."""
    vacio = {'veredicto': 'SIN_DATOS', 'resumen': '', 'confianza': 0, 'fuentes': []}

    # 8-sep-2026: mismo bug que why_cheap_analyzer antes del 25-ago -- Sonnet
    # 5 sin recortar, y aquí peor (max_tokens=4000 para un JSON con resumen
    # de máx. 300 caracteres). Medido el mismo día: $0.30/llamada, y con
    # MAX_COMMODITIES=10 eso es hasta $3/día si se analiza el universo
    # entero. Clasificar en 4 categorías a partir de 2-4 fuentes ya buscadas
    # es síntesis cerrada -- mismo razonamiento que why_cheap, mismo arreglo:
    # Haiku 4.5, menos tokens, menos búsquedas.
    texto, fuentes = ask_with_search(
        PROMPT.format(sector=sector, ticker=ticker, price=price or 0,
                      currency=currency or 'USD', pct_from_high=pct_from_high or 0,
                      pct_vs_2y=pct_vs_2y_avg or 0,
                      rating=value_rating or 'sin valorar'),
        system=SYSTEM, max_tokens=1200, max_searches=2,
        model=claude_research.MODEL_HAIKU,
    )
    return _interpretar(texto, fuentes, value_rating)


DE_PRECIO_BAJO = ('OPORTUNIDAD_ESTRUCTURAL', 'MINIMO_CICLICO', 'TRAMPA_DE_VALOR')


def contradice_al_precio(veredicto: str, rating: str | None) -> bool:
    """Una categoría de precio bajo sobre algo CARO, o PRECIO_EXIGENTE sobre algo
    barato. Con el prompt ya diciéndoselo, si aun así pasa, el veredicto parte de
    leer mal el precio y no se publica: mejor sin narrativa que con una que
    contradice a la nota de al lado. Barato con TRAMPA_DE_VALOR sí vale (ver
    `coherence_check.commodity_rating_vs_narrativa`)."""
    rating = (rating or '').upper()
    if rating == 'CARO':
        return veredicto in DE_PRECIO_BAJO
    if rating in ('MUY_ATRACTIVO', 'ATRACTIVO'):
        return veredicto == 'PRECIO_EXIGENTE'
    return False


def _interpretar(texto: str, fuentes: list[str], rating: str | None = None) -> dict:
    """Respuesta cruda -> veredicto. Compartido por la vía síncrona y la de
    lote; dos parseos separados acaban desincronizándose."""
    vacio = {'veredicto': 'SIN_DATOS', 'resumen': '', 'confianza': 0, 'fuentes': []}
    data = parse_json(texto)
    if not data:
        return vacio

    veredicto = str(data.get('veredicto', '')).upper().strip()
    if veredicto not in VEREDICTOS:
        veredicto = 'SIN_DATOS'
    if not fuentes:
        veredicto = 'SIN_DATOS'
    if contradice_al_precio(veredicto, rating):
        return dict(vacio, descartado=f'{veredicto} con la app diciendo {rating}')

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
    def _f(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    orden = {'MUY_ATRACTIVO': 0, 'ATRACTIVO': 1, 'NEUTRAL': 2, 'CARO': 3}
    candidatos = sorted(rows, key=lambda r: orden.get(r.get('value_rating', ''), 4))

    out: dict[str, dict] = {}

    # Las preguntas son independientes: van en UN lote, a mitad de precio.
    # `PRESUPUESTO_SEG` cortaba el bucle cuando las llamadas de una en una se
    # alargaban; en lote ese papel lo hace `espera_max_s`, que es el mismo
    # límite pero aplicado a la espera entera en vez de a cada llamada.
    elegidos: list[tuple[str, dict]] = []
    prompts: dict[str, str] = {}
    for r in candidatos[:max_commodities]:
        ticker = str(r.get('ticker', '')).upper()
        if not ticker:
            continue
        elegidos.append((ticker, r))
        prompts[ticker] = PROMPT.format(
            sector=str(r.get('sector', '')), ticker=ticker,
            price=_f(r.get('price')) or 0, currency=str(r.get('currency', 'USD')),
            pct_from_high=_f(r.get('pct_from_high')) or 0,
            pct_vs_2y=_f(r.get('pct_vs_2y_avg')) or 0,
            rating=str(r.get('value_rating') or 'sin valorar'))

    crudos = ask_with_search_lote(
        prompts, system=SYSTEM, max_tokens=1200, max_searches=2,
        model=claude_research.MODEL_HAIKU, espera_max_s=PRESUPUESTO_SEG,
    )

    for ticker, r in elegidos:
        res = _interpretar(*crudos[ticker], rating=r.get('value_rating'))
        out[ticker] = res
        icono = {'OPORTUNIDAD_ESTRUCTURAL': '🟢', 'MINIMO_CICLICO': '🟡',
                 'TRAMPA_DE_VALOR': '🔴', 'PRECIO_EXIGENTE': '🔵',
                 'SIN_DATOS': '❓'}.get(res['veredicto'], '❓')
        eu = r.get('eu_alternative') or ''
        compra = f" · comprable en IBKR Ireland vía {eu}" if eu else " · sin equivalente UCITS conocido"
        print(f"   {icono} {ticker} ({r.get('sector')}): {res['veredicto']}{compra}")
        if res['resumen']:
            print(f"      {res['resumen'][:100]}")
        if res.get('descartado'):
            print(f"      ⚠️  no se publica: {res['descartado']}")
    return out
