"""
El objetivo puede no existir, y eso tumbó el pipeline entero.

Desde el 16-sep-2026 el precio de salida sale del consenso de analistas y vale
None cuando los modelos propios lo desmienten (ver `_calculate_exit_price`). El
17 por la mañana, el paso «Calculate Entry/Exit Prices [CRITICAL]» falló:

    unsupported format string passed to NoneType.__format__
    TypeError: Column 'risk_reward' has dtype object, cannot use 'nlargest'

Como el paso está marcado [CRITICAL] —sin `continue-on-error`— se llevó por
delante TODO lo que va detrás en `core-scoring`:

    add_entry_exit · owner_earnings · conviction_filter · technical_filter
    generate_insights · portfolio_tracker · entry_verdict_agent · cerebro

Nueve pasos sin correr por un `:.2f`. La app publicó igualmente: lista VALUE
fresca, sin una sola columna de timing, y las señales del día sin registrar en
el tracker.

Por qué no lo cacé al probarlo: verifiqué `_enrich_csv_with_entry_exit` (la
ruta de VALUE) y no `add_entry_exit_prices` (la de MOMENTUM), que es otra
función con su propio formateo y su propio resumen. Dos rutas, probé una.
"""
import pandas as pd
import pytest

from entry_exit_calculator import EntryExitCalculator


@pytest.fixture
def _sin_objetivo():
    """Lo que devuelve el calculador cuando no hay objetivo defendible."""
    calc = EntryExitCalculator()
    hist = pd.DataFrame({
        'open': [100.0] * 60, 'high': [101.0] * 60,
        'low': [99.0] * 60, 'close': [100.0] * 60, 'volume': [1e6] * 60,
    })
    return calc.calculate_entry_exit(
        ticker='TEST', current_price=100.0, hist=hist,
        vcp_analysis={'score': 0, 'pattern_detected': False},
        fundamental_data={},
        # Consenso +18%, pero los dos modelos propios dicen que está cara:
        # no hay objetivo en el que apoyarse.
        validation={'price_vs_ath': -10.0, 'target_price_analyst': 118.0,
                    'target_price_dcf': 60.0, 'target_price_pe': 55.0},
    )


def test_el_calculador_devuelve_none_sin_reventar(_sin_objetivo):
    assert _sin_objetivo['exit_price'] is None
    assert _sin_objetivo['risk_reward_ratio'] is None
    assert _sin_objetivo['exit_range_low'] is None
    assert _sin_objetivo['meets_criteria'] is False
    # Lo que SÍ se puede calcular sigue estando
    assert _sin_objetivo['entry_price'] > 0
    assert _sin_objetivo['stop_loss'] > 0
    assert _sin_objetivo['risk_pct'] > 0


def test_la_ficha_se_puede_imprimir(_sin_objetivo):
    """El fallo literal: un `:.2f` sobre None."""
    e = _sin_objetivo
    salida, rr = e['exit_price'], e['risk_reward_ratio']
    destino = (f"Target ${salida:.2f} (R/R: {rr:.1f}:1)"
               if salida is not None and rr is not None else "sin objetivo por valoración")
    linea = f"${e['current_price']:.2f} → Entry: ${e['entry_price']:.2f} | {destino}"
    assert 'sin objetivo' in linea


def test_el_resumen_aguanta_una_columna_con_huecos():
    """La segunda mitad: con Nones la columna llega como `object` y `nlargest`
    levanta un TypeError."""
    # El caso real del 17-sep: la lista MOMENTUM tenía 2 tickers y NINGUNO
    # consiguió objetivo, así que la columna entera llegó a None → `object`.
    filas = [{'ticker': t, 'risk_reward': None, 'current_price': 1.0,
              'entry_price': 1.0, 'exit_price': None, 'entry_timing': 'x'}
             for t in ('VRSN', 'FAST')]
    df = pd.DataFrame(filas)
    assert df['risk_reward'].dtype == object, 'así llega antes de convertir'
    with pytest.raises(TypeError):
        df.nlargest(2, 'risk_reward')

    df['risk_reward'] = pd.to_numeric(df['risk_reward'], errors='coerce')
    con = df[df['risk_reward'].notna()]
    assert len(con) == 0, 'y entonces no se imprime un top de nada'

    # Y con la columna mixta, que es lo normal, se ordena sin romperse.
    mixto = pd.DataFrame([{'ticker': 'A', 'risk_reward': 3.2},
                          {'ticker': 'B', 'risk_reward': None},
                          {'ticker': 'C', 'risk_reward': 1.4}])
    mixto['risk_reward'] = pd.to_numeric(mixto['risk_reward'], errors='coerce')
    assert len(mixto[mixto['risk_reward'].notna()].nlargest(2, 'risk_reward')) == 2


def test_las_dos_rutas_estan_protegidas():
    """Probé una de las dos funciones y por eso se coló. Ahora se comprueban
    las dos: la de VALUE (`_enrich_csv_with_entry_exit`) y la de MOMENTUM
    (`add_entry_exit_prices`)."""
    import inspect

    import add_entry_exit_to_opportunities as m
    for fn in (m.add_entry_exit_prices, m._enrich_csv_with_entry_exit):
        fuente = inspect.getsource(fn)
        assert 'sin objetivo por valoración' in fuente, \
            f'{fn.__name__} no contempla que no haya objetivo'
