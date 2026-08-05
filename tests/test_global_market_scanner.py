#!/usr/bin/env python3
"""Tests para global_market_scanner._score_ticker — divisa de estados
financieros vs cotización.

Verificado con datos reales el 5-ago-2026: casi todo Hong Kong con
subyacente chino tiene currency=HKD pero financialCurrency=CNY/USD (Tencent,
Alibaba, CNOOC, PetroChina, HSBC, AIA). freeCashflow se dividía directamente
entre marketCap sin convertir — mismo bug que ATLKY/ASAZY en la lista VALUE.
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import global_market_scanner as gms

BASE_INFO = {
    "currentPrice": 100.0,
    "fiftyTwoWeekHigh": 120.0,
    "longName": "Test Co",
    "sector": "Communication Services",
    "currency": "HKD",
    "financialCurrency": "CNY",
    "marketCap": 1_000_000_000,
    "returnOnEquity": 0.15,
    "trailingPE": 10.0,
    "forwardPE": 9.0,
    "profitMargins": 0.15,
    "revenueGrowth": 0.05,
    "debtToEquity": 50.0,
    "dividendYield": 0.02,
    "payoutRatio": 0.3,
    "freeCashflow": 70_000_000,  # 7.0% sin convertir, 8.12% convertido a HKD
    "targetMeanPrice": 110.0,
    "numberOfAnalystOpinions": 10,
    "sharesOutstanding": 10_000_000,
}


def _mock_ticker(info):
    tk = MagicMock()
    tk.info = info
    return tk


class TestScoreTickerCurrencyMismatch:
    def test_fcf_yield_converted_when_fx_available(self):
        with patch.object(gms.yf, "Ticker", return_value=_mock_ticker(dict(BASE_INFO))), \
             patch("currency_normalizer.get_fx_rate", return_value=1.16):
            r = gms._score_ticker("0700.HK", "HongKong")
        assert r is not None
        # 70M CNY x1.16 / 1000M HKD = 8.12% -> cruza a la banda >=8% (10 pts)
        assert r["fcf_yield_pct"] == 8.1

    def test_fcf_yield_none_when_fx_unavailable(self):
        with patch.object(gms.yf, "Ticker", return_value=_mock_ticker(dict(BASE_INFO))), \
             patch("currency_normalizer.get_fx_rate", return_value=None):
            r = gms._score_ticker("0700.HK", "HongKong")
        assert r is not None
        assert r["fcf_yield_pct"] is None  # mejor sin dato que dato mal convertido

    def test_no_conversion_when_currencies_match(self):
        info = dict(BASE_INFO)
        info["financialCurrency"] = "HKD"
        with patch.object(gms.yf, "Ticker", return_value=_mock_ticker(info)), \
             patch("currency_normalizer.get_fx_rate") as fx:
            r = gms._score_ticker("0388.HK", "HongKong")
        fx.assert_not_called()
        assert r["fcf_yield_pct"] == 7.0
