"""Regression tests for market_regime_detector.

Guards the bug where rate-limited / partial yfinance data produced NaN prices,
every `price > ma` check silently became False, and the detector fabricated a
CORRECTION verdict that aborted the whole pipeline with exit code 1.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import market_regime_detector as mrd


def _detector():
    return mrd.MarketRegimeDetector()


def _nan_history(rows=260):
    """A non-empty frame whose Close column is all NaN (rate-limit shape)."""
    return pd.DataFrame({'Close': [np.nan] * rows})


def _flat_history(price=100.0, rows=260):
    return pd.DataFrame({'Close': [price] * rows})


class TestNaNDoesNotFakeCorrection:
    def test_nan_prices_return_error_not_correction(self, monkeypatch):
        d = _detector()
        monkeypatch.setattr(d, '_get_historical_data', lambda symbol: _nan_history())
        result = d._analyze_index('SPY', 'S&P 500')
        assert result['status'] == 'ERROR', \
            "NaN data must yield ERROR, never a fabricated CORRECTION"

    def test_empty_history_returns_error(self, monkeypatch):
        d = _detector()
        monkeypatch.setattr(d, '_get_historical_data', lambda symbol: pd.DataFrame())
        assert d._analyze_index('SPY', 'S&P 500')['status'] == 'ERROR'

    def test_valid_data_still_scores(self, monkeypatch):
        d = _detector()
        monkeypatch.setattr(d, '_get_historical_data', lambda symbol: _flat_history())
        result = d._analyze_index('SPY', 'S&P 500')
        assert result['status'] != 'ERROR'
        assert 'current_price' in result


class TestRegimeNeverAbortsPipeline:
    def test_both_indices_error_gives_unknown_not_correction(self, monkeypatch):
        d = _detector()
        monkeypatch.setattr(d, '_get_historical_data', lambda symbol: _nan_history())
        regime = d.detect_regime()
        assert regime['regime'] == 'UNKNOWN', \
            "Missing data for both indices must be UNKNOWN, not a fake CORRECTION"
        assert regime['recommendation'] != 'AVOID'

    def test_main_returns_zero_even_when_avoid(self, monkeypatch):
        # Force an AVOID verdict; main() must still exit 0 (informational step).
        monkeypatch.setattr(
            mrd.MarketRegimeDetector, 'detect_regime',
            lambda self: {'regime': 'CORRECTION', 'recommendation': 'AVOID',
                          'confidence': 'HIGH', 'explanation': 'test'},
        )
        assert mrd.main() == 0, "Regime detector must never abort the pipeline"
