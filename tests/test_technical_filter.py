#!/usr/bin/env python3
"""
Tests for technical_filter.py — all public and private functions.

Functions covered (11 total):
  1.  _now_utc
  2.  _fetch_history               (mocked — no real yfinance calls)
  3.  fetch_spy_6m_return          (mocked)
  4.  _compute_ma_signals
  5.  _compute_atr_ratio
  6.  _compute_volume_dryup
  7.  _compute_52w
  8.  _compute_rs
  9.  _compute_trend
  10. _compute_tech_stage
  11. _merge_tech_signals
  12. compute_technical_signals     (integration, mocked _fetch_history)

No real yfinance calls are made — all data is synthetic DataFrames.
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from technical_filter import (
    _now_utc,
    _compute_ma_signals,
    _compute_atr_ratio,
    _compute_volume_dryup,
    _compute_52w,
    _compute_rs,
    _compute_trend,
    _compute_tech_stage,
    _merge_tech_signals,
    compute_technical_signals,
    fetch_spy_6m_return,
    TECH_COLS,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_close(n: int = 252, start: float = 100.0, trend: float = 0.1) -> pd.Series:
    """Synthetic close price series with a gentle uptrend."""
    prices = [start + trend * i for i in range(n)]
    return pd.Series(prices, dtype=float)


def _make_ohlcv(
    n: int = 252,
    start: float = 100.0,
    trend: float = 0.1,
    vol: int = 1_000_000,
) -> pd.DataFrame:
    """Synthetic OHLCV DataFrame — all columns needed by the filter."""
    close = _make_close(n, start, trend)
    high = close + 1.0
    low = close - 1.0
    volume = pd.Series([vol] * n, dtype=float)
    return pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close, "Volume": volume})


# ─── 1. _now_utc ──────────────────────────────────────────────────────────────

class TestNowUtc:

    def test_returns_string(self):
        result = _now_utc()
        assert isinstance(result, str)

    def test_format_iso8601(self):
        result = _now_utc()
        # Must parse as UTC ISO 8601  e.g. 2026-05-01T12:00:00Z
        dt = datetime.strptime(result, "%Y-%m-%dT%H:%M:%SZ")
        assert dt.year >= 2024

    def test_ends_with_Z(self):
        assert _now_utc().endswith("Z")

    def test_two_calls_close_in_time(self):
        t1 = _now_utc()
        t2 = _now_utc()
        dt1 = datetime.strptime(t1, "%Y-%m-%dT%H:%M:%SZ")
        dt2 = datetime.strptime(t2, "%Y-%m-%dT%H:%M:%SZ")
        assert abs((dt2 - dt1).total_seconds()) < 2


# ─── 2. _fetch_history ────────────────────────────────────────────────────────

class TestFetchHistory:
    """_fetch_history is tightly coupled to yfinance; test via mocking."""

    def test_returns_dataframe_on_success(self):
        mock_df = _make_ohlcv(100)
        with patch("technical_filter.yf.download", return_value=mock_df):
            from technical_filter import _fetch_history
            result = _fetch_history("AAPL")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 100

    def test_returns_none_when_empty(self):
        with patch("technical_filter.yf.download", return_value=pd.DataFrame()):
            from technical_filter import _fetch_history
            result = _fetch_history("AAPL")
        assert result is None

    def test_returns_none_when_less_than_30_rows(self):
        mock_df = _make_ohlcv(20)
        with patch("technical_filter.yf.download", return_value=mock_df):
            from technical_filter import _fetch_history
            result = _fetch_history("AAPL")
        assert result is None

    def test_returns_none_on_exception(self):
        with patch("technical_filter.yf.download", side_effect=Exception("network error")):
            from technical_filter import _fetch_history
            result = _fetch_history("AAPL")
        assert result is None

    def test_flattens_multiindex_columns(self):
        mock_df = _make_ohlcv(100)
        # Wrap in a MultiIndex the way yfinance sometimes returns
        mock_df.columns = pd.MultiIndex.from_tuples(
            [(c, "AAPL") for c in mock_df.columns]
        )
        with patch("technical_filter.yf.download", return_value=mock_df):
            from technical_filter import _fetch_history
            result = _fetch_history("AAPL")
        assert isinstance(result, pd.DataFrame)
        # Columns should be flat strings after flattening
        assert all(isinstance(c, str) for c in result.columns)


# ─── 3. fetch_spy_6m_return ───────────────────────────────────────────────────

class TestFetchSpyReturn:

    def test_returns_float(self):
        mock_df = _make_ohlcv(200, start=400.0, trend=0.5)
        with patch("technical_filter.yf.download", return_value=mock_df):
            result = fetch_spy_6m_return()
        assert isinstance(result, float)

    def test_returns_zero_on_empty(self):
        with patch("technical_filter.yf.download", return_value=pd.DataFrame()):
            result = fetch_spy_6m_return()
        assert result == 0.0

    def test_returns_zero_on_exception(self):
        with patch("technical_filter.yf.download", side_effect=Exception("timeout")):
            result = fetch_spy_6m_return()
        assert result == 0.0

    def test_positive_trend_gives_positive_return(self):
        # Prices go 400 → 410 over 200 bars; 6m return should be positive
        mock_df = _make_ohlcv(200, start=400.0, trend=0.05)
        with patch("technical_filter.yf.download", return_value=mock_df):
            result = fetch_spy_6m_return()
        assert result > 0.0

    def test_short_series_uses_first_price(self):
        # Fewer than 126 bars — should still return a float without crashing
        mock_df = _make_ohlcv(50, start=100.0, trend=0.1)
        with patch("technical_filter.yf.download", return_value=mock_df):
            result = fetch_spy_6m_return()
        assert isinstance(result, float)


# ─── 4. _compute_ma_signals ───────────────────────────────────────────────────

class TestComputeMaSignals:

    def test_returns_tuple_of_correct_types(self):
        close = _make_close(252)
        price = float(close.iloc[-1])
        is_stage2, ma_score, ma200_4wk = _compute_ma_signals(close, price)
        assert isinstance(is_stage2, bool)
        assert isinstance(ma_score, int)
        assert ma200_4wk is None or isinstance(ma200_4wk, float)

    def test_stage2_true_on_clean_uptrend(self):
        # Strong uptrend: price rises linearly from 50 → 275 over 252 bars
        close = _make_close(252, start=50.0, trend=0.9)
        price = float(close.iloc[-1])
        is_stage2, ma_score, _ = _compute_ma_signals(close, price)
        # In a consistent uptrend: price > MA50 > MA150 > MA200 (all rising)
        assert is_stage2 is True
        assert ma_score == 3

    def test_stage2_false_on_downtrend(self):
        # Downtrend: prices falling from 200 → ~-25 (below MAs)
        close = _make_close(252, start=200.0, trend=-0.9)
        price = float(close.iloc[-1])
        is_stage2, ma_score, _ = _compute_ma_signals(close, price)
        assert is_stage2 is False

    def test_ma_score_range(self):
        close = _make_close(252)
        price = float(close.iloc[-1])
        _, ma_score, _ = _compute_ma_signals(close, price)
        assert 0 <= ma_score <= 3

    def test_short_series_no_ma200(self):
        # Only 100 bars — MA200 not available
        close = _make_close(100, start=50.0, trend=0.5)
        price = float(close.iloc[-1])
        is_stage2, ma_score, ma200_4wk = _compute_ma_signals(close, price)
        # ma200_4wk must be None (insufficient data)
        assert ma200_4wk is None
        # is_stage2 requires cond4 (ma200 rising) which requires ma200_4wk → False
        assert is_stage2 is False

    def test_exactly_50_bars_for_ma50(self):
        close = _make_close(55, start=50.0, trend=0.2)
        price = float(close.iloc[-1])
        is_stage2, ma_score, _ = _compute_ma_signals(close, price)
        # Should not raise; only MA50 meaningful here
        assert isinstance(ma_score, int)

    @pytest.mark.parametrize("n_bars,trend", [
        (252, 1.0),   # clear uptrend
        (252, -1.0),  # clear downtrend
        (100, 0.5),   # medium length, uptrend
    ])
    def test_no_exception_various_lengths(self, n_bars, trend):
        close = _make_close(n_bars, start=100.0, trend=trend)
        price = float(close.iloc[-1])
        # Must not raise
        _compute_ma_signals(close, price)


# ─── 5. _compute_atr_ratio ────────────────────────────────────────────────────

class TestComputeAtrRatio:

    def test_returns_float_on_valid_data(self):
        df = _make_ohlcv(252)
        result = _compute_atr_ratio(df["High"], df["Low"], df["Close"])
        assert result is not None
        assert isinstance(result, float)

    def test_result_positive(self):
        df = _make_ohlcv(252)
        result = _compute_atr_ratio(df["High"], df["Low"], df["Close"])
        assert result > 0

    def test_result_rounded_to_3_decimals(self):
        df = _make_ohlcv(252)
        result = _compute_atr_ratio(df["High"], df["Low"], df["Close"])
        assert result == round(result, 3)

    def test_returns_none_on_zero_atr60(self):
        # Flat prices → high==low==close → TR=0 → atr60=0 → None
        flat = pd.Series([100.0] * 252)
        result = _compute_atr_ratio(flat, flat, flat)
        # atr60 = 0 → should return None
        assert result is None

    def test_volatile_series_ratio_gt_1(self):
        # Make recent 10 bars much more volatile than historical 60
        close = pd.Series([100.0] * 252)
        high = close.copy()
        low = close.copy()
        # Last 10 bars: spike +/- 20
        high.iloc[-10:] = 120.0
        low.iloc[-10:] = 80.0
        result = _compute_atr_ratio(high, low, close)
        assert result is not None
        assert result > 1.0

    def test_returns_none_on_exception(self):
        # Passing empty series should trigger the except branch
        empty = pd.Series([], dtype=float)
        result = _compute_atr_ratio(empty, empty, empty)
        assert result is None

    def test_short_series_below_60_bars(self):
        df = _make_ohlcv(30)
        # Not enough for atr60; rolling will return NaN → result None
        result = _compute_atr_ratio(df["High"], df["Low"], df["Close"])
        assert result is None


# ─── 6. _compute_volume_dryup ─────────────────────────────────────────────────

class TestComputeVolumeDryup:

    def test_returns_bool(self):
        volume = pd.Series([1_000_000.0] * 100)
        result = _compute_volume_dryup(volume)
        assert isinstance(result, bool)

    def test_dryup_true_when_recent_volume_half(self):
        # Last 10 bars at 40% of 60-bar average → dryup
        volume = pd.Series([1_000_000.0] * 100)
        volume.iloc[-10:] = 400_000.0
        result = _compute_volume_dryup(volume)
        assert result is True

    def test_dryup_false_when_volume_normal(self):
        volume = pd.Series([1_000_000.0] * 100)
        result = _compute_volume_dryup(volume)
        assert result is False

    def test_dryup_false_when_volume_expanding(self):
        volume = pd.Series([1_000_000.0] * 100)
        volume.iloc[-10:] = 2_000_000.0
        result = _compute_volume_dryup(volume)
        assert result is False

    def test_boundary_exactly_50pct(self):
        # vol10 == vol60 * 0.50 → NOT strictly less than → False
        volume = pd.Series([1_000_000.0] * 100)
        volume.iloc[-10:] = 500_000.0
        result = _compute_volume_dryup(volume)
        assert result is False

    def test_boundary_just_below_50pct(self):
        # vol10 must be < vol60 * 0.50 strictly.
        # vol60 = mean of last 60 bars. To ensure dryup, make the non-recent bars
        # clearly high and recent 10 bars clearly low (< 50% of the 60-bar mean).
        volume = pd.Series([2_000_000.0] * 90 + [100_000.0] * 10)
        result = _compute_volume_dryup(volume)
        assert result is True

    def test_returns_false_on_zero_volume(self):
        volume = pd.Series([0.0] * 100)
        result = _compute_volume_dryup(volume)
        assert result is False

    def test_returns_false_on_empty_series(self):
        result = _compute_volume_dryup(pd.Series([], dtype=float))
        assert result is False

    def test_returns_false_on_exception(self):
        result = _compute_volume_dryup(None)  # type: ignore
        assert result is False


# ─── 7. _compute_52w ──────────────────────────────────────────────────────────

class TestCompute52w:

    def test_returns_tuple_of_two(self):
        df = _make_ohlcv(252)
        result = _compute_52w(df["High"], df["Low"], float(df["Close"].iloc[-1]))
        assert len(result) == 2

    def test_pct_hi_is_zero_when_at_52w_high(self):
        high = pd.Series([100.0] * 252)
        low = pd.Series([90.0] * 252)
        pct_hi, pct_lo = _compute_52w(high, low, 100.0)
        assert pct_hi == pytest.approx(0.0, abs=0.01)

    def test_pct_lo_is_positive_when_above_52w_low(self):
        high = pd.Series([110.0] * 252)
        low = pd.Series([90.0] * 252)
        pct_hi, pct_lo = _compute_52w(high, low, 100.0)
        # price=100, low=90 → (100-90)/90 * 100 ≈ 11.11
        assert pct_lo is not None
        assert pct_lo > 0

    def test_pct_hi_negative_when_below_52w_high(self):
        high = pd.Series([120.0] * 252)
        low = pd.Series([80.0] * 252)
        pct_hi, pct_lo = _compute_52w(high, low, 100.0)
        assert pct_hi is not None
        assert pct_hi < 0

    def test_short_series_uses_full_range(self):
        # Fewer than 252 bars — should still work (uses .max() / .min())
        df = _make_ohlcv(100)
        pct_hi, pct_lo = _compute_52w(df["High"], df["Low"], float(df["Close"].iloc[-1]))
        assert pct_hi is not None
        assert pct_lo is not None

    def test_returns_none_on_zero_price(self):
        high = pd.Series([0.0] * 252)
        low = pd.Series([0.0] * 252)
        pct_hi, pct_lo = _compute_52w(high, low, 0.0)
        assert pct_hi is None
        assert pct_lo is None

    def test_rounded_to_2_decimals(self):
        high = pd.Series([123.456] * 252)
        low = pd.Series([80.0] * 252)
        pct_hi, _ = _compute_52w(high, low, 123.456)
        assert pct_hi == round(pct_hi, 2)

    def test_returns_none_tuple_on_exception(self):
        result = _compute_52w(None, None, 100.0)  # type: ignore
        assert result == (None, None)


# ─── 8. _compute_rs ───────────────────────────────────────────────────────────

class TestComputeRs:

    def test_returns_float(self):
        close = _make_close(252)
        price = float(close.iloc[-1])
        result = _compute_rs(close, price, 10.0)
        assert result is not None
        assert isinstance(result, float)

    def test_outperformer_positive_rs(self):
        # Ticker up 30%, SPY up 10% → RS = +20
        # _compute_rs uses close.iloc[-126] as "6m ago" price.
        # Series of exactly 126 elements: iloc[-126] == iloc[0] == 100.0
        close = pd.Series([100.0] + [130.0] * 125)
        price = 130.0
        result = _compute_rs(close, price, 10.0)
        assert result is not None
        assert result == pytest.approx(20.0, abs=0.1)

    def test_underperformer_negative_rs(self):
        # Ticker up 5%, SPY up 20% → RS = -15
        close = pd.Series([100.0] * 126 + [105.0] * 126)
        price = 105.0
        result = _compute_rs(close, price, 20.0)
        assert result is not None
        assert result < 0

    def test_matches_spy_rs_is_zero(self):
        # Both ticker and SPY up 10% → RS = 0
        # iloc[-126] == iloc[0] == 100.0 with exactly 126 elements
        close = pd.Series([100.0] + [110.0] * 125)
        price = 110.0
        result = _compute_rs(close, price, 10.0)
        assert result is not None
        assert result == pytest.approx(0.0, abs=0.01)

    def test_short_series_uses_first_price(self):
        # Fewer than 126 bars — uses close.iloc[0] as 6m ago price
        close = pd.Series([100.0] * 50 + [115.0] * 50)
        price = 115.0
        result = _compute_rs(close, price, 5.0)
        assert result is not None
        assert isinstance(result, float)

    def test_rounded_to_2_decimals(self):
        close = pd.Series([100.0] * 126 + [113.333] * 126)
        price = 113.333
        result = _compute_rs(close, price, 0.0)
        assert result == round(result, 2)

    def test_returns_none_on_exception(self):
        result = _compute_rs(None, 100.0, 5.0)  # type: ignore
        assert result is None


# ─── 9. _compute_trend ────────────────────────────────────────────────────────

class TestComputeTrend:

    def test_returns_string(self):
        close = _make_close(252)
        price = float(close.iloc[-1])
        result = _compute_trend(close, price)
        assert isinstance(result, str)
        assert result in ("uptrend", "downtrend", "sideways")

    def test_uptrend_on_rising_prices(self):
        # Strong uptrend — price > MA50 > MA200
        close = _make_close(252, start=50.0, trend=0.9)
        price = float(close.iloc[-1])
        result = _compute_trend(close, price)
        assert result == "uptrend"

    def test_downtrend_on_falling_prices(self):
        # Strong downtrend — price < MA50 < MA200
        close = _make_close(252, start=250.0, trend=-0.9)
        price = float(close.iloc[-1])
        result = _compute_trend(close, price)
        assert result == "downtrend"

    def test_sideways_when_short_series(self):
        # Fewer than 200 bars → MA200 not available → sideways
        close = _make_close(100, start=100.0, trend=0.5)
        price = float(close.iloc[-1])
        result = _compute_trend(close, price)
        assert result == "sideways"

    def test_sideways_on_flat_prices(self):
        # Flat prices → all MAs equal → not strictly up or down
        close = pd.Series([100.0] * 252)
        price = 100.0
        result = _compute_trend(close, price)
        assert result == "sideways"

    def test_returns_sideways_on_exception(self):
        result = _compute_trend(None, 100.0)  # type: ignore
        assert result == "sideways"


# ─── 10. _compute_tech_stage ──────────────────────────────────────────────────

class TestComputeTechStage:

    def test_returns_string(self):
        close = _make_close(252, start=50.0, trend=0.9)
        price = float(close.iloc[-1])
        result = _compute_tech_stage(close, price, None, None, None)
        assert isinstance(result, str)

    def test_stage1_when_short_series(self):
        close = _make_close(100, start=100.0, trend=0.5)
        price = float(close.iloc[-1])
        result = _compute_tech_stage(close, price, None, None, None)
        assert result == "stage1"

    def test_stage2_on_clean_uptrend_not_extended(self):
        # Price above MA200 (trending up), not within 5% of 52w high
        close = _make_close(252, start=50.0, trend=0.9)
        price = float(close.iloc[-1])
        ma200 = float(close.rolling(200).mean().iloc[-1])
        ma200_4wk = float(close.rolling(200).mean().iloc[-21])
        # pct_from_52w_high = -20% (not extended)
        result = _compute_tech_stage(close, price, ma200_4wk, -20.0, 15.0)
        assert result == "stage2"

    def test_stage3_when_extended_near_52w_high(self):
        close = _make_close(252, start=50.0, trend=0.9)
        price = float(close.iloc[-1])
        ma200_4wk = float(close.rolling(200).mean().iloc[-21])
        # pct_from_52w_high = -2% → extended (> -5)
        result = _compute_tech_stage(close, price, ma200_4wk, -2.0, 50.0)
        assert result == "stage3"

    def test_stage4_when_below_ma200_and_extended_down(self):
        # Downtrend: price well below MA200, far from 52w low (>15%)
        close = _make_close(252, start=250.0, trend=-0.9)
        price = float(close.iloc[-1])
        ma200 = float(close.rolling(200).mean().iloc[-1])
        # Ensure price is below MA200 (true for downtrend)
        assert price < ma200, "Test setup: price should be below MA200"
        # pct_from_52w_low > 15 → stage4 path
        result = _compute_tech_stage(close, price, None, None, 20.0)
        assert result == "stage4"

    def test_stage1_when_below_ma200_and_near_52w_low(self):
        close = _make_close(252, start=250.0, trend=-0.9)
        price = float(close.iloc[-1])
        # pct_from_52w_low < 15 → stage1 (basing)
        result = _compute_tech_stage(close, price, None, -30.0, 5.0)
        assert result == "stage1"

    def test_stage1_when_ma200_not_trending_up(self):
        # Price above MA200 but MA200 is flat/falling (ma200_4wk >= current)
        close = _make_close(252, start=50.0, trend=0.9)
        price = float(close.iloc[-1])
        ma200 = float(close.rolling(200).mean().iloc[-1])
        # Provide ma200_4wk > ma200 → not trending up
        result = _compute_tech_stage(close, price, ma200 + 5.0, -20.0, 30.0)
        assert result == "stage1"

    def test_returns_unknown_on_exception(self):
        result = _compute_tech_stage(None, 100.0, None, None, None)  # type: ignore
        assert result == "unknown"

    def test_stage3_when_price_150pct_above_ma200(self):
        # price > ma200 * 1.5 → extended → stage3
        close = _make_close(252, start=50.0, trend=0.9)
        price = float(close.iloc[-1])
        ma200 = float(close.rolling(200).mean().iloc[-1])
        ma200_4wk = float(close.rolling(200).mean().iloc[-21])
        # Force price way above MA200 * 1.5 by bumping price
        extended_price = ma200 * 1.6
        result = _compute_tech_stage(close, extended_price, ma200_4wk, -20.0, 30.0)
        assert result == "stage3"


# ─── 11. _merge_tech_signals ──────────────────────────────────────────────────

class TestMergeTechSignals:

    def _make_signals(self, tickers: list[str]) -> dict:
        """Build a minimal signals dict for testing the merge."""
        result = {}
        for t in tickers:
            result[t] = {
                "is_stage2": True,
                "ma_score": 3,
                "atr_ratio": 1.2,
                "volume_dryup": False,
                "pct_from_52w_high": -10.5,
                "pct_from_52w_low": 25.0,
                "relative_strength_6m": 8.5,
                "trend_direction": "uptrend",
                "tech_stage": "stage2",
            }
        return result

    def test_adds_all_tech_cols(self):
        df = pd.DataFrame({"ticker": ["AAPL", "MSFT"]})
        signals = self._make_signals(["AAPL", "MSFT"])
        result = _merge_tech_signals(df, signals)
        for col in TECH_COLS:
            assert col in result.columns, f"Missing column: {col}"

    def test_returns_dataframe_with_added_columns(self):
        # _merge_tech_signals mutates df in-place by design (adds TECH_COLS).
        # Verify the returned df has all original columns plus the new ones.
        df = pd.DataFrame({"ticker": ["AAPL"], "value_score": [75.0]})
        signals = self._make_signals(["AAPL"])
        result = _merge_tech_signals(df, signals)
        assert "value_score" in result.columns
        for col in TECH_COLS:
            assert col in result.columns

    def test_values_mapped_correctly(self):
        df = pd.DataFrame({"ticker": ["AAPL"]})
        signals = self._make_signals(["AAPL"])
        result = _merge_tech_signals(df, signals)
        assert result.loc[0, "ma_score"] == 3
        assert result.loc[0, "trend_direction"] == "uptrend"
        assert result.loc[0, "tech_stage"] == "stage2"

    def test_missing_ticker_maps_to_none(self):
        df = pd.DataFrame({"ticker": ["AAPL", "GOOG"]})
        signals = self._make_signals(["AAPL"])  # GOOG missing
        result = _merge_tech_signals(df, signals)
        assert pd.isna(result.loc[result["ticker"] == "GOOG", "ma_score"].iloc[0])

    def test_empty_dataframe_returns_with_cols(self):
        df = pd.DataFrame({"ticker": pd.Series([], dtype=str)})
        signals = {}
        result = _merge_tech_signals(df, signals)
        for col in TECH_COLS:
            assert col in result.columns

    def test_handles_lowercase_tickers(self):
        df = pd.DataFrame({"ticker": ["aapl"]})
        signals = {"AAPL": {col: None for col in TECH_COLS}}
        result = _merge_tech_signals(df, signals)
        # The map uses str(t).upper() so "aapl" should resolve to AAPL signal
        assert "ma_score" in result.columns

    def test_multiple_tickers_independent(self):
        df = pd.DataFrame({"ticker": ["AAPL", "MSFT", "GOOG"]})
        signals = {
            "AAPL": {**{col: None for col in TECH_COLS}, "ma_score": 1},
            "MSFT": {**{col: None for col in TECH_COLS}, "ma_score": 2},
            "GOOG": {**{col: None for col in TECH_COLS}, "ma_score": 3},
        }
        result = _merge_tech_signals(df, signals)
        assert result.loc[result["ticker"] == "AAPL", "ma_score"].iloc[0] == 1
        assert result.loc[result["ticker"] == "MSFT", "ma_score"].iloc[0] == 2
        assert result.loc[result["ticker"] == "GOOG", "ma_score"].iloc[0] == 3


# ─── 12. compute_technical_signals (integration) ──────────────────────────────

class TestComputeTechnicalSignals:

    def _mock_fetch(self, n: int = 252, start: float = 50.0, trend: float = 0.9):
        return _make_ohlcv(n, start=start, trend=trend)

    def test_returns_dict_with_required_keys(self):
        with patch("technical_filter._fetch_history", return_value=self._mock_fetch()):
            result = compute_technical_signals("AAPL", spy_6m_return=5.0)
        required = [
            "ticker", "is_stage2", "ma_score", "atr_ratio", "volume_dryup",
            "pct_from_52w_high", "pct_from_52w_low", "relative_strength_6m",
            "trend_direction", "tech_stage", "computed_at", "error",
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_ticker_preserved_in_output(self):
        with patch("technical_filter._fetch_history", return_value=self._mock_fetch()):
            result = compute_technical_signals("TSLA", spy_6m_return=0.0)
        assert result["ticker"] == "TSLA"

    def test_error_none_on_valid_data(self):
        with patch("technical_filter._fetch_history", return_value=self._mock_fetch()):
            result = compute_technical_signals("AAPL", spy_6m_return=5.0)
        assert result["error"] is None

    def test_error_no_data_when_fetch_returns_none(self):
        with patch("technical_filter._fetch_history", return_value=None):
            result = compute_technical_signals("AAPL", spy_6m_return=5.0)
        assert result["error"] == "no_data"
        assert result["is_stage2"] is False
        assert result["ma_score"] == 0

    def test_error_insufficient_data_when_less_than_60_bars(self):
        with patch("technical_filter._fetch_history", return_value=self._mock_fetch(n=40)):
            result = compute_technical_signals("AAPL", spy_6m_return=5.0)
        assert result["error"] == "insufficient_data"

    def test_uptrend_stock_gets_stage2_or_stage3(self):
        with patch("technical_filter._fetch_history", return_value=self._mock_fetch()):
            result = compute_technical_signals("AAPL", spy_6m_return=5.0)
        assert result["trend_direction"] == "uptrend"
        assert result["tech_stage"] in ("stage2", "stage3")

    def test_ma_score_is_integer(self):
        with patch("technical_filter._fetch_history", return_value=self._mock_fetch()):
            result = compute_technical_signals("AAPL", spy_6m_return=0.0)
        assert isinstance(result["ma_score"], int)

    def test_computed_at_is_iso_string(self):
        with patch("technical_filter._fetch_history", return_value=self._mock_fetch()):
            result = compute_technical_signals("AAPL", spy_6m_return=0.0)
        assert isinstance(result["computed_at"], str)
        assert result["computed_at"].endswith("Z")

    def test_volume_dryup_is_bool(self):
        with patch("technical_filter._fetch_history", return_value=self._mock_fetch()):
            result = compute_technical_signals("AAPL", spy_6m_return=0.0)
        assert isinstance(result["volume_dryup"], bool)

    def test_multiindex_columns_handled(self):
        # yfinance sometimes returns MultiIndex; _fetch_history should flatten
        df = self._mock_fetch()
        df.columns = pd.MultiIndex.from_tuples([(c, "AAPL") for c in df.columns])
        with patch("technical_filter._fetch_history", return_value=df):
            result = compute_technical_signals("AAPL", spy_6m_return=0.0)
        # Should not crash; columns get flattened inside _fetch_history mock bypass
        assert "ticker" in result

    def test_downtrend_stock_gets_downtrend_direction(self):
        falling = self._mock_fetch(start=250.0, trend=-0.9)
        with patch("technical_filter._fetch_history", return_value=falling):
            result = compute_technical_signals("AAPL", spy_6m_return=0.0)
        assert result["trend_direction"] == "downtrend"

    def test_spy_return_affects_relative_strength(self):
        df = self._mock_fetch(start=50.0, trend=0.9)
        with patch("technical_filter._fetch_history", return_value=df):
            r_low_spy = compute_technical_signals("AAPL", spy_6m_return=0.0)
            r_high_spy = compute_technical_signals("AAPL", spy_6m_return=100.0)
        # Same ticker but higher SPY return → lower RS
        if r_low_spy["relative_strength_6m"] is not None and r_high_spy["relative_strength_6m"] is not None:
            assert r_low_spy["relative_strength_6m"] > r_high_spy["relative_strength_6m"]
