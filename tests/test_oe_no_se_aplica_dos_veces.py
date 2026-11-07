"""El ajuste de Owner Earnings cuenta una vez, y en Value US no cuenta.

El integrator sumaba a `value_score` el ajuste del JSON de la víspera y más tarde
`apply_oe_ai_adjustment` volvía a sumar el del día encima. Con el mismo veredicto
los dos días, un -8 restaba 16. El 6-nov-2026 eso sacó seis empresas de la lista
VALUE: el integrator dejó 21 y salieron 15. Desde el 7-nov Value US ordena por
value_bands.nota_value y el veredicto solo se anota; en Europa sigue puntuando.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import apply_oe_ai_adjustment as oe


def _parchear(tmp_path, filas, por_ticker, nombre='european_value_opportunities.csv'):
    csv = tmp_path / nombre
    pd.DataFrame(filas).to_csv(csv, index=False)
    oe.patch_csv(csv, por_ticker)
    return csv, pd.read_csv(csv).set_index('ticker')


def test_mismo_veredicto_que_ayer_no_vuelve_a_restar(tmp_path):
    _, df = _parchear(tmp_path, [{'ticker': 'RMD', 'value_score': 62.3, 'oe_ai_adjustment': -5}],
                      {'RMD': {'score_adjustment': -5}})
    assert df.loc['RMD', 'value_score'] == 62.3
    assert df.loc['RMD', 'oe_ai_adjustment'] == -5


def test_veredicto_nuevo_sustituye_al_de_ayer(tmp_path):
    _, df = _parchear(tmp_path, [{'ticker': 'X', 'value_score': 50.0, 'oe_ai_adjustment': -8}],
                      {'X': {'score_adjustment': 3}})
    assert df.loc['X', 'value_score'] == 61.0
    assert df.loc['X', 'oe_ai_adjustment'] == 3


def test_sin_ajuste_previo_se_aplica_una_vez(tmp_path):
    _, df = _parchear(tmp_path, [{'ticker': 'X', 'value_score': 50.0}], {'X': {'score_adjustment': -8}})
    assert df.loc['X', 'value_score'] == 42.0


def test_si_hoy_no_hay_veredicto_se_retira_el_de_ayer(tmp_path):
    _, df = _parchear(tmp_path, [{'ticker': 'X', 'value_score': 42.0, 'oe_ai_adjustment': -8}],
                      {'OTRA': {'score_adjustment': -8}})
    assert df.loc['X', 'value_score'] == 50.0
    assert df.loc['X', 'oe_ai_adjustment'] == 0


def test_un_ajuste_ya_contado_no_saca_a_nadie_de_la_lista(tmp_path):
    """GGG, 6-nov-2026: BUY de la IA y fuera de la lista por un -8 restado dos veces."""
    _, df = _parchear(tmp_path, [{'ticker': 'GGG', 'value_score': 33.0, 'oe_ai_adjustment': -8}],
                      {'GGG': {'score_adjustment': -8}})
    assert 'GGG' in df.index


def test_un_ajuste_nuevo_si_puede_sacarla(tmp_path):
    _, df = _parchear(tmp_path, [{'ticker': 'X', 'value_score': 33.0, 'oe_ai_adjustment': 0}],
                      {'X': {'score_adjustment': -8}})
    assert 'X' not in df.index


def test_aplicarlo_dos_veces_da_lo_mismo(tmp_path):
    csv, _ = _parchear(tmp_path, [{'ticker': 'X', 'value_score': 50.0}], {'X': {'score_adjustment': -8}})
    oe.patch_csv(csv, {'X': {'score_adjustment': -8}})
    assert pd.read_csv(csv).set_index('ticker').loc['X', 'value_score'] == 42.0


def test_en_value_us_el_veredicto_se_anota_pero_no_mueve_la_nota(tmp_path):
    for nombre in ('value_opportunities.csv', 'value_opportunities_filtered.csv', 'value_conviction.csv'):
        _, df = _parchear(tmp_path, [{'ticker': 'X', 'value_score': 41.0, 'oe_ai_adjustment': 0}],
                          {'X': {'score_adjustment': -10, 'oe_ai_verdict': 'UNRELIABLE/AVOID (-10)'}}, nombre)
        assert df.loc['X', 'value_score'] == 41.0
        assert df.loc['X', 'oe_ai_adjustment'] == -10
        assert df.loc['X', 'oe_ai_verdict'] == 'UNRELIABLE/AVOID (-10)'


def test_en_value_us_no_saca_a_nadie(tmp_path):
    _, df = _parchear(tmp_path, [{'ticker': 'X', 'value_score': 12.0}], {'X': {'score_adjustment': -8}},
                      'value_opportunities_filtered.csv')
    assert 'X' in df.index
