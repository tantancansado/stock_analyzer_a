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
