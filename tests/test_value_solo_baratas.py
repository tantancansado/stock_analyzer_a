"""La lista VALUE es de empresas baratas cuyo negocio no empeora.

El usuario, 5-nov-2026: «normalmente buscamos acciones que estén baratas sin
que empeore el negocio ni los números, circunstanciales». Ese día, en 6 de las
11 publicadas nuestra valoración no veía recorrido (WST, EFX, NDAQ, FCNCA, PG,
TT). Medido sobre las listas diarias desde febrero, las baratas con las ventas
cayendo quedaban 10-16 puntos por debajo del universo a 180 días, y estar
cerca de máximos no restaba (ver value_bands).
"""
from pathlib import Path

import pandas as pd

from conftest import bloque_de_codigo
from value_bands import motivo_fuera_de_value

RAIZ = Path(__file__).resolve().parent.parent


def _fila(ticker, tri=20.0, div='', dist=-25.0, margen=20.0, ventas=5.0):
    return {'ticker': ticker, 'upside_triangulated_pct': tri, 'upside_divergence': div,
            'proximity_to_52w_high': dist, 'rev_growth_yoy': ventas,
            'health_details': str({'operating_margin_pct': margen, 'roe_pct': 20.0})}


def _motivos(*filas):
    df = pd.DataFrame(list(filas))
    return dict(zip(df['ticker'], motivo_fuera_de_value(df)))


def test_barata_y_creciendo_es_value():
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


def test_barata_con_las_ventas_cayendo_no_es_value():
    m = _motivos(_fila('TRAMPA', ventas=-8.0), _fila('CASI', ventas=-0.4))
    assert m['TRAMPA'] == 'ventas cayendo (-8.0%): el negocio empeora'
    assert m['CASI'] == 'ventas cayendo (-0.4%): el negocio empeora'   # nunca «+0%»


def test_el_escalon_esta_en_caer_no_en_crecer_poco():
    assert _motivos(_fila('PLANA', ventas=0.0))['PLANA'] == ''


def test_sin_dato_de_ventas_no_se_presume_que_el_negocio_va_bien():
    assert _motivos(_fila('X', ventas=float('nan')))['X'].startswith('sin dato de ventas')


def test_cerca_de_maximos_no_es_motivo():
    """La primera versión de la regla las sacaba salvo negocio excepcional; con
    los datos no restaban nada. AMZN crece con margen normal, RELX tiene margen
    alto y crece poco: las dos entran si están baratas y no empeoran."""
    m = _motivos(_fila('AMZN', dist=-0.4, margen=13.9, ventas=20.4),
                 _fila('RELX', dist=-5.8, margen=32.0, ventas=1.7))
    assert m == {'AMZN': '', 'RELX': ''}


def test_un_trimestre_no_tapa_un_año_cayendo():
    """HHH, 6-nov-2026: +330 % en el trimestre por ventas de suelo, -15,8 % en el año."""
    m = _motivos({**_fila('HHH', ventas=330.2), 'ventas_anual_pct': -15.8})
    assert m['HHH'] == 'ventas cayendo en el último año (-15.8%): el negocio empeora'


def test_sin_ventas_anuales_decide_el_trimestre():
    """Europa no tiene TIKR para esto, y un dato que no hay no descarta."""
    assert _motivos({**_fila('EU', ventas=4.0), 'ventas_anual_pct': float('nan')})['EU'] == ''


def test_el_motivo_de_valoracion_va_antes_que_el_de_ventas():
    assert _motivos(_fila('X', tri=2.0, ventas=-5.0))['X'].startswith('nuestra valoración')


def test_las_dos_listas_lo_aplican_antes_del_corte():
    """US y Europa con la misma definición, y antes del corte de puntuación:
    después, los ajustes que suman podían devolver a la lista un descarte."""
    for fichero, desde in (('super_score_integrator.py', '# VALUE opportunities (Section A'),
                           ('european_value_scanner.py', '# ─── Filter: mismo corte')):
        bloque = bloque_de_codigo((RAIZ / fichero).read_text(), desde)
        assert 'motivo_fuera_de_value(' in bloque
        assert bloque.index('motivo_fuera_de_value(') < bloque.index("['value_score'] >= VALUE_SCORE_MIN]")
