#!/usr/bin/env python3
"""
Bounce Catalyst Check — antes de avisar de un rebote, mirar si la sobreventa
tiene una causa que la explique.

Los setups se deciden con RSI2, volumen y distancia al soporte. Nada miraba si
esa sobreventa viene de un profit warning, una guidance retirada o una
investigación abierta. Un RSI2 de 1.7 puede ser una goma estirada o el primer
día de un desplome de tres semanas, y desde los indicadores se ven igual.

Como son operaciones de 1-5 días, entrar mal duele rápido. Y como los setups son
raros (~1/semana), comprobar dos o tres tickers al día no cuesta nada.

Solo veta ante un catalizador negativo GRAVE, reciente y con búsquedas detrás
(las fuentes salen de la herramienta, no del texto del modelo — ver
claude_research). Un mal día de mercado o una rebaja de precio objetivo no son
motivo: eso es justo lo que crea la oportunidad.
"""
from __future__ import annotations

import claude_research
from claude_research import ask_with_search, ask_with_search_lote, parse_json

LOOKBACK_HORAS = 72

SYSTEM = """Compruebas si una acción fuertemente sobrevendida lo está por una razón
grave o por movimiento de mercado. La distinción decide si un rebote técnico a 1-5
días es una oportunidad o un cuchillo cayendo.

Busca noticias recientes antes de responder. No afirmes nada que no hayas encontrado
buscando.

Responde SOLO con este JSON, sin markdown alrededor:
{"veredicto": "PELIGRO|LIMPIO|SIN_DATOS", "motivo": "<una frase en español>"}

- PELIGRO solo si encuentras algo de esta gravedad: profit warning, recorte o
  retirada de guidance, resultados muy por debajo de lo esperado, investigación
  regulatoria, fraude o problemas contables, dimisión inesperada del CEO o CFO,
  pérdida de un contrato relevante, ampliación de capital dilutiva o problemas de
  liquidez.
- LIMPIO si la caída es movimiento de mercado, rotación sectorial, una rebaja de
  precio objetivo o debilidad técnica: eso crea la oportunidad, no la invalida.
- SIN_DATOS si no encuentras información fiable."""

PROMPT = """{ticker} está fuertemente sobrevendida (RSI extremo) y aparece como
candidata a rebote técnico de 1 a 5 días.

¿Ha pasado algo en las últimas {horas} horas que explique la caída?"""


def check_ticker(ticker: str) -> dict:
    """Devuelve {veredicto, motivo, fuentes}. SIN_DATOS ante cualquier problema.

    Coste (revisado 25-ago-2026, junto con why_cheap_analyzer, que llamaba a
    la misma ask_with_search con el doble de búsquedas y salía a $0.33/llamada
    — el 44% del gasto mensual). Esta llamada ya estaba más ajustada (4
    búsquedas frente a las 6 por defecto), pero medía $0.27/llamada igual —
    caro para lo que es, aunque la muestra es de solo 4 llamadas en todo el
    mes y con tan poco volumen (~1 setup/semana, ver bounce-scanners-expected-
    rate) el ahorro total es de céntimos, no de dólares.
    Se recorta a 3 búsquedas por la misma razón que why_cheap: un catalizador
    lo bastante grave para vetar un rebote (profit warning, fraude,
    investigación) sale en las dos-tres primeras búsquedas si existe, o no
    existe. `effort` se deja en 'medium' A PROPÓSITO, sin tocar: esto es un
    gate de seguridad antes de recomendar una entrada de 1-5 días, no una
    clasificación cerrada como why_cheap — vale la pena que razone un poco
    más para pesar la gravedad, y el volumen es tan bajo que bajarlo no
    cambiaría la factura de forma medible.
    """
    vacio = {'veredicto': 'SIN_DATOS', 'motivo': '', 'fuentes': []}

    # max_searches=2, no 3: el coste de una llamada con búsqueda crece con el
    # CUADRADO del número de búsquedas, porque el bucle del servidor reenvía el
    # contexto acumulado en cada ronda. Medido en producción (sep-2026), cada
    # llamada arrastraba 172k-263k tokens de ENTRADA — ahí está el gasto, no en
    # el modelo. Con 3 búsquedas el servidor manda 1+2+3=6 unidades de contexto;
    # con 2, son 1+2=3. Quitar UNA búsqueda cuesta la mitad, no un tercio.
    #
    # Y a Haiku, como why_cheap y commodity_narrative: era el último que
    # quedaba en Sonnet y el más caro de los tres ($0.31/llamada). La tarea es
    # clasificar en categorías cerradas material que ya trajo el buscador — no
    # comparar ni razonar en cadena — y ahí Haiku rinde igual a un tercio del
    # precio por token. `effort` desaparece: con Haiku no se manda (ver
    # claude_research._SIN_EFFORT), así que dejarlo solo despistaba.
    texto, fuentes = ask_with_search(
        PROMPT.format(ticker=ticker, horas=LOOKBACK_HORAS),
        system=SYSTEM, max_tokens=1200, max_searches=2,
        model=claude_research.MODEL_HAIKU,
    )
    return _interpretar(texto, fuentes)


