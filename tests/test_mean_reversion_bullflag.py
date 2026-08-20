"""Regresión del bull flag pullback (mean_reversion_detector).

Bug encontrado el 5-jul-2026: lookback_days=180 (~124 sesiones) hacía que la
SMA200 cayera SIEMPRE a la SMA50, así que el criterio de tendencia mayor —lo
que DEFINE un bull flag— nunca se evaluaba: trend salía siempre 'Bearish' y
el RSI estaba hardcodeado a None. Estos tests fijan que no vuelva a pasar.
"""
import inspect
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mean_reversion_detector as mrd


def test_lookback_covers_sma200():
    d = mrd.MeanReversionDetector()
    # 300 días de calendario ≈ 205 sesiones; hace falta >=200 para la SMA200
    assert d.lookback_days >= 290


def test_bullflag_no_longer_hardcodes_rsi_none():
    src = inspect.getsource(mrd.MeanReversionDetector.detect_bull_flag_pullback)
    # el rsi ya NO se emite como None fijo
    assert "'rsi': None" not in src
    assert "'rsi': current_rsi_bf" in src
    # y exige 200 sesiones reales en vez de inventar una SMA200
    assert "len(hist) < 200" in src
    assert "else sma_50" not in src  # el fallback falso desapareció


def test_bullflag_computes_rsi_tier():
    src = inspect.getsource(mrd.MeanReversionDetector.detect_bull_flag_pullback)
    assert "calculate_rsi" in src
    assert "rsi_tier_bf" in src


class TestTargetNuncaPorDebajoDelPrecio:
    """Una señal de rebote con el target por debajo del precio es basura.

    El 20-ago-2026 llegaron a producción DVA (precio 177,27 → target 156,76,
    -11,6%) y UNH (388,61 → 347,91, -10,5%): "oportunidades" que pedían
    comprar caro para vender barato. La causa era
    `min(current_price * 1.07, resistance)` sin comprobar que la resistencia
    estuviera por encima del precio.

    Y detrás había algo peor: el RSI marcaba sobreventa (11,9 en DVA) mientras
    el precio estaba un 22-37% POR ENCIMA del soporte. No hay rebote que hacer
    desde ahí — el setup entero era falso, no solo el número.
    """

    def test_el_calculo_de_min_es_el_que_fallaba(self):
        """Reproduce la aritmética exacta que se coló en producción."""
        precio, resistencia = 177.27, 156.76
        target_viejo = round(min(precio * 1.07, resistencia), 2)
        assert target_viejo < precio, 'así salía el target negativo'
        assert round((target_viejo / precio - 1) * 100, 1) == -11.6

    def test_el_detector_descarta_si_la_resistencia_esta_debajo(self):
        from pathlib import Path
        import mean_reversion_detector as mrd
        src = Path(mrd.__file__).read_text()
        # el guard tiene que estar ANTES de calcular el target, en ambos setups
        assert 'if resistance <= current_price:' in src
        assert 'if high_60d <= current_price:' in src

    def test_ninguna_señal_publicada_pide_comprar_caro_para_vender_barato(self):
        """Sobre el CSV real: es la comprobación que habría cazado el fallo."""
        from pathlib import Path
        import pandas as pd
        import pytest
        f = Path(__file__).parent.parent / 'docs' / 'mean_reversion_opportunities.csv'
        if not f.exists():
            pytest.skip('sin CSV de mean reversion')
        d = pd.read_csv(f)
        if d.empty:
            pytest.skip('sin señales hoy')
        precio = pd.to_numeric(d['current_price'], errors='coerce')
        for col in ('target', 'bounce_target'):
            if col not in d.columns:
                continue
            t = pd.to_numeric(d[col], errors='coerce')
            malas = d.loc[t.notna() & precio.notna() & (t <= precio), 'ticker'].tolist()
            assert not malas, f'{col} por debajo del precio en: {malas}'
