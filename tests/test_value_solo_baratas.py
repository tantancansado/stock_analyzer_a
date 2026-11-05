"""La lista VALUE es de empresas baratas, no de buenas empresas a precio justo.

El usuario, 5-nov-2026: «la filosofía no es comprar empresas cercanas a máximos
a no ser que sus datos sean increíbles, tipo Microsoft [...] normalmente
buscamos acciones que estén baratas sin que empeore el negocio». Ese día, en 6
de las 11 publicadas nuestra valoración no veía recorrido (WST, EFX, NDAQ,
FCNCA, PG, TT).
"""
from pathlib import Path

import pandas as pd

from conftest import bloque_de_codigo
from value_bands import CRECIMIENTO_QUE_JUSTIFICA, motivo_fuera_de_value

RAIZ = Path(__file__).resolve().parent.parent


def _fila(ticker, tri=20.0, div='', dist=-25.0, margen=20.0, ventas=5.0):
    return {'ticker': ticker, 'upside_triangulated_pct': tri, 'upside_divergence': div,
            'proximity_to_52w_high': dist, 'rev_growth_yoy': ventas,
            'health_details': str({'operating_margin_pct': margen, 'roe_pct': 20.0})}


def _motivos(*filas):
    # Un universo de relleno fija el cuartil alto del margen en 30%.
    relleno = [_fila(f'R{i}', margen=m) for i, m in enumerate([10, 15, 20, 25, 30, 30, 30, 30])]
    df = pd.DataFrame(list(filas) + relleno)
    return dict(zip(df['ticker'], motivo_fuera_de_value(df)))


def test_barata_y_caida_es_value():
    assert _motivos(_fila('OK'))['OK'] == ''


def test_sin_margen_en_nuestra_valoracion_no_es_value():
    m = _motivos(_fila('WST', tri=-7.6), _fila('PG', tri=-0.1), _fila('BAC', tri=5.4))
    assert m['WST'] == 'nuestra valoración solo le ve -8%'
    assert m['PG'] == 'nuestra valoración solo le ve +0%'      # nunca «-0%»
    assert m['BAC'].startswith('nuestra valoración')


def test_sin_modelos_propios_no_hay_respaldo():
    assert _motivos(_fila('X', tri=float('nan')))['X'] == 'sin valoración propia que la respalde'


def test_si_los_modelos_desmienten_al_analista_no_cuenta():
    assert _motivos(_fila('AVGO', tri=20.0, div='ALTA'))['AVGO'].startswith('nuestra valoración')


def test_cerca_de_maximos_sin_negocio_excepcional_no_es_value():
    m = _motivos(_fila('AMZN', dist=-7.4, margen=13.9, ventas=20.4),   # crece, pero margen normal
                 _fila('RELX', dist=-5.8, margen=32.0, ventas=1.7))    # margen alto, no crece
    assert m['AMZN'] == 'a 7% del máximo sin un negocio excepcional que lo justifique'
    assert m['RELX'].startswith('a 6% del máximo')


def test_cerca_de_maximos_con_negocio_excepcional_si():
    """El caso MSFT: margen del cuartil alto y ventas a doble dígito."""
    assert _motivos(_fila('MSFT', dist=-0.6, margen=49.8, ventas=18.8))['MSFT'] == ''


def test_lejos_del_maximo_no_se_le_pide_ser_excepcional():
    assert _motivos(_fila('UNH', dist=-10.8, margen=5.8, ventas=-0.4))['UNH'] == ''


def test_sin_distancia_al_maximo_no_se_presume_que_este_cerca():
    assert _motivos(_fila('X', dist=float('nan'), margen=5.0))['X'] == ''


def test_el_crecimiento_que_justifica_es_de_doble_digito():
    assert CRECIMIENTO_QUE_JUSTIFICA >= 10


def test_las_dos_listas_lo_aplican_antes_del_corte():
    """US y Europa con la misma definición, y antes del corte de puntuación:
    después, los ajustes que suman podían devolver a la lista un descarte."""
    for fichero, desde in (('super_score_integrator.py', '# VALUE opportunities (Section A'),
                           ('european_value_scanner.py', '# ─── Filter: mismo corte')):
        bloque = bloque_de_codigo((RAIZ / fichero).read_text(), desde)
        assert 'motivo_fuera_de_value(' in bloque
        assert bloque.index('motivo_fuera_de_value(') < bloque.index("['value_score'] >= VALUE_SCORE_MIN]")
