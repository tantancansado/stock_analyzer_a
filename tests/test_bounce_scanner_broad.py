#!/usr/bin/env python3
"""Tests para bounce_scanner_broad — regresión del bug "0 setups para siempre".

El bug: RSI(2) se medía en la vela de HOY a la vez que se exigía vela verde HOY —
la vela verde resetea el RSI(2), así que la combinación era incumplible
(0 setups en 4.794 ticker-días de backtest de 1 año). El fix mide el oversold
en la vela de AYER. Estos tests construyen un setup sintético de libro
(tendencia alcista → pánico de 3 días → reversión verde con volumen) y verifican
que AHORA pasa los filtros — y que las variantes rotas no.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bounce_scanner_broad as bsb


def _make_bounce_df(green_today=True, panic=True, volume_spike=True) -> pd.DataFrame:
    """260 días: subida suave (sobre SMA200) + 3 días de pánico + reversión hoy."""
    n = 260
    rng = np.random.default_rng(7)
    # Base: tendencia alcista suave 100 → ~130 con ruido leve
    drift = np.linspace(100, 130, n)
    noise = rng.normal(0, 0.3, n)
    close = drift + noise

    # Pánico: días -4..-2 caen fuerte (~-7% acumulado desde el máximo local)
    if panic:
        close[-4] = close[-5] * 0.975
        close[-3] = close[-4] * 0.970
        close[-2] = close[-3] * 0.975
    else:
        close[-4] = close[-5] * 1.001
        close[-3] = close[-4] * 1.001
        close[-2] = close[-3] * 1.001

    # Hoy: reversión verde (o día rojo para el caso negativo)
    close[-1] = close[-2] * (1.012 if green_today else 0.99)

    high = close * 1.008
    low  = close * 0.992
    # El low de hoy testea el mínimo de los últimos 20 días (soporte de ayer)
    low[-1] = min(low[-30:-1].min() * 1.001, close[-1] * 0.985)

    vol = np.full(n, 1_000_000.0)
    if volume_spike:
        vol[-1] = 1_600_000.0

    idx = pd.date_range('2025-06-01', periods=n, freq='B')
    return pd.DataFrame({'Close': close, 'High': high, 'Low': low, 'Volume': vol}, index=idx)


class TestBounceFilters:
    def test_textbook_bounce_passes(self):
        df = _make_bounce_df()
        m = bsb._compute_metrics(df)
        assert m is not None
        assert bsb._passes_filters(m), f'setup de libro debería pasar: {m}'

    def test_eval_ticker_returns_setup(self):
        df = _make_bounce_df()
        setup = bsb._eval_ticker('TEST', df)
        assert setup is not None
        assert setup['setup_type'] == 'BOUNCE_OVERSOLD'
        assert setup['rr'] >= bsb.MIN_RR

    def test_red_day_fails(self):
        # Sin vela verde hoy no hay reversión — debe rechazar
        df = _make_bounce_df(green_today=False)
        m = bsb._compute_metrics(df)
        assert m is None or not bsb._passes_filters(m)

    def test_no_panic_fails(self):
        # Sin pánico previo el RSI(2) de ayer no está en oversold — debe rechazar
        df = _make_bounce_df(panic=False)
        m = bsb._compute_metrics(df)
        assert m is None or not bsb._passes_filters(m)

    def test_no_volume_fails(self):
        df = _make_bounce_df(volume_spike=False)
        m = bsb._compute_metrics(df)
        assert m is None or not bsb._passes_filters(m)

    def test_rsi_measured_on_previous_bar(self):
        # Regresión del bug: r2/r14 deben ser los de AYER, no los de hoy.
        # En el setup de libro, la vela verde de hoy sube el RSI(2) de hoy muy
        # por encima del de ayer — si m['r2'] fuera el de hoy, el filtro fallaría.
        df = _make_bounce_df()
        m = bsb._compute_metrics(df)
        r2_today = float(bsb._rsi(df['Close'], 2).iloc[-1])
        assert m['r2'] < r2_today, 'r2 debe ser el de ayer (pánico), no el de hoy (ya rebotado)'


class TestMeanReversionStockVar:
    def test_detect_oversold_bounce_defines_stock(self):
        # Regresión: la variable `stock` se perdió en un refactor y el NameError
        # silenciado en el gate de market cap rechazaba el 100% de candidatos.
        import inspect
        from mean_reversion_detector import MeanReversionDetector
        src = inspect.getsource(MeanReversionDetector.detect_oversold_bounce)
        uses  = 'stock.fast_info' in src or 'stock.calendar' in src
        defines = 'stock = yf.Ticker(' in src
        assert not uses or defines, (
            'detect_oversold_bounce usa `stock.` sin definir `stock = yf.Ticker(...)` '
            '— el NameError silenciado rechaza todos los candidatos'
        )
