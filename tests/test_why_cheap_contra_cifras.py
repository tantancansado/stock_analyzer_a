"""Una causa que las propias cuentas desmienten no se publica como causa."""
import pandas as pd

import why_cheap_analyzer as w

JKHY = "{'eps_growth_yoy': -12.8, 'op_growth_yoy': -12.2, 'crecimiento_respaldado': True}"


def test_el_caso_real_de_jkhy_se_veta():
    df = pd.DataFrame([{'ticker': 'JKHY', 'earnings_details': JKHY}])
    v = {'JKHY': {'veredicto': 'SENTIMIENTO', 'resumen': 'EPS +12%, guidance subida', 'fuentes': []}}
    out, _ = w.apply_to_dataframe(df, v)
    assert out.iloc[0]['why_cheap'] == 'SIN_DATOS'
    assert '12%' in out.iloc[0]['why_cheap_resumen']


def test_sentimiento_con_cuentas_sanas_se_respeta():
    df = pd.DataFrame([{'ticker': 'BR', 'earnings_details': "{'eps_growth_yoy': 6.4, 'op_growth_yoy': 9.5}"}])
    out, _ = w.apply_to_dataframe(df, {'BR': {'veredicto': 'SENTIMIENTO', 'resumen': 'x', 'fuentes': []}})
    assert out.iloc[0]['why_cheap'] == 'SENTIMIENTO'


def test_ciclico_o_evento_pueden_explicar_una_caida_del_beneficio():
    for ver in ('CICLICO', 'EVENTO'):
        assert w.contradice_las_cifras(ver, {'earnings_details': JKHY}) is None


def test_sin_cifras_no_se_inventa_contradiccion():
    assert w.contradice_las_cifras('SENTIMIENTO', {'earnings_details': ''}) is None
    assert w.cifras_propias({}) == ''


def test_el_prompt_lleva_las_cifras_propias():
    txt = w.cifras_propias({'earnings_details': JKHY})
    assert 'resultado operativo -12.2%' in txt and 'BPA -12.8%' in txt
    assert 'mandan estas' in txt
    assert '{cifras}' in w.PROMPT
