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

Hasta el 5-ago-2026 solo procesaba `value_opportunities.csv` (US) — mismo bug
que tuvo `technical_filter.py` con el timing técnico: la lista europea nunca
entraba en la selección de candidatos, ni un ticker. El presupuesto y el
límite de candidatos siguen siendo TOTALES entre ambas listas, no se duplica
el gasto de API por añadir un universo.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from why_cheap_analyzer import analyze_ticker, apply_to_dataframe, MIN_SCORE_CANDIDATO

DOCS = Path('docs')
TARGET_CSVS: list[Path] = [
    DOCS / 'value_opportunities.csv',
    DOCS / 'european_value_opportunities.csv',
]

# El presupuesto es un tope REAL, no orientativo: antes se comprobaba sólo
# "¿me he pasado ya?" antes de arrancar cada ticker, así que siempre se podía
# desbordar por el coste entero del último. El 7-ago-2026 gastó 527s con
# presupuesto de 420 (+25%), y el job core-scoring va a 78-84 min sobre un
# tope de 90: ese desbordamiento sale del margen que evita que el job muera.
# Ahora se reserva el coste estimado del siguiente antes de empezarlo.
PRESUPUESTO_SEG = 600
COSTE_TICKER_SEG = 175.0   # medido: BR 178s, SAP 148s, MSFT 201s (timeout)
MAX_TICKERS = 5

# Una caída del 8% no es un castigo, es ruido — y explicarla cuesta lo mismo
# que explicar una de verdad. El 7-ago-2026 MSFT entró con -9,7% del máximo,
# se llevó 201s de los 420 (timeout de Claude, 100s + reintento) y dejó fuera
# a MCO (-13,5%, la única candidata que pasa zona dorada + sector + valoración
# coherente). Este módulo existe para separar castigo de deterioro; por debajo
# de ~12% no hay castigo que separar.
MIN_CAIDA_PCT = 12.0


def _candidatos(csv: Path) -> pd.DataFrame:
    """Filas de un CSV que merecen why_cheap, con la columna 'origen_csv' añadida."""
    if not csv.exists():
        print(f'[enrich_why_cheap] {csv} no existe — se omite')
        return pd.DataFrame()
    df = pd.read_csv(csv)
    if df.empty:
        return pd.DataFrame()
    caida = pd.to_numeric(df.get('proximity_to_52w_high'), errors='coerce').abs()
    score = pd.to_numeric(df.get('value_score'), errors='coerce')
    cand = df[(caida >= MIN_CAIDA_PCT) & (score >= MIN_SCORE_CANDIDATO)].copy()
    cand['origen_csv'] = str(csv)
    return cand


def main() -> None:
    frames = {str(csv): pd.read_csv(csv) for csv in TARGET_CSVS if csv.exists()}
    if not frames:
        print('[enrich_why_cheap] ningún universo con datos — nada que enriquecer')
        return

    candidatos = pd.concat([_candidatos(csv) for csv in TARGET_CSVS], ignore_index=True)
    if candidatos.empty:
        print('[enrich_why_cheap] ningún candidato con caída que explicar')
        return

    cand = candidatos.sort_values('value_score', ascending=False).head(MAX_TICKERS)

    print(f'[enrich_why_cheap] {len(cand)} candidatos de {len(frames)} universo(s) '
          f'· presupuesto {PRESUPUESTO_SEG}s')
    inicio = time.monotonic()
    # veredictos por CSV de origen, para no mezclar tickers de US/EU al aplicar
    veredictos_por_csv: dict[str, dict] = {str(csv): {} for csv in TARGET_CSVS}
    reserva = COSTE_TICKER_SEG   # lo que hay que dejar libre para el siguiente
    for _, r in cand.iterrows():
        gastado = time.monotonic() - inicio
        # Reservar antes de empezar, no comprobar después de pasarse: si no cabe
        # entero, no se arranca. Así el presupuesto es un techo de verdad.
        if gastado + reserva > PRESUPUESTO_SEG:
            total = sum(len(v) for v in veredictos_por_csv.values())
            print(f'   ⏱️  Sin margen para otro ticker ({gastado:.0f}s gastados de '
                  f'{PRESUPUESTO_SEG}s, hacen falta ~{reserva:.0f}s) — {total}/{len(cand)} analizados')
            break
        ticker = str(r['ticker']).upper()
        t0 = time.monotonic()
        res = analyze_ticker(ticker, str(r.get('company_name', '')),
                             abs(float(r.get('proximity_to_52w_high') or 0)),
                             float(r.get('relative_strength_6m') or 0))
        # La reserva sigue al peor caso visto en esta corrida: si un ticker se
        # atasca, el siguiente exige más margen en vez de repetir el atasco.
        reserva = max(reserva, time.monotonic() - t0)
        veredictos_por_csv[r['origen_csv']][ticker] = res
        icono = {'DETERIORO': '🚫', 'CICLICO': '🔄', 'EVENTO': '⚡',
                 'SENTIMIENTO': '💭', 'SIN_DATOS': '❓'}.get(res['veredicto'], '❓')
        print(f"   {icono} {ticker}: {res['veredicto']} · {len(res['fuentes'])} fuentes "
              f"· {res['resumen'][:70]}")

    for csv_path, veredictos in veredictos_por_csv.items():
        if not veredictos:
            continue
        df = frames[csv_path]
        df, deteriorados = apply_to_dataframe(df, veredictos)
        df.to_csv(csv_path, index=False)
        print(f'   ✓ {csv_path} enriquecido'
              + (f' · fuera por deterioro: {deteriorados}' if deteriorados else ''))


if __name__ == '__main__':
    main()
