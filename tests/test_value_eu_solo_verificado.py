"""Value Europa enseña lo que el gate verificó, igual que Value US.

El grado de convicción europeo se calcula desde el escáner SIN filtrar, no
desde lo verificado: el 1-oct-2026 european_value_conviction.csv tenía 11
empresas que el gate había descartado (NESN, SIKA, SGE...) y le faltaban 11 que
sí había dado por buenas (ASML, AZN, Inditex...). La pantalla y la API leían
conviction, así que enseñaban lo contrario de lo verificado.

Además el ajuste de Owner Earnings se aplicaba a todos los CSV europeos menos
al filtrado: AUTO.L (RELIABLE/AVOID, -8) saldría con 59,6 en vez de 51,6.
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import apply_oe_ai_adjustment as oe
import ticker_api


def test_el_parche_de_oe_cubre_el_csv_europeo_filtrado():
    nombres = {p.name for p in oe.TARGET_CSVS}
    assert 'european_value_opportunities_filtered.csv' in nombres


def test_el_parche_de_oe_rebaja_a_auto_l_tambien_en_el_filtrado(tmp_path, monkeypatch):
    csv = tmp_path / 'european_value_opportunities_filtered.csv'
    pd.DataFrame({'ticker': ['AUTO.L', 'ASML.AS'], 'value_score': [59.6, 70.0]}).to_csv(csv, index=False)
    by_ticker = {'AUTO.L': {'score_adjustment': -8, 'oe_ai_verdict': 'RELIABLE/AVOID (-8)'}}
    oe.patch_csv(csv, by_ticker)
    df = pd.read_csv(csv).set_index('ticker')
    assert round(df.loc['AUTO.L', 'value_score'], 1) == 51.6
    assert df.loc['AUTO.L', 'oe_ai_verdict'] == 'RELIABLE/AVOID (-8)'
    assert df.loc['ASML.AS', 'value_score'] == 70.0


def test_la_api_europea_solo_sirve_lo_verificado(tmp_path, monkeypatch):
    docs = tmp_path
    pd.DataFrame({'ticker': ['ASML.AS'], 'value_score': [70.0]}).to_csv(
        docs / 'european_value_opportunities_filtered.csv', index=False)
    # Un nombre que el gate descartó pero que el grado sí conoce
    pd.DataFrame({'ticker': ['NESN.SW'], 'value_score': [31.7], 'conviction_grade': ['C']}).to_csv(
        docs / 'european_value_conviction.csv', index=False)
    monkeypatch.setattr(ticker_api, 'DOCS', docs)
    with ticker_api.app.test_request_context():
        resp = ticker_api.eu_value_opportunities()
    cuerpo = json.loads(resp.get_data(as_text=True))
    assert [r['ticker'] for r in cuerpo['data']] == ['ASML.AS']
    assert cuerpo['source'] == 'ai_filtered'


def test_la_api_europea_con_cero_verificados_devuelve_vacio(tmp_path, monkeypatch):
    pd.DataFrame({'ticker': [], 'value_score': []}).to_csv(
        tmp_path / 'european_value_opportunities_filtered.csv', index=False)
    pd.DataFrame({'ticker': ['NESN.SW'], 'value_score': [31.7]}).to_csv(
        tmp_path / 'european_value_conviction.csv', index=False)
    pd.DataFrame({'ticker': ['NESN.SW'], 'value_score': [31.7]}).to_csv(
        tmp_path / 'european_value_opportunities.csv', index=False)
    monkeypatch.setattr(ticker_api, 'DOCS', tmp_path)
    with ticker_api.app.test_request_context():
        resp = ticker_api.eu_value_opportunities()
    assert json.loads(resp.get_data(as_text=True))['data'] == []


# ── el grado europeo sale de lo verificado ────────────────────────────────
def test_el_grado_europeo_se_calcula_sobre_lo_verificado(tmp_path, monkeypatch):
    import conviction_filter as cf
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'docs').mkdir()
    # El escáner sin filtrar trae NESN; el gate solo verificó ASML
    pd.DataFrame({'ticker': ['ASML.AS', 'NESN.SW']}).to_csv(
        'docs/european_value_opportunities.csv', index=False)
    pd.DataFrame({'ticker': ['ASML.AS']}).to_csv(
        'docs/european_value_opportunities_filtered.csv', index=False)
    entradas = []
    monkeypatch.setattr(cf, 'filter_by_conviction',
                        lambda entrada, **kw: entradas.append(entrada) or 0)
    monkeypatch.setattr(sys, 'argv', ['conviction_filter.py', '--european-only'])
    cf.main()
    assert entradas == ['docs/european_value_opportunities_filtered.csv']


def test_sin_lista_verificada_no_se_cae_al_escaner(tmp_path, monkeypatch):
    import conviction_filter as cf
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'docs').mkdir()
    pd.DataFrame({'ticker': ['NESN.SW']}).to_csv(
        'docs/european_value_opportunities.csv', index=False)
    entradas = []
    monkeypatch.setattr(cf, 'filter_by_conviction',
                        lambda entrada, **kw: entradas.append(entrada) or None)
    monkeypatch.setattr(sys, 'argv', ['conviction_filter.py', '--european-only'])
    cf.main()
    assert 'docs/european_value_opportunities.csv' not in entradas
