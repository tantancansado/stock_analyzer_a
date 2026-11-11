"""La recomendación de opciones respeta el tamaño de la posición y el precio objetivo."""
import ticker_api as api

EXPIRIES = [{'expiry': '2026-11-13', 'days_out': 21,
             'covered_calls': [{'strike': 415.0}, {'strike': 430.0}],
             'protective_puts': [{'strike': 345.0}]}]


def test_sobreponderada_es_pasar_del_techo():
    assert api._sobreponderada({'portfolio_pct': 16.7, 'peso_techo_pct': 9.0})
    assert not api._sobreponderada({'portfolio_pct': 9.0, 'peso_techo_pct': 9.0})
    assert not api._sobreponderada({'portfolio_pct': 16.7, 'peso_techo_pct': None})


def test_no_se_publica_vender_puts_para_añadir_si_ya_sobra():
    row = {'action': 'MANTENER', 'options_strategy': 'CASH_SECURED_PUT', 'options_rationale': 'aumenta peso'}
    api._corregir_si_añade_sobreponderada(row, {'portfolio_pct': 16.7, 'peso_techo_pct': 9.0})
    assert row['options_strategy'] == 'HOLD' and 'no añadas' in row['options_rationale']


def test_añadir_con_peso_normal_se_respeta():
    row = {'action': 'AÑADIR', 'options_strategy': 'CASH_SECURED_PUT', 'options_rationale': 'x'}
    api._corregir_si_añade_sobreponderada(row, {'portfolio_pct': 5.0, 'peso_techo_pct': 9.0})
    assert row['options_strategy'] == 'CASH_SECURED_PUT' and row['action'] == 'AÑADIR'


def _rec(estrategia, accion, tipo, strike, expiry='2026-11-13'):
    return {'recommended_strategy': estrategia,
            'primary_contract': {'action': accion, 'type': tipo, 'strike': strike, 'expiry': expiry}}


def test_no_vender_call_por_debajo_del_objetivo():
    motivo = api._validar_contrato(_rec('COVERED_CALL', 'VENDER', 'CALL', 415), EXPIRIES, 628.0, False)
    assert motivo and 'objetivo' in motivo


def test_contrato_inventado_se_descarta():
    assert 'cadena real' in api._validar_contrato(_rec('PROTECTIVE_PUT', 'COMPRAR', 'PUT', 300), EXPIRIES, 628.0, False)


def test_put_de_proteccion_real_vale():
    assert api._validar_contrato(_rec('PROTECTIVE_PUT', 'COMPRAR', 'PUT', 345), EXPIRIES, 628.0, False) is None


def test_sobreponderada_no_admite_put_vendida_ni_leaps():
    assert api._validar_contrato(_rec('CASH_SECURED_PUT', 'VENDER', 'PUT', 345), EXPIRIES, 628.0, True)


def test_hold_sin_contrato_es_valido():
    assert api._validar_contrato({'recommended_strategy': 'HOLD', 'primary_contract': None}, EXPIRIES, 628.0, True) is None


# ── El peso lo decide la casa; la IA, si la tesis sigue viva ─────────────────

def test_la_ia_no_puede_añadir_lo_que_no_es_prioridad():
    p = {'asset_type': 'stock', 'peso_accion': 'MANTENER'}
    assert api._accion_final('AÑADIR', p) == 'MANTENER'


def test_la_ia_si_puede_vender_si_la_tesis_se_rompe():
    assert api._accion_final('VENDER', {'asset_type': 'stock', 'peso_accion': 'AÑADIR'}) == 'VENDER'


def test_el_peso_manda_sobre_la_ia():
    assert api._accion_final('MANTENER', {'asset_type': 'stock', 'peso_accion': 'REDUCIR'}) == 'REDUCIR'


def test_un_fondo_no_se_manda_añadir():
    assert api._accion_final('AÑADIR', {'asset_type': 'stock', 'es_fondo': True}) == 'MANTENER'


def test_pesos_de_cartera_con_la_regla_de_la_lista(monkeypatch):
    """Una Prioridad al 25 % se recorta al techo; un fondo no lleva peso; el objetivo es el nuestro."""
    import numpy as np
    import pandas as pd
    import position_sizer as ps
    idx = pd.bdate_range('2025-11-01', periods=260)
    rng = np.random.default_rng(1)
    precios = pd.DataFrame({'AAA': 100 * np.exp(np.cumsum(rng.normal(0, 0.30 / np.sqrt(252), 260)))}, index=idx)
    monkeypatch.setattr(ps, 'precios_diarios', lambda t: precios)
    enriched = [
        {'ticker': 'AAA', 'asset_type': 'stock', 'es_fondo': False, 'portfolio_pct': 25.0, 'current_price': 100.0},
        {'ticker': 'VOO', 'asset_type': 'stock', 'es_fondo': True, 'portfolio_pct': 75.0, 'current_price': 500.0},
    ]
    casa = {'AAA': {'value_grupo': 'PRIORIDAD', 'objetivo_propio': 130.0}}
    assert api._pesos_de_cartera(enriched, casa) == []
    a, voo = enriched
    assert a['peso_accion'] == 'REDUCIR' and a['peso_recomendado_pct'] == a['peso_techo_pct']
    assert a['upside_propio_pct'] == 30.0
    assert 'peso_accion' not in voo


def test_la_cartera_y_el_aviso_de_venta_usan_el_mismo_objetivo(monkeypatch):
    """Con divergencia ALTA el aviso de venta no tiene objetivo: la cartera tampoco."""
    import pandas as pd
    fund = pd.DataFrame([
        {'ticker': 'SANA', 'current_price': 100.0, 'analyst_upside_pct': 20.0,
         'target_price_dcf_upside_pct': 25.0, 'target_price_pe_upside_pct': 15.0},
        {'ticker': 'CHOCA', 'current_price': 100.0, 'analyst_upside_pct': 60.0,
         'target_price_dcf_upside_pct': -10.0, 'target_price_pe_upside_pct': -5.0},
    ]).set_index('ticker')
    monkeypatch.setattr(api, 'DF_FUND_US', fund)
    monkeypatch.setattr(api, '_load_csv', lambda *a, **k: pd.DataFrame())
    casa = api._casa_para_cartera()
    assert casa['SANA']['objetivo_propio'] == 120.0
    assert 'CHOCA' not in casa
