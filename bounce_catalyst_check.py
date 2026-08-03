#!/usr/bin/env python3
"""
Bounce Catalyst Check — antes de avisar de un rebote, mirar si la sobreventa
tiene una causa que la explique.

Los setups se deciden con RSI2, volumen y distancia al soporte. Nada miraba si
esa sobreventa viene de un profit warning, una guidance retirada o una
investigación abierta. Un RSI2 de 1.7 puede ser una goma estirada o el primer
día de un desplome de tres semanas, y desde los indicadores se ven igual.

Como son operaciones de 1-5 días, entrar mal duele rápido. Y como los setups
son raros (~1/semana), comprobar dos o tres tickers al día no cuesta nada.

Solo veta ante un catalizador negativo GRAVE y reciente. Un mal día de mercado
o una rebaja de precio objetivo no son motivo: eso es justo lo que crea la
oportunidad.
"""
from __future__ import annotations

import json
import os

SEARCH_MODEL = 'compound-beta'
LOOKBACK_HORAS = 72

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


PROMPT = """La acción {ticker} está fuertemente sobrevendida (RSI extremo) y aparece
como candidata a rebote técnico de 1 a 5 días.

Busca si en las últimas {horas} horas ha habido alguna noticia que explique la caída.

Responde "PELIGRO" solo si encuentras algo de esta gravedad:
- profit warning o recorte/retirada de guidance
- resultados muy por debajo de lo esperado
- investigación regulatoria, fraude o problemas contables
- dimisión inesperada del CEO o CFO
- pérdida de un contrato o cliente relevante
- ampliación de capital dilutiva o problemas de liquidez

Responde "LIMPIO" si la caída es movimiento de mercado, rotación sectorial, una
rebaja de precio objetivo o simple debilidad técnica: eso es lo que crea la
oportunidad, no lo que la invalida.

Responde "SIN_DATOS" si no encuentras información fiable.

NO inventes. "fuentes" debe traer URLs concretas; sin ellas el veredicto es
"SIN_DATOS".

Responde SOLO con este JSON:
{{"veredicto": "PELIGRO|LIMPIO|SIN_DATOS", "motivo": "<una frase en español>", "fuentes": ["url"]}}"""


def check_ticker(ticker: str) -> dict:
    """Devuelve {veredicto, motivo, fuentes}. SIN_DATOS ante cualquier problema."""
    vacio = {'veredicto': 'SIN_DATOS', 'motivo': '', 'fuentes': []}

    client = _get_client()
    if client is None:
        return vacio

    try:
        resp = client.chat.completions.create(
            model=SEARCH_MODEL,
            messages=[{'role': 'user', 'content': PROMPT.format(
                ticker=ticker, horas=LOOKBACK_HORAS)}],
            temperature=0,
            max_tokens=500,
        )
        raw = (resp.choices[0].message.content or '').strip()
    except Exception as e:
        print(f'   ⚠️  {ticker}: sin comprobación de catalizador ({str(e)[:60]})')
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
    if veredicto not in ('PELIGRO', 'LIMPIO', 'SIN_DATOS'):
        veredicto = 'SIN_DATOS'

    fuentes = [u for u in (data.get('fuentes') or [])
               if isinstance(u, str) and u.startswith(('http://', 'https://'))]
    # Un "PELIGRO" sin fuente no basta para tirar un setup válido
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

    limpios, descartados = [], []
    for s in setups:
        ticker = str(s.get('ticker', '')).upper()
        if not ticker:
            continue
        res = check_ticker(ticker)
        if res['veredicto'] == 'PELIGRO':
            descartados.append({**s, 'catalyst_motivo': res['motivo'],
                                'catalyst_fuentes': res['fuentes']})
            print(f"   🚫 {ticker} descartado — {res['motivo']}")
        else:
            if res['veredicto'] == 'LIMPIO':
                print(f'   ✅ {ticker}: sin catalizador negativo reciente')
            limpios.append(s)
    return limpios, descartados
