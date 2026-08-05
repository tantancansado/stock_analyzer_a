#!/usr/bin/env python3
"""Tests para ticker_api._build_search_live_snapshot / _build_earnings_expectation_snapshot
— divisa GBp en el buscador de tickers y la cartera real.

Verificado con datos reales el 5-ago-2026: tickers UK (AZN.L en curated_tickers_eu.py)
cotizan en GBp pero epsForward/lastDividendValue/trailingAnnualDividendRate venían
crudos en GBP, sin el x100 de subunidad — el buscador y el endpoint de earnings
mostraban EPS/dividendos ~100x más pequeños que el precio.
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import ticker_api as api

GBP_INFO = {
    "currentPrice": 12100.0,
    "regularMarketPrice": 12100.0,
    "currency": "GBp",
    "financialCurrency": "GBP",
    "epsForward": 8.519137,
    "forwardEps": 8.519137,
    "targetMeanPrice": 15698.697,
    "longName": "AstraZeneca PLC",
    "sector": "Healthcare",
    "freeCashflow": 5_000_000_000,
    "marketCap": 190_000_000_000,
    "sharesOutstanding": 1_500_000_000,
}


def _mock_ticker(info, earnings_estimate=None):
    tk = MagicMock()
    tk.info = info
    tk.fast_info = {}
    tk.earnings_estimate = earnings_estimate if earnings_estimate is not None else pd.DataFrame()
    tk.revenue_estimate = pd.DataFrame()
    tk.earnings_history = None
    tk.calendar = None
    tk.earnings_dates = None
    return tk


class TestSearchLiveSnapshotCurrency:
    def setup_method(self):
        # _build_search_live_snapshot/_build_earnings_expectation_snapshot
        # cachean por ticker — sin limpiar, un test contamina al siguiente.
        api._SEARCH_ENRICH_CACHE.clear()
        api._EARNINGS_SIGNAL_CACHE.clear()

    def test_fcf_yield_uses_normalized_info(self):
        with patch.object(api, "_yf", create=True), \
             patch("yfinance.Ticker", return_value=_mock_ticker(dict(GBP_INFO))):
            snap = api._build_search_live_snapshot("AZN.L")
        assert snap["current_price"] == 12100.0
        # freeCashflow/marketCap misma divisa (GBP ambos, sin subunidad en marketCap
        # de yfinance) -> fcf_yield debe calcularse sin reventar
        assert snap.get("fcf_yield") is not None

    def test_consensus_eps_from_earnings_estimate_gets_subunit_fix(self):
        est_df = pd.DataFrame({"avg": [2.65107]}, index=["0q"])
        with patch.object(api, "_yf", create=True), \
             patch("yfinance.Ticker", return_value=_mock_ticker(dict(GBP_INFO), est_df)):
            snap = api._build_search_live_snapshot("AZN.L")
        # 2.65107 x100 = 265.107, no el crudo
        assert abs(snap["consensus_eps"] - 265.107) < 0.01


class TestEarningsExpectationSnapshotCurrency:
    def setup_method(self):
        api._SEARCH_ENRICH_CACHE.clear()
        api._EARNINGS_SIGNAL_CACHE.clear()

    def test_eps_est_override_gets_subunit_fix(self):
        est_df = pd.DataFrame({"avg": [2.65107]}, index=["0q"])
        with patch.object(api, "_yf", create=True), \
             patch("yfinance.Ticker", return_value=_mock_ticker(dict(GBP_INFO), est_df)):
            snap = api._build_earnings_expectation_snapshot("AZN.L", {}, {})
        assert abs(snap["consensus_eps"] - 265.107) < 0.01
