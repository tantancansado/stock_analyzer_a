#!/usr/bin/env python3
"""Tests para earnings_thesis_generator._build_context — divisa de cotización.

Verificado con datos reales el 5-ago-2026: acciones UK (AZN.L, ULVR.L...)
cotizan en GBp (peniques) pero currentPrice/EPS crudos de yfinance vienen en
escalas distintas antes de normalizar. Sin normalize_info(), el prompt de IA
recibía "Precio actual: 12184 / EPS consenso: 8.52" (AZN.L) — implica PE
~1430x cuando el real es ~14x. También el hardcode "M$" mentía la divisa de
revenue_estimate para cualquier ticker no-USD.
"""
import os
import sys
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import earnings_thesis_generator as etg

GBP_INFO = {
    "currentPrice": 12184.0,
    "currency": "GBp",
    "financialCurrency": "GBP",
    "epsForward": 8.519137,   # crudo, en libras, sin el x100 de subunidad
    "shortName": "AstraZeneca",
    "sector": "Healthcare",
    "fiftyTwoWeekHigh": 13000.0,
    "fiftyTwoWeekLow": 10000.0,
}


def _mock_ticker(info):
    tk = MagicMock()
    tk.info = info
    return tk


class TestBuildContextCurrency:
    def test_subunit_price_and_eps_normalized_consistently(self):
        edate = date.today() + timedelta(days=5)
        with patch.object(etg, "yf") as yf_mod, \
             patch.object(etg, "_next_earnings_date", return_value=edate), \
             patch.object(etg, "_implied_move_pct", return_value=None), \
             patch.object(etg, "_earnings_history", return_value=(None, [])), \
             patch.object(etg, "_fetch_recent_headlines", return_value=[]):
            yf_mod.Ticker.return_value = _mock_ticker(dict(GBP_INFO))
            ctx = etg._build_context("AZN.L", shares=None, avg_price=None)

        assert ctx is not None
        assert ctx["currency"] == "GBp"
        # EPS normalizado (x100) debe quedar en la MISMA escala que el precio,
        # de forma que precio/eps dé un PE plausible (no ~1430x)
        implied_pe = ctx["current_price"] / ctx["expected_eps"]
        assert 10 < implied_pe < 20

    def test_context_carries_currency_for_prompt_labeling(self):
        edate = date.today() + timedelta(days=5)
        with patch.object(etg, "yf") as yf_mod, \
             patch.object(etg, "_next_earnings_date", return_value=edate), \
             patch.object(etg, "_implied_move_pct", return_value=None), \
             patch.object(etg, "_earnings_history", return_value=(None, [])), \
             patch.object(etg, "_fetch_recent_headlines", return_value=[]):
            yf_mod.Ticker.return_value = _mock_ticker(dict(GBP_INFO))
            ctx = etg._build_context("AZN.L", shares=None, avg_price=None)

        prompt = etg._build_prompt(ctx)
        assert "GBp" in prompt
        assert "M$" not in prompt  # no debe mentir la divisa como dólares

    def test_earnings_estimate_quarterly_eps_also_needs_subunit_fix(self):
        # tk.earnings_estimate es una llamada de yfinance APARTE de `info` —
        # normalize_info() no la toca. Real (AZN.L, 5-ago-2026): '0q' avg
        # 2.65107 crudo, sin ×100, sobreescribiendo el epsForward ya normalizado
        # y dejando un implied PE de ~4585x en vez de ~46x (base trimestral).
        edate = date.today() + timedelta(days=5)
        est_df = pd.DataFrame(
            {"avg": [2.65107], "low": [2.46], "high": [2.98]}, index=["0q"]
        )
        with patch.object(etg, "yf") as yf_mod, \
             patch.object(etg, "_next_earnings_date", return_value=edate), \
             patch.object(etg, "_implied_move_pct", return_value=None), \
             patch.object(etg, "_earnings_history", return_value=(None, [])), \
             patch.object(etg, "_fetch_recent_headlines", return_value=[]):
            tk = _mock_ticker(dict(GBP_INFO))
            tk.earnings_estimate = est_df
            yf_mod.Ticker.return_value = tk
            ctx = etg._build_context("AZN.L", shares=None, avg_price=None)

        assert abs(ctx["expected_eps"] - 265.107) < 0.01  # 2.65107 x100, no el crudo
        implied_pe = ctx["current_price"] / ctx["expected_eps"]
        assert 30 < implied_pe < 60  # base trimestral, no anual
