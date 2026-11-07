#!/usr/bin/env python3
"""Los descartes duros de VALUE: ROE negativo y analistas por debajo del precio.

Son reglas que el usuario ha reiterado («NUNCA dar scores cuando el dato es
default/missing») y están en CLAUDE.md. Antes este fichero las comprobaba sobre
una copia de la lógica; ahora ejercita la función que usa el integrator.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from value_bands import nota_value, vetos_value


def _fila(**extra):
    return {'ticker': 'X', 'upside_triangulated_pct': 25.0, 'upside_divergence': '', 'rev_growth_yoy': 12.0, 'ventas_anual_pct': 12.0,
            'per_z': -1.5, 'fcf_yield_pct': 5.0, 'analyst_upside_pct': 20.0, 'negative_roe': False, **extra}


def _veto(**extra):
    return bool(vetos_value(pd.DataFrame([_fila(**extra)])).iloc[0])


def test_roe_negativo_es_veto():
    assert _veto(negative_roe=True)


def test_leido_de_un_csv_es_texto():
    """bool('False') es True: leída de un CSV, esta columna vetaba a toda la lista."""
    assert not _veto(negative_roe='False') and _veto(negative_roe='True')
    assert not _veto(negative_roe=float('nan'))


def test_analistas_por_debajo_del_precio_es_veto():
    assert _veto(analyst_upside_pct=-12.5)


def test_upside_cero_no_es_veto():
    assert not _veto(analyst_upside_pct=0.0)


def test_sin_analistas_no_es_veto():
    """Sin cobertura no hay opinión de los analistas, no una opinión negativa."""
    assert not _veto(analyst_upside_pct=float('nan'))


def test_cerebro_no_veta():
    """Medido: lo que vetaba con AVOID rindió +8,6 a 90 días frente a -1,5 de lo neutro."""
    assert not _veto(cerebro_signal='AVOID') and not _veto(cerebro_signal='EXIT')


def test_sin_columnas_no_veta_a_nadie():
    assert not vetos_value(pd.DataFrame({'ticker': ['X']})).any()


def test_un_valor_por_defecto_no_da_puntos():
    """fundamental_score y ml_score de 50 (dato ausente) no entran en la nota: dos
    empresas iguales en lo demás sacan lo mismo tengan el dato o no."""
    a, b = _fila(fundamental_score=50.0, ml_score=50.0), _fila(fundamental_score=91.0, ml_score=88.0)
    notas = nota_value(pd.DataFrame([a, b]))['value_score']
    assert notas.iloc[0] == notas.iloc[1]
