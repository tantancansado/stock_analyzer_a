#!/usr/bin/env python3
"""
Signal Post-Mortem — mira las señales cerradas y busca qué separa a las
ganadoras de las perdedoras.

El tracker publica el resultado (a 3-ago-2026: 35.8% de acierto y -1.84% de
media a 90 días sobre 134 señales) y ahí se queda. Nadie ha abierto nunca esas
134 para preguntarse qué tenían en común las que salieron mal.

Hace dos cosas, en este orden:

  1. Cortes deterministas: agrupa por sector, régimen de mercado, banda de
     upside, distancia al máximo, Piotroski y divergencia de valoración, y
     calcula win rate y retorno medio de cada grupo. Esto son hechos.
  2. Claude lee esa tabla y propone hipótesis de qué distingue a unas de otras.

Lo que NO hace, deliberadamente: tocar el score. Devuelve hipótesis para que
las valides con el backtest, no reglas que se apliquen solas. Una muestra de 134
señales genera correlaciones espurias con facilidad, y cambiar el scoring con
una de ellas es la mejor forma de empeorar el sistema creyendo que se mejora.

Salida: docs/signal_postmortem.json
Corre semanalmente — a diario no cambia nada y gasta llamadas.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from groq_utils import CLAUDE_SONNET, claude_chat

RECS = Path('docs/portfolio_tracker/recommendations.csv')
OUT  = Path('docs/signal_postmortem.json')

VALUE_STRATEGIES = {'VALUE', 'EU_VALUE'}
MIN_GRUPO = 5          # por debajo, cualquier win rate es anécdota
HORIZONTE = 'return_90d'


def _cortes(df: pd.DataFrame) -> dict:
    """Win rate y retorno medio por grupo. Solo grupos con muestra suficiente."""
    out: dict[str, list] = {}

    def agrupa(nombre: str, serie: pd.Series):
        filas = []
        for valor, sub in df.groupby(serie, dropna=True):
            vivos = sub[sub[HORIZONTE].notna()]
            if len(vivos) < MIN_GRUPO:
                continue
            filas.append({
                'grupo': str(valor),
                'n': int(len(vivos)),
                'win_rate': round((vivos[HORIZONTE] > 0).mean() * 100, 1),
                'retorno_medio': round(float(vivos[HORIZONTE].mean()), 2),
            })
        if filas:
            out[nombre] = sorted(filas, key=lambda r: r['retorno_medio'])

    if 'sector' in df.columns:
        agrupa('sector', df['sector'])
    if 'market_regime' in df.columns:
        agrupa('regimen_mercado', df['market_regime'])

    if 'analyst_upside_pct' in df.columns:
        up = pd.to_numeric(df['analyst_upside_pct'], errors='coerce')
        agrupa('banda_upside', pd.cut(
            up, [-999, 0, 10, 15, 20, 25, 30, 999],
            labels=['<0%', '0-10%', '10-15%', '15-20%', '20-25%', '25-30%', '>=30%']))

    if 'value_score' in df.columns:
        sc = pd.to_numeric(df['value_score'], errors='coerce')
        agrupa('banda_score', pd.cut(
            sc, [0, 40, 50, 60, 70, 100],
            labels=['<40', '40-50', '50-60', '60-70', '>=70']))

    if 'risk_reward_ratio' in df.columns:
        rr = pd.to_numeric(df['risk_reward_ratio'], errors='coerce')
        agrupa('banda_rr', pd.cut(rr, [0, 1, 1.5, 2, 3, 999],
                                  labels=['<1', '1-1.5', '1.5-2', '2-3', '>=3']))
    return out


def _hipotesis(cortes: dict, resumen: dict) -> dict:
    """Claude propone qué distingue a las perdedoras. Hipótesis, no reglas."""
    if not cortes:
        return {'hipotesis': [], 'nota': 'sin grupos con muestra suficiente'}

    system = (
        'Eres un analista cuantitativo revisando el histórico de una estrategia '
        'VALUE. Te doy win rate y retorno medio por grupo, ya calculados. Tu '
        'trabajo es proponer HIPÓTESIS de qué distingue a las señales que '
        'funcionan de las que no.\n\n'
        'Sé escéptico: con muestras de decenas de señales las correlaciones '
        'espurias son la norma. Di explícitamente cuándo un patrón puede ser '
        'ruido. No propongas cambios de scoring: propones qué medir, no qué '
        'cambiar. Responde SOLO con JSON:\n'
        '{"hipotesis": [{"patron": "...", "evidencia": "...", '
        '"como_validarlo": "...", "confianza": "alta|media|baja"}], '
        '"nota": "..."}'
    )
    prompt = (
        f'Resultado global: {json.dumps(resumen, ensure_ascii=False)}\n\n'
        f'Cortes por grupo (horizonte {HORIZONTE}):\n'
        f'{json.dumps(cortes, ensure_ascii=False, indent=1)}'
    )

    raw = claude_chat([{'role': 'user', 'content': prompt}],
                      model=CLAUDE_SONNET, system=system,
                      max_tokens=1500, temperature=0.2)
    if not raw:
        return {'hipotesis': [], 'nota': 'verificador no disponible'}
    try:
        text = raw.strip()
        if text.startswith('```'):
            text = text.split('```')[1].lstrip('json').strip()
        return json.loads(text)
    except (ValueError, IndexError):
        return {'hipotesis': [], 'nota': 'respuesta ilegible'}


def main() -> None:
    print('[signal_postmortem] Analizando señales cerradas...')
    if not RECS.exists():
        print(f'  {RECS} no existe — nada que analizar')
        return

    df = pd.read_csv(RECS)
    df = df[df['strategy'].isin(VALUE_STRATEGIES)]
    if HORIZONTE not in df.columns:
        print(f'  Sin columna {HORIZONTE} todavía — el histórico aún no cumple el horizonte')
        return

    cerradas = df[df[HORIZONTE].notna()]
    if len(cerradas) < MIN_GRUPO * 2:
        print(f'  Solo {len(cerradas)} señales cerradas — muestra insuficiente')
        return

    resumen = {
        'n': int(len(cerradas)),
        'win_rate': round((cerradas[HORIZONTE] > 0).mean() * 100, 1),
        'retorno_medio': round(float(cerradas[HORIZONTE].mean()), 2),
        'horizonte': HORIZONTE,
    }
    print(f"  {resumen['n']} señales · {resumen['win_rate']}% acierto · "
          f"{resumen['retorno_medio']:+.2f}% medio")

    cortes = _cortes(cerradas)
    for nombre, filas in cortes.items():
        peor, mejor = filas[0], filas[-1]
        print(f"  {nombre}: peor {peor['grupo']} ({peor['retorno_medio']:+.1f}%, n={peor['n']}) · "
              f"mejor {mejor['grupo']} ({mejor['retorno_medio']:+.1f}%, n={mejor['n']})")

    analisis = _hipotesis(cortes, resumen)
    for h in analisis.get('hipotesis', [])[:5]:
        print(f"  💡 [{h.get('confianza', '?')}] {h.get('patron', '')}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'generated_at': datetime.now().isoformat(),
        'resumen': resumen,
        'cortes': cortes,
        'analisis': analisis,
    }, ensure_ascii=False, indent=2))
    print(f'  ✓ {OUT}')


if __name__ == '__main__':
    main()
