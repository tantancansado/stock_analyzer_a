#!/usr/bin/env python3
"""Las funciones del camino crítico, ejecutadas contra los CSV PUBLICADOS
leídos con pandas — que es como les llegan los datos en el pipeline.

Existe por el fallo del 23-sep-2026: `fcf_es_caja_libre` hacía
`(pick.get('campo') or '').strip()` y al leer un CSV pandas convierte las
celdas vacías en NaN, que es un float y además *truthy*: `nan or ''` devuelve
nan y `nan.strip()` lanza AttributeError. Tumbó
`Run Super Score Integration [CRITICAL]` y con él los veinte pasos
siguientes del job.

Los tests unitarios pasaban porque usaban diccionarios limpios. La prueba
que lo habría evitado es esta: recorrer el fichero de verdad.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pd = pytest.importorskip('pandas')
RAIZ = Path(__file__).resolve().parents[1]


def _csv(nombre):
    p = RAIZ / 'docs' / nombre
    if not p.exists():
        pytest.skip(f'sin {nombre}')
    df = pd.read_csv(p)
    if df.empty:
        pytest.skip(f'{nombre} vacío')
    return df


def _todas_las_filas(df, fn, nombre):
    fallos = []
    for _, r in df.iterrows():
        try:
            fn(r.to_dict())
        except Exception as e:      # noqa: BLE001 — se quiere el tipo exacto
            fallos.append(f"{r.get('ticker')}: {type(e).__name__}: {e}")
    assert not fallos, f'{nombre} revienta con filas reales:\n  ' + '\n  '.join(fallos[:5])


class TestConFilasDeVerdad:

    @pytest.mark.parametrize('fichero', [
        'value_opportunities.csv',
        'value_opportunities_filtered.csv',
        'european_value_opportunities.csv',
    ])
    def test_fcf_es_caja_libre(self, fichero):
        from data_integrity import fcf_es_caja_libre
        _todas_las_filas(_csv(fichero), fcf_es_caja_libre, 'fcf_es_caja_libre')

    def test_check_row(self):
        from data_integrity import check_row
        _todas_las_filas(_csv('value_opportunities.csv'),
                         lambda d: check_row(d, require_value_fields=False), 'check_row')

    def test_conviction_score(self):
        from conviction_filter import calculate_conviction_score
        _todas_las_filas(_csv('value_opportunities.csv'),
                         calculate_conviction_score, 'calculate_conviction_score')

    def test_el_bloque_de_bonus_fcf_del_integrator(self):
        """Réplica del bloque que falló, con el CSV real."""
        from data_integrity import fcf_es_caja_libre
        df = _csv('value_opportunities.csv').copy()
        df['_fcf'] = pd.to_numeric(df['fcf_yield_pct'], errors='coerce')
        interpretable = df.apply(lambda r: fcf_es_caja_libre(r.to_dict()), axis=1)
        df.loc[~interpretable, '_fcf'] = pd.NA
        assert len(interpretable) == len(df)


class TestElPatronQueFallo:
    """`x or ''` no protege de NaN, y por eso no se usa con datos de pandas."""

    def test_nan_es_truthy(self):
        import math
        nan = float('nan')
        assert bool(nan) is True, 'por esto `nan or ""` devuelve nan'
        assert math.isnan(nan or '')

    def test_el_helper_lo_absorbe(self):
        from data_integrity import _texto
        for v in (float('nan'), None, '', '  ', pd.NA):
            assert _texto(v) == ''
        assert _texto('  Banks  ') == 'Banks'
        assert _texto(3.5) == '3.5'
