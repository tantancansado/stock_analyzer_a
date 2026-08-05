#!/usr/bin/env python3
"""
Enrich Commodity Narrative — añade a commodity_opportunities.csv el motivo real
de cada movimiento de precio, con fuentes.

Vive fuera de commodity_scanner.py por el mismo motivo que enrich_why_cheap.py
vive fuera de super_score_integrator.py: son búsquedas web que pueden tardar
minutos, y el scanner determinista no puede depender de eso para publicar.
Paso opcional, con presupuesto de tiempo propio — si falla o no hay API key, el
CSV ya está publicado y solo se queda sin las columnas de narrativa.
"""
from __future__ import annotations

import csv
from pathlib import Path

from commodity_narrative_analyzer import enrich

CSV = Path('docs/commodity_opportunities.csv')


def main() -> None:
    if not CSV.exists():
        print(f'[enrich_commodity_narrative] {CSV} no existe — nada que enriquecer')
        return

    with CSV.open(newline='') as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if not rows:
        print('[enrich_commodity_narrative] CSV vacío')
        return

    print(f'[enrich_commodity_narrative] {len(rows)} commodities en el universo')
    veredictos = enrich(rows)
    if not veredictos:
        print('   Sin veredictos — Claude no disponible o presupuesto agotado antes del primero')
        return

    nuevas = ('ai_narrative_veredicto', 'ai_narrative_resumen', 'ai_narrative_fuentes')
    for c in nuevas:
        if c not in fieldnames:
            fieldnames.append(c)

    for r in rows:
        v = veredictos.get(str(r.get('ticker', '')).upper())
        if v:
            r['ai_narrative_veredicto'] = v['veredicto']
            r['ai_narrative_resumen'] = v['resumen']
            r['ai_narrative_fuentes'] = ' | '.join(v['fuentes'])

    with CSV.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'   ✓ {CSV} enriquecido con {len(veredictos)} narrativas')


if __name__ == '__main__':
    main()