def _interpretar(texto: str, fuentes: list[str]) -> dict:
    """Respuesta cruda -> {veredicto, motivo, fuentes}. Compartido por la vía
    síncrona y la de lote: dos parseos separados se desincronizan."""
    vacio = {'veredicto': 'SIN_DATOS', 'motivo': '', 'fuentes': []}
    data = parse_json(texto)
    if not data:
        return vacio

    veredicto = str(data.get('veredicto', '')).upper().strip()
    if veredicto not in ('PELIGRO', 'LIMPIO', 'SIN_DATOS'):
        veredicto = 'SIN_DATOS'

    # No se tira un setup técnicamente válido por una afirmación sin búsquedas
    # que la respalden
    if veredicto == 'PELIGRO' and not fuentes:
        veredicto = 'SIN_DATOS'

    return {'veredicto': veredicto, 'motivo': str(data.get('motivo', ''))[:200],
            'fuentes': fuentes[:3]}


def filter_setups(setups: list[dict]) -> tuple[list[dict], list[dict]]:
    """Devuelve (setups limpios, descartados). SIN_DATOS no descarta.

    La comprobación veta, no autoriza: si la API no responde, el setup sigue su
    camino con los filtros técnicos de siempre.
    """
    if not setups:
        return setups, []

    # Las preguntas son independientes entre sí, así que van en UN lote: la
    # Batch API las cobra a la mitad y esta es la llamada más cara de la app
    # ($0,31 cada una por el contexto que arrastra la búsqueda). Lo que no
    # vuelva del lote lo resuelve `ask_with_search_lote` en síncrono, así que
    # el peor caso es pagar lo de siempre, nunca quedarse sin comprobar.
    tickers = [t for t in (str(x.get('ticker', '')).upper() for x in setups) if t]
    prompts = {t: PROMPT.format(ticker=t, horas=LOOKBACK_HORAS) for t in tickers}
    crudos = ask_with_search_lote(
        prompts, system=SYSTEM, max_tokens=1200, max_searches=2,
        model=claude_research.MODEL_HAIKU,
    )
    veredictos = {t: _interpretar(*crudos[t]) for t in prompts}

    limpios, descartados = [], []
    for s in setups:
        ticker = str(s.get('ticker', '')).upper()
        if not ticker:
            continue
        res = veredictos.get(ticker) or {'veredicto': 'SIN_DATOS', 'motivo': '', 'fuentes': []}
        if res['veredicto'] == 'PELIGRO':
            descartados.append({**s, 'catalyst_motivo': res['motivo'],
                                'catalyst_fuentes': res['fuentes']})
            print(f"   🚫 {ticker} descartado — {res['motivo']}")
        else:
            if res['veredicto'] == 'LIMPIO':
                print(f'   ✅ {ticker}: sin catalizador negativo reciente')
            limpios.append(s)
    return limpios, descartados
