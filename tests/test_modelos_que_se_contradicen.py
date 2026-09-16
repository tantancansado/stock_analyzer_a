"""
`upside_triangulated_pct` era, en un tercio de los casos, el número del analista.

La divergencia que ya existía solo miraba analista-CONTRA-modelos. El desacuerdo
de los modelos ENTRE ELLOS no lo miraba nadie, y es la mitad del universo:
medido el 16-sep-2026 sobre las 63 filas con DCF y P/E, la mediana de
|DCF − P/E| son 38,8 puntos de upside, y en el 32% uno dice BARATA y el otro CARA.

Ahí la «triangulación» es una ficción. Cuando el analista cae entre los dos
modelos —que es justo lo que pasa cuando se contradicen— la mediana de tres ES
el analista: ocurría en 14 de esas 20 filas.

    EQIX   DCF +54,3%   P/E −55,1%   «triangulado» 22,5 = el analista clavado
    AXP    DCF +50,0%   P/E −44,7%   ídem
    NUE    DCF −50,6%   P/E +47,6%   ídem

El corte no es un umbral inventado: es el signo. No existe un valor verdadero
entre «un 50% barata» y «un 45% cara» — son dos respuestas a la misma pregunta,
no dos medidas del mismo número. El código ya aplicaba exactamente ese
razonamiento al caso de CERO modelos válidos ("dejarlo en NaN en vez de devolver
el upside del analista disfrazado de mediana de tres fuentes"); dos modelos que
se contradicen son, para esto, lo mismo.
"""
import numpy as np
import pandas as pd

from upside_triangulation import DISPERSION_ALTA_PTS, add_upside_triangulation


def _df(filas):
    return pd.DataFrame(filas)


def test_si_discrepan_en_el_signo_no_hay_triangulacion():
    r = add_upside_triangulation(_df([{
        'ticker': 'EQIX', 'analyst_upside_pct': 22.5,
        'target_price_dcf_upside_pct': 54.3, 'target_price_pe_upside_pct': -55.1,
    }]))
    assert r.loc[0, 'modelos_acuerdo'] == 'CONTRADICEN'
    assert pd.isna(r.loc[0, 'upside_triangulated_pct']), \
        'la mediana de dos respuestas contrarias no estima nada'


def test_y_tampoco_hay_divergencia_que_medir():
    """Si los modelos no tienen una opinión conjunta, no se puede medir cuánto
    se separa el analista de ella."""
    r = add_upside_triangulation(_df([{
        'ticker': 'AXP', 'analyst_upside_pct': 15.9,
        'target_price_dcf_upside_pct': 50.0, 'target_price_pe_upside_pct': -44.7,
    }]))
    assert (r.loc[0, 'upside_divergence'] or '') == ''


def test_si_coinciden_la_triangulacion_se_mantiene():
    r = add_upside_triangulation(_df([{
        'ticker': 'AAA', 'analyst_upside_pct': 15.0,
        'target_price_dcf_upside_pct': 18.0, 'target_price_pe_upside_pct': 12.0,
    }]))
    assert r.loc[0, 'modelos_acuerdo'] == 'COHERENTES'
    assert r.loc[0, 'upside_triangulated_pct'] == 15.0


def test_mismo_signo_pero_muy_separados_es_un_aviso_no_una_anulacion():
    """45 puntos es el percentil 75 de |DCF − P/E| entre las que sí coinciden en
    signo. Es un aviso al usuario, no un filtro: la mediana sigue estimando algo
    cuando los dos apuntan al mismo lado."""
    r = add_upside_triangulation(_df([{
        'ticker': 'BBB', 'analyst_upside_pct': 20.0,
        'target_price_dcf_upside_pct': 5.0,
        'target_price_pe_upside_pct': 5.0 + DISPERSION_ALTA_PTS + 10,
    }]))
    assert r.loc[0, 'modelos_acuerdo'] == 'DISPERSOS'
    assert not pd.isna(r.loc[0, 'upside_triangulated_pct'])


def test_se_publica_cuanto_se_separan():
    r = add_upside_triangulation(_df([{
        'ticker': 'CCC', 'analyst_upside_pct': 10.0,
        'target_price_dcf_upside_pct': 30.0, 'target_price_pe_upside_pct': -10.0,
    }]))
    assert r.loc[0, 'modelos_dispersion_pts'] == 40.0


def test_sobre_el_universo_real_los_que_pierden_la_triangulacion_la_tenian_falsa():
    from pathlib import Path
    import pytest
    f = Path(__file__).parent.parent / 'docs' / 'value_opportunities.csv'
    if not f.exists():
        pytest.skip('sin CSV VALUE')
    d = pd.read_csv(f)
    if d.empty or 'target_price_dcf_upside_pct' not in d.columns:
        pytest.skip('sin modelos propios en el CSV')
    r = add_upside_triangulation(d.drop(columns=[c for c in (
        'upside_divergence', 'upside_triangulated_pct', 'upside_divergence_pts') if c in d.columns]).copy())
    an = pd.to_numeric(d['analyst_upside_pct'], errors='coerce')
    antes = pd.to_numeric(d.get('upside_triangulated_pct'), errors='coerce')
    pierden = antes.notna() & r['upside_triangulated_pct'].isna()
    if not pierden.any():
        pytest.skip('hoy no hay modelos que se contradigan')
    era_el_analista = ((antes - an).abs() < 0.05) & pierden
    assert era_el_analista.sum() >= pierden.sum() * 0.5, \
        'si se anula una triangulación, la mayoría de las veces debe ser porque era el analista disfrazado'
