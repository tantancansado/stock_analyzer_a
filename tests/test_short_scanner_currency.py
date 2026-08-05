#!/usr/bin/env python3
"""Tests para short_scanner._score_ticker — divisa de estados financieros
vs cotización.

Verificado con datos reales el 5-ago-2026: BABA/JD/PDD/BIDU/LI cotizan en
USD (ADR) pero reportan en CNY, STLA en EUR. fcf_yield_pct dividía
freeCashflow (financialCurrency) entre marketCap (currency) sin convertir —
BABA daba -14,1% (real -2,1%), cruzando el umbral fund_score +10/+6.
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import short_scanner as ss

BASE_INFO = {
    "currentPrice": 100.0,
    "regularMarketPrice": 100.0,
    "currency": "USD",
    "financialCurrency": "CNY",
    "marketCap": 10_000_000_000,
    "shortPercentOfFloat": 3.0,
    "revenueGrowth": 0.02,
    "freeCashflow": -1_000_000_000,  # -10% sin convertir
    "returnOnEquity": 0.05,
    "debtToEquity": 50.0,
    "operatingMargins": 0.10,
    "profitMargins": 0.05,
    "targetMeanPrice": 105.0,
    "longName": "Test ADR Co",
    "sector": "Consumer Cyclical",
}


def _fake_hist(n=300):
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    close = pd.Series(np.linspace(120, 100, n), index=idx)
    return pd.DataFrame({"Close": close})


def _mock_ticker(info):
    tk = MagicMock()
    tk.info = info
    tk.history.return_value = _fake_hist()
    tk.financials = pd.DataFrame()
    return tk


class TestScoreTickerCurrencyMismatch:
    def test_fcf_yield_converted_when_fx_available(self):
        with patch.object(ss.yf, "Ticker", return_value=_mock_ticker(dict(BASE_INFO))), \
             patch("currency_normalizer.get_fx_rate", return_value=0.148):
            r = ss._score_ticker("BABATEST")
        assert r is not None
        # -1B CNY x0.148 / 10B USD = -1.48% -> banda "<0" (no "<-5")
        assert r["fcf_yield_pct"] == -1.5
        assert r["fund_score"] < 35  # no debe llevarse el bucket -5 completo

    def test_fcf_yield_none_when_fx_unavailable(self):
        with patch.object(ss.yf, "Ticker", return_value=_mock_ticker(dict(BASE_INFO))), \
             patch("currency_normalizer.get_fx_rate", return_value=None):
            r = ss._score_ticker("BABATEST")
        assert r is not None
        assert r["fcf_yield_pct"] is None

    def test_no_conversion_when_currencies_match(self):
        info = dict(BASE_INFO)
        info["financialCurrency"] = "USD"
        with patch.object(ss.yf, "Ticker", return_value=_mock_ticker(info)), \
             patch("currency_normalizer.get_fx_rate") as fx:
            r = ss._score_ticker("USTEST")
        fx.assert_not_called()
        assert r["fcf_yield_pct"] == -10.0
