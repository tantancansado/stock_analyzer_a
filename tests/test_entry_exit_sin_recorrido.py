"""Un objetivo por debajo de la entrada no se publica como salida."""
import pandas as pd

from entry_exit_calculator import EntryExitCalculator


def test_cerca_de_maximos_sin_recorrido_no_hay_salida():
    # CVX 27-oct-2026: precio 232,01, a un 0,9% de máximos, objetivo 232,50
    idx = pd.date_range('2026-01-01', periods=60, freq='B')
    hist = pd.DataFrame({'high': [234.0] * 60, 'low': [225.0] * 60, 'close': [232.0] * 60}, index=idx)
    r = EntryExitCalculator().calculate_entry_exit(
        ticker='CVX', current_price=232.01, hist=hist,
        vcp_analysis={'pattern_detected': False}, fundamental_data={},
        validation={'price_vs_ath': -0.9, 'target_price_analyst': 232.5})
    assert r['exit_price'] is None and r['risk_reward_ratio'] is None


def test_con_recorrido_la_salida_sigue():
    idx = pd.date_range('2026-01-01', periods=60, freq='B')
    hist = pd.DataFrame({'high': [110.0] * 60, 'low': [90.0] * 60, 'close': [100.0] * 60}, index=idx)
    r = EntryExitCalculator().calculate_entry_exit(
        ticker='X', current_price=100.0, hist=hist,
        vcp_analysis={'pattern_detected': False}, fundamental_data={},
        validation={'price_vs_ath': -20, 'target_price_analyst': 120.0})
    assert r['exit_price'] == 120.0 and r['exit_price'] > r['entry_price']
