#!/usr/bin/env python3
"""
Enrich Why Cheap — añade a la lista VALUE el motivo de cada caída.

Vive fuera del integrator a propósito. El 3-ago-2026 este análisis corría dentro
de `save_results()`, que es un paso CRÍTICO del pipeline: ocho búsquedas web de
Claude sin timeout explícito (el cliente por defecto espera 10 min por petición)
agotaron los 75 minutos del job y lo tumbaron entero. Un enriquecimiento
opcional nunca puede matar al scoring.

Aquí es un paso aparte con `continue-on-error`: si tarda, si falla o si no hay
API key, la lista VALUE ya está publicada y solo se queda sin las columnas
why_cheap. Además lleva presupuesto de tiempo propio, así que no puede
desbordarse por muchos candidatos que haya.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from why_cheap_analyzer import analyze_ticker, apply_to_dataframe, MIN_SCORE_CANDIDATO

CSV = Path('docs/value_opportunities.csv')

PRESUPUESTO_SEG = 420      # 7 min como mucho para todo el enriquecimiento
MAX_TICKERS = 5
MIN_CAIDA_PCT = 8.0


def main() -> None:
    if not CSV.exists():
        print(f'[enrich_why_cheap] {CSV} no existe — nada que enriquecer')
        return

    df = pd.read_csv(CSV)
    if df.empty:
        print('[enrich_why_cheap] lista vacía')
        return

    caida = pd.to_numeric(df.get('proximity_to_52w_high'), errors='coerce').abs()
    score = pd.to_numeric(df.get('value_score'), errors='coerce')
    cand = df[(caida >= MIN_CAIDA_PCT) & (score >= MIN_SCORE_CANDIDATO)].copy()
    cand = cand.sort_values('value_score', ascending=False).head(MAX_TICKERS)

    if cand.empty:
        print('[enrich_why_cheap] ningún candidato con caída que explicar')
        return

    print(f'[enrich_why_cheap] {len(cand)} candidatos · presupuesto {PRESUPUESTO_SEG}s')
    inicio, veredictos = time.monotonic(), {}
    for _, r in cand.iterrows():
        gastado = time.monotonic() - inicio
        if gastado > PRESUPUESTO_SEG:
            print(f'   ⏱️  Presupuesto agotado tras {gastado:.0f}s — '
                  f'{len(veredictos)}/{len(cand)} analizados')
            break
        ticker = str(r['ticker']).upper()
        res = analyze_ticker(ticker, str(r.get('company_name', '')),
                             abs(float(r.get('proximity_to_52w_high') or 0)),
                             float(r.get('relative_strength_6m') or 0))
        veredictos[ticker] = res
        icono = {'DETERIORO': '🚫', 'CICLICO': '🔄', 'EVENTO': '⚡',
                 'SENTIMIENTO': '💭', 'SIN_DATOS': '❓'}.get(res['veredicto'], '❓')
        print(f"   {icono} {ticker}: {res['veredicto']} · {len(res['fuentes'])} fuentes "
              f"· {res['resumen'][:70]}")

    if not veredictos:
        return

    df, deteriorados = apply_to_dataframe(df, veredictos)
    df.to_csv(CSV, index=False)
    print(f'   ✓ {CSV} enriquecido'
          + (f' · fuera por deterioro: {deteriorados}' if deteriorados else ''))


if __name__ == '__main__':
    main()
