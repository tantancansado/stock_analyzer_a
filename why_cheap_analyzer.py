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
  - Cada veredicto va con las URLs en las que se apoya. Sin fuentes → SIN_DATOS,
    que no veta pero tampoco respalda.
  - El modelo no inventa cifras: busca y cita.
  - Si la API cae, el pick sale sin veredicto (fail-open, como ai_pick_verifier).
"""
from __future__ import annotations

import json
import os
from typing import Any

# compound-beta trae búsqueda web integrada — mismo motor que ai_data_fetcher
SEARCH_MODEL = 'compound-beta'

VEREDICTOS = ('DETERIORO', 'CICLICO', 'EVENTO', 'SENTIMIENTO', 'SIN_DATOS')
BLOQUEANTES = ('DETERIORO',)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return None
    try:
        from groq import Groq
        _client = Groq(api_key=api_key)
        return _client
    except Exception:
        return None


PROMPT = """Analiza por qué la acción de {company} ({ticker}) cotiza un {drop:.1f}%
por debajo de su máximo de 52 semanas, con una fuerza relativa a 6 meses de {rs:.1f}%.

Busca resultados trimestrales, guidance y noticias de los últimos 6 meses.

Clasifica la caída en UNA de estas categorías:
- "DETERIORO": el negocio está estructuralmente peor (guidance retirada o
  recortada varias veces, márgenes en caída sostenida, pérdida de cuota,
  investigación regulatoria grave, deuda que aprieta).
- "CICLICO": el sector está en la parte baja de su ciclo pero el negocio aguanta.
- "EVENTO": shock puntual y acotado, ya conocido y cuantificable.
- "SENTIMIENTO": rotación sectorial, compresión de múltiplos o macro; nada
  específico de la empresa.
- "SIN_DATOS": no encuentras información suficiente. Úsalo sin reparos: es
  preferible a elegir una categoría por descarte.

Reglas:
- NO inventes cifras. Cada afirmación se apoya en algo que hayas encontrado.
- "fuentes" debe traer URLs concretas. Sin fuentes, el veredicto es "SIN_DATOS".
- "resumen": máximo dos frases, en español, concretas (qué pasó y cuándo).

Responde SOLO con este JSON:
{{"veredicto": "...", "resumen": "...", "confianza": 0-100, "fuentes": ["url", ...]}}"""


def analyze_ticker(ticker: str, company: str, drop_pct: float,
                   rs_6m: float = 0.0) -> dict[str, Any]:
    """Devuelve {veredicto, resumen, confianza, fuentes}. SIN_DATOS si no puede."""
    vacio = {'veredicto': 'SIN_DATOS', 'resumen': '', 'confianza': 0, 'fuentes': []}

    client = _get_client()
    if client is None:
        return vacio

    try:
        resp = client.chat.completions.create(
            model=SEARCH_MODEL,
            messages=[{'role': 'user', 'content': PROMPT.format(
                company=company or ticker, ticker=ticker,
                drop=abs(drop_pct or 0), rs=rs_6m or 0)}],
            temperature=0,
            max_tokens=700,
        )
        raw = (resp.choices[0].message.content or '').strip()
    except Exception as e:
        print(f'   ⚠️  {ticker}: análisis no disponible ({str(e)[:60]})')
        return vacio

    if '```' in raw:
        parts = raw.split('```')
        if len(parts) > 1:
            raw = parts[1].lstrip('json').strip()
    start, end = raw.find('{'), raw.rfind('}')
    if start < 0 or end <= start:
        return vacio
    try:
        data = json.loads(raw[start:end + 1])
    except ValueError:
        return vacio

    veredicto = str(data.get('veredicto', '')).upper().strip()
    if veredicto not in VEREDICTOS:
        veredicto = 'SIN_DATOS'

    fuentes = [u for u in (data.get('fuentes') or [])
               if isinstance(u, str) and u.startswith(('http://', 'https://'))]

    # Un veredicto sin fuentes no se sostiene: podría venir de la memoria del
    # modelo, y ese es justo el fallo que no queremos.
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
                  max_tickers: int = 12) -> dict[str, dict]:
    """Analiza los picks que de verdad han caído.

    Por debajo de min_drop_pct no hay caída que explicar (y sin caída no hay
    tesis value que perseguir), así que no se gasta una llamada.
    """
    out: dict[str, dict] = {}
    candidatos = []
    for r in rows:
        try:
            drop = abs(float(r.get('proximity_to_52w_high') or 0))
        except (TypeError, ValueError):
            continue
        if drop >= min_drop_pct:
            candidatos.append((drop, r))

    candidatos.sort(key=lambda x: -x[0])
    for drop, r in candidatos[:max_tickers]:
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
