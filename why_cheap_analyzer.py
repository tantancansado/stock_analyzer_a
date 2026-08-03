#!/usr/bin/env python3
"""
Why Cheap — responde la única pregunta que decide una compra value: ¿por qué
está barata?

Todo el pipeline mide CUÁNTO ha caído un valor. Nada miraba POR QUÉ, que es
justo el criterio del usuario: comprar buenas empresas castigadas solo si el
castigo no es deterioro real del negocio. El 3-ago-2026, con OTIS (-23.9% del
máximo, EBIT/EV 6.21) e ICE (-19.5%, RS -20.1) sobre la mesa, no había forma de
cerrar el análisis: los números decían "barata y cayendo" y nadie sabía si la
caída era el ciclo o el negocio rompiéndose.

Clasifica la caída en cuatro:
  DETERIORO   el negocio está peor: guidance retirada, márgenes que no vuelven,
              pérdida estructural de cuota, investigación grave → NO comprar
  CICLICO     el sector está en la parte baja del ciclo, el negocio aguanta
  EVENTO      shock puntual y acotado (multa, litigio cerrado, salida de un CEO)
  SENTIMIENTO rotación, múltiplos, macro — nada específico de la empresa

Solo DETERIORO veta. El resto informa y sube o baja convicción.

Reglas del módulo, heredadas de todo el trabajo de integridad:
  - Las fuentes NO son lo que el modelo escriba: se leen de los bloques de
    resultado de la herramienta de búsqueda (ver claude_research). Un modelo
    puede escribir una URL plausible igual que escribe una cifra plausible.
  - Sin búsquedas reales detrás → SIN_DATOS: no veta, pero tampoco respalda.
  - Si la API cae, el pick sale sin veredicto (fail-open, como ai_pick_verifier).
"""
from __future__ import annotations

from typing import Any

from claude_research import ask_with_search, parse_json

VEREDICTOS = ('DETERIORO', 'CICLICO', 'EVENTO', 'SENTIMIENTO', 'SIN_DATOS')
BLOQUEANTES = ('DETERIORO',)

# Por debajo de este score el ticker no es un candidato de compra, así que no se
# gasta una búsqueda en explicar su caída.
MIN_SCORE_CANDIDATO = 50.0

SYSTEM = """Eres un analista value evaluando si una caída de precio es una oportunidad
o una trampa. El criterio del inversor: comprar buenas empresas castigadas solo si el
castigo NO es deterioro real del negocio.

Busca antes de responder: resultados trimestrales, guidance y noticias de los últimos
seis meses. No afirmes nada que no hayas encontrado buscando — si la búsqueda no da
suficiente, el veredicto es "SIN_DATOS", que es una respuesta perfectamente válida y
preferible a elegir una categoría por descarte.

Responde SOLO con este JSON, sin markdown alrededor:
{"veredicto": "DETERIORO|CICLICO|EVENTO|SENTIMIENTO|SIN_DATOS",
 "resumen": "<máximo dos frases en español: qué pasó y cuándo>",
 "confianza": 0-100}

Categorías:
- DETERIORO: el negocio está estructuralmente peor — guidance retirada o recortada
  varias veces, márgenes en caída sostenida, pérdida de cuota, investigación
  regulatoria grave, deuda que aprieta.
- CICLICO: el sector está en la parte baja de su ciclo pero el negocio aguanta.
- EVENTO: shock puntual y acotado, ya conocido y cuantificable.
- SENTIMIENTO: rotación, múltiplos o macro; nada específico de la empresa."""

PROMPT = """{company} ({ticker}) cotiza un {drop:.1f}% por debajo de su máximo de 52
semanas, con una fuerza relativa a 6 meses de {rs:.1f}%.

¿Por qué ha caído? Busca y clasifica."""


def analyze_ticker(ticker: str, company: str, drop_pct: float,
                   rs_6m: float = 0.0) -> dict[str, Any]:
    """Devuelve {veredicto, resumen, confianza, fuentes}. SIN_DATOS si no puede."""
    vacio = {'veredicto': 'SIN_DATOS', 'resumen': '', 'confianza': 0, 'fuentes': []}

    texto, fuentes = ask_with_search(
        PROMPT.format(company=company or ticker, ticker=ticker,
                      drop=abs(drop_pct or 0), rs=rs_6m or 0),
        system=SYSTEM,
    )
    data = parse_json(texto)
    if not data:
        return vacio

    veredicto = str(data.get('veredicto', '')).upper().strip()
    if veredicto not in VEREDICTOS:
        veredicto = 'SIN_DATOS'

    # Las fuentes vienen de la herramienta, no del texto del modelo. Sin
    # búsquedas detrás el veredicto podría salir de su memoria: no se acepta.
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
        'fuentes': fuentes[:4],
    }


def analyze_picks(rows: list[dict], min_drop_pct: float = 8.0,
                  max_tickers: int = 8) -> dict[str, dict]:
    """Analiza solo los candidatos reales: score de compra Y caída que explicar.

    Un ticker con score bajo no se va a comprar aunque la caída resulte ser
    ruido, así que no merece una búsqueda; y sin caída no hay nada que explicar.
    Se ordenan por score para gastar las llamadas en los mejores.
    """
    out: dict[str, dict] = {}
    candidatos = []
    for r in rows:
        try:
            drop = abs(float(r.get('proximity_to_52w_high') or 0))
            score = float(r.get('value_score') or 0)
        except (TypeError, ValueError):
            continue
        if drop >= min_drop_pct and score >= MIN_SCORE_CANDIDATO:
            candidatos.append((score, drop, r))

    candidatos.sort(key=lambda x: -x[0])
    if candidatos:
        print(f'   🔍 {len(candidatos)} candidatos con caída que explicar '
              f'(score ≥ {MIN_SCORE_CANDIDATO:.0f}); se analizan {min(len(candidatos), max_tickers)}')
    for _score, drop, r in candidatos[:max_tickers]:
        ticker = str(r.get('ticker', '')).upper()
        if not ticker:
            continue
        try:
            rs = float(r.get('relative_strength_6m') or 0)
        except (TypeError, ValueError):
            rs = 0.0
        res = analyze_ticker(ticker, str(r.get('company_name', '')), drop, rs)
        out[ticker] = res
        icono = {'DETERIORO': '🚫', 'CICLICO': '🔄', 'EVENTO': '⚡',
                 'SENTIMIENTO': '💭', 'SIN_DATOS': '❓'}.get(res['veredicto'], '❓')
        print(f"   {icono} {ticker} (-{drop:.1f}%): {res['veredicto']} — {res['resumen'][:90]}")
    return out


def apply_to_dataframe(df, veredictos: dict[str, dict]):
    """Añade las columnas del veredicto y saca los DETERIORO.

    Lo no analizado se queda: como en ai_pick_verifier, esto veta, no autoriza.
    """
    if df is None or df.empty or not veredictos:
        return df, []

    tickers = df['ticker'].astype(str).str.upper()
    df = df.copy()
    df['why_cheap']         = tickers.map(lambda t: veredictos.get(t, {}).get('veredicto', ''))
    df['why_cheap_resumen'] = tickers.map(lambda t: veredictos.get(t, {}).get('resumen', ''))
    df['why_cheap_fuentes'] = tickers.map(
        lambda t: ' | '.join(veredictos.get(t, {}).get('fuentes', []))[:400])

    bloqueados = [t for t, v in veredictos.items() if v.get('veredicto') in BLOQUEANTES]
    if bloqueados:
        df = df[~tickers.isin(bloqueados)].copy()
        print(f'   🚫 Fuera por deterioro del negocio: {bloqueados}')
    return df, bloqueados
