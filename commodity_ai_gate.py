#!/usr/bin/env python3
"""Filtro de IA de materias primas: un rating atractivo solo se publica verificado.

El rating de `commodity_scanner` sale de tres números (precio frente a su media
de dos años, posición en el rango anual, estacionalidad). Es una regla de
reversión a la media: no sabe POR QUÉ está barato el fondo. Un fondo de futuros
(UNG, USO...) arrastra el coste de renovar contratos y puede parecer barato años
sin que la materia prima lo sea; un minero (COPX) no es el metal.

Mismo criterio que el gate de Value: fail-closed. Un ATRACTIVO / MUY_ATRACTIVO
sin verificar se enseña como «sin verificar», no como señal. Nada se quita de la
tabla: la fila sigue, lo que cambia es lo que se afirma de ella.

Coste: una sola llamada con solo los candidatos (suelen ser 1-4), y ninguna si
no hay ninguno.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from groq_utils import CLAUDE_HAIKU, claude_chat

CSV = Path('docs/commodity_opportunities.csv')
ATRACTIVOS = ('MUY_ATRACTIVO', 'ATRACTIVO')

SYSTEM = """Eres el auditor de un inversor que compra a 12 meses vista y vende a precio objetivo.
Recibes fichas de ETF de materias primas que una regla mecánica marcó como baratos
(precio frente a su media de 2 años y posición en su rango anual). Tu trabajo es decir,
para cada uno, si ese «barato» se sostiene o si es un espejismo.

Desconfía cuando:
- `estructura` es «futuros»: el fondo pierde por renovar contratos (contango), así que
  su precio puede estar bajo sin que la materia prima lo esté.
- `estructura` es «mineras»: es renta variable de empresas, no el metal.
- La narrativa (si la hay) explica la caída por un cambio permanente de oferta o demanda.
- Cae con fuerza sin ninguna causa conocida: no la inventes, dilo.

Reglas: usa SOLO los datos que te doy, no inventes cifras ni noticias. Si no hay narrativa,
la causa no está investigada: dilo en el motivo y verifica solo si precio y estructura
sostienen el rating por sí solos. Prefiere rechazar a avalar algo dudoso.

Responde SOLO JSON: {"resultados":[{"ticker":"X","verificado":true|false,"motivo":"una frase en español llano, máximo 140 caracteres"}]}"""


def _ficha(r: dict) -> dict:
    campos = ('ticker', 'sector', 'value_rating', 'etf_estructura', 'price',
              'pct_vs_2y_avg', 'pct_from_high', 'range_position',
              'momentum_signal', 'seasonality', 'expense_ratio_pct',
              'ai_narrative_veredicto', 'ai_narrative_resumen', 'ai_narrative_fecha')
    out = {k: r.get(k) for k in campos if r.get(k) not in (None, '')}
    if 'etf_estructura' in out:
        out['estructura'] = out.pop('etf_estructura')
    return out


def _interpretar(raw: str | None) -> dict[str, dict]:
    if not raw:
        return {}
    texto = raw.strip()
    if texto.startswith('```'):
        texto = texto.split('```')[1].removeprefix('json').strip()
    try:
        data = json.loads(texto)
    except ValueError:
        return {}
    out = {}
    for item in data.get('resultados', []):
        t = str(item.get('ticker', '')).upper()
        if t and isinstance(item.get('verificado'), bool):
            out[t] = {'verificado': item['verificado'],
                      'motivo': str(item.get('motivo', ''))[:160]}
    return out


def verificar(rows: list[dict]) -> None:
    """Rellena `ai_verified` y `ai_gate_motivo` en cada fila, en sitio."""
    for r in rows:
        r['ai_verified'] = ''
        r['ai_gate_motivo'] = ''

    candidatos = [r for r in rows if r.get('value_rating') in ATRACTIVOS]
    if not candidatos:
        print('[commodity_ai_gate] ningún ETF atractivo hoy — sin llamada, sin coste')
        return

    # Un dato malo no se avala: la fila ya viene como SIN_DATO y no entra aquí,
    # pero si llegara un atractivo con `data_ok` falso, se rechaza sin preguntar.
    a_preguntar = []
    for r in candidatos:
        if str(r.get('data_ok')) == 'False':
            r['ai_verified'] = 'False'
            r['ai_gate_motivo'] = r.get('data_motivo') or 'dato no fiable'
        else:
            a_preguntar.append(r)

    veredictos: dict[str, dict] = {}
    if a_preguntar:
        raw = claude_chat(
            [{'role': 'user', 'content': 'Fichas:\n' + json.dumps(
                [_ficha(r) for r in a_preguntar], ensure_ascii=False)}],
            model=CLAUDE_HAIKU, system=SYSTEM, max_tokens=1500, temperature=0.0)
        veredictos = _interpretar(raw)
        if not veredictos:
            print('[commodity_ai_gate] ⚠️  sin respuesta utilizable de la IA — '
                  'los atractivos quedan SIN VERIFICAR (fail-closed)')

    for r in a_preguntar:
        v = veredictos.get(str(r['ticker']).upper())
        if v is None:
            r['ai_verified'] = 'False'
            r['ai_gate_motivo'] = 'sin verificar: la IA no respondió'
            continue
        r['ai_verified'] = str(v['verificado'])
        r['ai_gate_motivo'] = v['motivo']
        marca = '✓' if v['verificado'] else '✗'
        print(f"   {marca} {r['ticker']:7s} {v['motivo']}")


def main() -> None:
    if not CSV.exists():
        print(f'[commodity_ai_gate] {CSV} no existe')
        return
    with CSV.open(newline='') as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        campos = list(reader.fieldnames or [])
    if not rows:
        return
    verificar(rows)
    for c in ('ai_verified', 'ai_gate_motivo'):
        if c not in campos:
            campos.append(c)
    with CSV.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(rows)


if __name__ == '__main__':
    main()
