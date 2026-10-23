"""La recomendación de opciones respeta el tamaño de la posición y el precio objetivo."""
import ticker_api as api

EXPIRIES = [{'expiry': '2026-11-13', 'days_out': 21,
             'covered_calls': [{'strike': 415.0}, {'strike': 430.0}],
             'protective_puts': [{'strike': 345.0}]}]


def test_sobreponderada_con_la_misma_regla_que_la_ficha():
    assert api._sobreponderada({'portfolio_pct': 16.7, 'optimal_size_pct': 8.3})
    assert not api._sobreponderada({'portfolio_pct': 10.0, 'optimal_size_pct': 8.3})
    assert not api._sobreponderada({'portfolio_pct': 16.7, 'optimal_size_pct': None})


def test_no_se_publica_vender_puts_para_añadir_si_ya_sobra():
    row = {'action': 'MANTENER', 'options_strategy': 'CASH_SECURED_PUT', 'options_rationale': 'aumenta peso'}
    api._corregir_si_añade_sobreponderada(row, {'portfolio_pct': 16.7, 'optimal_size_pct': 8.3})
    assert row['options_strategy'] == 'HOLD' and 'no añadas' in row['options_rationale']


def test_añadir_con_peso_normal_se_respeta():
    row = {'action': 'AÑADIR', 'options_strategy': 'CASH_SECURED_PUT', 'options_rationale': 'x'}
    api._corregir_si_añade_sobreponderada(row, {'portfolio_pct': 5.0, 'optimal_size_pct': 8.3})
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
