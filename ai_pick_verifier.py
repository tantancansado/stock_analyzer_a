#!/usr/bin/env python3
"""
AI Pick Verifier — Claude revisa la ficha de cada recomendación antes de que
salga a la lista o a Telegram.

Es la segunda capa. La primera (data_integrity) son rangos fijos y coge lo
imposible; esta coge lo *incoherente*, que ninguna regla fija anticipa: un score
alto sostenido por fundamentales flojos, un "suelo confirmado" con el precio bajo
la MA200, un múltiplo que no cuadra con el sector, una cifra que huele a error de
unidad o de divisa.

REGLA INNEGOCIABLE: Claude NO aporta ni un solo número. Solo juzga si la ficha
que se le enseña es coherente consigo misma. Pedirle a un modelo el FCF de una
empresa es pedirle que se lo invente, y ese es justo el problema que venimos a
resolver — los datos salen de yfinance o no salen.

Si la API no está disponible el pipeline sigue (fail-open) y lo dice: bloquear
toda la lista porque falta una API key sería peor que publicarla, ya que
data_integrity ya ha filtrado lo imposible.
"""
from __future__ import annotations

import json
from typing import Any

from groq_utils import CLAUDE_HAIKU, claude_chat

# Campos que se le enseñan al verificador. Solo lectura: ninguno se sustituye
# con lo que responda.
FICHA_FIELDS = (
    'ticker', 'company_name', 'sector', 'industry', 'current_price',
    'value_score', 'fundamental_score', 'piotroski_score',
    'analyst_upside_pct', 'target_price_dcf_upside_pct', 'target_price_pe_upside_pct',
    'upside_triangulated_pct', 'upside_divergence',
    'fcf_yield_pct', 'ebit_ev_yield', 'peg_ratio', 'dividend_yield_pct',
    'proximity_to_52w_high', 'relative_strength_6m',
    'entry_readiness', 'entry_readiness_reason', 'ma_filter_pass', 'ma_filter_reason',
    'tech_stage', 'trend_direction', 'price_currency', 'financial_currency',
)

SYSTEM = """Eres un auditor de datos financieros. Tu único trabajo es decidir si la
ficha de un valor es COHERENTE CONSIGO MISMA.

NO aportas datos. NO corriges cifras. NO estimas valores que falten. Si un dato no
está, eso en sí mismo puede ser un problema que señalas, pero jamás lo rellenas.

Buscas exactamente esto:
- Cifras imposibles o que sugieren error de unidad/divisa (FCF yield de dos
  dígitos altos, múltiplos absurdos, ratios que solo cuadran con otro factor de
  escala como 10, 100 o un tipo de cambio).
- Contradicciones internas: un texto que afirma algo que otro campo desmiente
  (p.ej. "sobre MA200 ascendente" cuando el filtro de medias dice lo contrario,
  o "suelo confirmado" con tendencia lateral o bajista).
- Un score alto que no se sostiene en los fundamentales de la propia ficha.
- Valoraciones que se contradicen entre sí sin que nada lo señale.

Severidad:
- "BLOCK": el dato es erróneo o la contradicción invalida la recomendación.
- "WARN": llamativo pero defendible.
- "OK": la ficha es coherente.

Respondes SOLO con un JSON válido, sin markdown ni explicación fuera del JSON:
{"resultados": [{"ticker": "XXX", "veredicto": "OK|WARN|BLOCK", "problemas": ["..."]}]}"""


def _ficha(row: dict) -> dict:
    return {k: row.get(k) for k in FICHA_FIELDS if row.get(k) not in (None, '')}


def verify_picks(rows: list[dict], model: str = CLAUDE_HAIKU,
                 max_picks: int = 25) -> dict[str, dict[str, Any]]:
    """Verifica una lista de picks. Devuelve {ticker: {veredicto, problemas}}.

    Un ticker ausente del resultado es un ticker sin verificar (API caída,
    respuesta ilegible): el consumidor lo trata como no verificado, no como
    aprobado ni como rechazado.
    """
    if not rows:
        return {}

    fichas = [_ficha(r) for r in rows[:max_picks]]
    prompt = (
        'Audita la coherencia de estas fichas. Una entrada por ticker en el JSON '
        'de salida, con el mismo ticker que recibes.\n\n'
        + json.dumps(fichas, ensure_ascii=False, default=str)
    )

    raw = claude_chat(
        [{'role': 'user', 'content': prompt}],
        model=model, system=SYSTEM, max_tokens=2000, temperature=0.0,
    )
    if not raw:
        print('   ⚠️  Verificador IA no disponible — se publica solo con el guard determinista')
        return {}

    try:
        text = raw.strip()
        if text.startswith('```'):
            text = text.split('```')[1].lstrip('json').strip()
        data = json.loads(text)
    except (ValueError, IndexError) as e:
        print(f'   ⚠️  Respuesta del verificador ilegible ({e}) — no se bloquea nada por ello')
        return {}

    out: dict[str, dict[str, Any]] = {}
    for item in data.get('resultados', []):
        ticker = str(item.get('ticker', '')).upper()
        if not ticker:
            continue
        veredicto = str(item.get('veredicto', 'OK')).upper()
        if veredicto not in ('OK', 'WARN', 'BLOCK'):
            veredicto = 'WARN'
        out[ticker] = {'veredicto': veredicto, 'problemas': item.get('problemas', [])}

    n_block = sum(1 for v in out.values() if v['veredicto'] == 'BLOCK')
    n_warn  = sum(1 for v in out.values() if v['veredicto'] == 'WARN')
    print(f'   🤖 Verificador IA: {len(out)} fichas · {n_block} bloqueadas · {n_warn} con avisos')
    for t, v in out.items():
        if v['veredicto'] != 'OK':
            for p in v['problemas'][:2]:
                print(f"      {'🚫' if v['veredicto'] == 'BLOCK' else '⚠️ '} {t}: {p}")
    return out


def apply_verdicts(df, verdicts: dict[str, dict], block_only: bool = True):
    """Quita del DataFrame los tickers que la IA marcó BLOCK.

    Lo no verificado se queda: la IA veta, no autoriza. Así una caída de la API
    nunca vacía la lista.
    """
    if df is None or df.empty or not verdicts:
        return df, []
    blocked = [t for t, v in verdicts.items() if v['veredicto'] == 'BLOCK']
    if not blocked:
        return df, []
    if block_only:
        keep = ~df['ticker'].astype(str).str.upper().isin(blocked)
        return df[keep].copy(), blocked
    return df, blocked
