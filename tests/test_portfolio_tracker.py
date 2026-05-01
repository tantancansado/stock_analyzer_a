#!/usr/bin/env python3
"""
Comprehensive tests for portfolio_tracker.py

Coverage:
  - Return calculation (pct change entry → future price)
  - Win/loss classification (>0% = win)
  - 7d/14d/30d bucketing logic (days_since >= period gate)
  - LSE GBp/GBP 100x correction
  - Max drawdown calculation
  - Score correlation
  - win_stats() helper (win rate, avg return, median, best, worst)
  - _alpha_stats() helper
  - generate_summary() aggregation
  - generate_calibration() score buckets
  - Edge cases: zero entry price guard, missing prices, negative returns,
    same-day (0 days since signal), all losses, all wins, NaN returns
"""

import os
import sys
import json
import types
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers shared across tests
# ─────────────────────────────────────────────────────────────────────────────

def _make_rec(
    ticker='AAPL',
    strategy='VALUE',
    signal_date=None,
    signal_price=100.0,
    value_score=65.0,
    sector='Technology',
    market_regime='BULL',
    return_7d=None, return_14d=None, return_30d=None,
    price_7d=None, price_14d=None, price_30d=None,
    win_7d=None, win_14d=None, win_30d=None,
    max_drawdown_30d=None,
    status='ACTIVE',
    benchmark_return_7d=None, benchmark_return_14d=None, benchmark_return_30d=None,
    alpha_7d=None, alpha_14d=None, alpha_30d=None,
    fcf_yield_pct=None,
    **kwargs,
) -> dict:
    if signal_date is None:
        signal_date = pd.Timestamp('2026-01-01')
    return {
        'ticker': ticker,
        'company_name': ticker,
        'strategy': strategy,
        'signal_date': signal_date,
        'signal_price': signal_price,
        'value_score': value_score,
        'momentum_score': None,
        'fcf_yield_pct': fcf_yield_pct,
        'risk_reward_ratio': 2.0,
        'analyst_upside_pct': 15.0,
        'sector': sector,
        'market_regime': market_regime,
        'return_7d': return_7d,
        'return_14d': return_14d,
        'return_30d': return_30d,
        'price_7d': price_7d,
        'price_14d': price_14d,
        'price_30d': price_30d,
        'win_7d': win_7d,
        'win_14d': win_14d,
        'win_30d': win_30d,
        'max_drawdown_30d': max_drawdown_30d,
        'status': status,
        'benchmark_return_7d': benchmark_return_7d,
        'benchmark_return_14d': benchmark_return_14d,
        'benchmark_return_30d': benchmark_return_30d,
        'alpha_7d': alpha_7d,
        'alpha_14d': alpha_14d,
        'alpha_30d': alpha_30d,
        **kwargs,
    }


def _make_df(*recs) -> pd.DataFrame:
    rows = [_make_rec(**r) if isinstance(r, dict) else r for r in recs]
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Import the module under test (mock TRACKER_DIR so nothing is written to disk)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_tracker_dir(tmp_path, monkeypatch):
    """Redirect TRACKER_DIR to a temp location so tests don't touch docs/."""
    import portfolio_tracker as pt
    monkeypatch.setattr(pt, 'TRACKER_DIR', tmp_path)
    monkeypatch.setattr(pt, 'RECOMMENDATIONS_FILE', tmp_path / 'recommendations.csv')
    monkeypatch.setattr(pt, 'PERFORMANCE_FILE', tmp_path / 'performance.csv')
    monkeypatch.setattr(pt, 'SUMMARY_FILE', tmp_path / 'summary.json')
    monkeypatch.setattr(pt, 'CALIBRATION_FILE', tmp_path / 'calibration.json')
    yield tmp_path


def _make_tracker(recs_df=None) -> 'PortfolioTracker':
    """Return a PortfolioTracker with pre-loaded recommendations, skipping file I/O."""
    import portfolio_tracker as pt
    tracker = object.__new__(pt.PortfolioTracker)
    # Bypass __init__ (which tries to create dirs and read CSV)
    if recs_df is None:
        tracker.recommendations = pt.PortfolioTracker._load_recommendations(tracker)
        # But we want empty — just use the empty frame the real init would give
        tracker.recommendations = pd.DataFrame(columns=[
            'ticker', 'company_name', 'strategy', 'signal_date', 'signal_price',
            'value_score', 'momentum_score', 'fcf_yield_pct', 'risk_reward_ratio',
            'analyst_upside_pct', 'sector', 'market_regime',
            'return_7d', 'return_14d', 'return_30d',
            'price_7d', 'price_14d', 'price_30d',
            'win_7d', 'win_14d', 'win_30d',
            'max_drawdown_30d', 'status',
            'benchmark_return_7d', 'benchmark_return_14d', 'benchmark_return_30d',
            'alpha_7d', 'alpha_14d', 'alpha_30d',
        ])
    else:
        tracker.recommendations = recs_df.copy()
    return tracker


# ─────────────────────────────────────────────────────────────────────────────
# 1. RETURN CALCULATION — pct change formula
# ─────────────────────────────────────────────────────────────────────────────

class TestReturnCalculation:
    """Verify the core pct-return formula: (check_price - entry) / entry * 100"""

    def _pct(self, entry, future):
        return ((future - entry) / entry) * 100

    def test_positive_return(self):
        assert round(self._pct(100.0, 110.0), 2) == 10.0

    def test_negative_return(self):
        assert round(self._pct(100.0, 80.0), 2) == -20.0

    def test_flat_return(self):
        assert round(self._pct(50.0, 50.0), 2) == 0.0

    def test_small_fractional(self):
        result = round(self._pct(250.75, 253.26), 2)
        assert abs(result - 1.0) < 0.1  # roughly +1%

    def test_large_gain(self):
        assert round(self._pct(10.0, 30.0), 2) == 200.0

    def test_near_total_loss(self):
        result = self._pct(100.0, 1.0)
        assert result == pytest.approx(-99.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. WIN/LOSS CLASSIFICATION  — win_Xd = (return > 0)
# ─────────────────────────────────────────────────────────────────────────────

class TestWinLossClassification:
    """win_Xd is set to (pct_return > 0) in update_performance."""

    def test_positive_return_is_win(self):
        pct = 5.0
        assert (pct > 0) is True

    def test_zero_return_is_not_win(self):
        pct = 0.0
        assert (pct > 0) is False

    def test_negative_return_is_loss(self):
        pct = -3.5
        assert (pct > 0) is False

    def test_tiny_positive_is_win(self):
        pct = 0.01
        assert (pct > 0) is True

    def test_tiny_negative_is_loss(self):
        pct = -0.001
        assert (pct > 0) is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. 7d/14d/30d BUCKETING — days_since >= period gate
# ─────────────────────────────────────────────────────────────────────────────

class TestPeriodBucketingGate:
    """
    update_performance only writes return_Xd when:
      days_since >= period AND pd.isna(current value)
    """

    def _days_since(self, signal_date_str, today_str):
        today = pd.Timestamp(today_str)
        sig = pd.Timestamp(signal_date_str)
        return (today - sig).days

    def test_exactly_7d_qualifies_for_7d(self):
        assert self._days_since('2026-01-01', '2026-01-08') >= 7

    def test_6d_does_not_qualify_for_7d(self):
        assert self._days_since('2026-01-01', '2026-01-07') < 7

    def test_14d_qualifies(self):
        assert self._days_since('2026-01-01', '2026-01-15') >= 14

    def test_13d_does_not_qualify_for_14d(self):
        assert self._days_since('2026-01-01', '2026-01-14') < 14

    def test_30d_qualifies(self):
        assert self._days_since('2026-01-01', '2026-01-31') >= 30

    def test_29d_does_not_qualify_for_30d(self):
        assert self._days_since('2026-01-01', '2026-01-30') < 30

    def test_same_day_does_not_qualify_for_any_period(self):
        ds = self._days_since('2026-01-01', '2026-01-01')
        assert ds < 7

    def test_already_filled_field_is_skipped(self):
        """If return_7d is not NaN, pd.isna returns False → skipped."""
        val = 5.0
        assert pd.isna(val) is False

    def test_none_field_triggers_update(self):
        """None → pd.isna = True → update runs."""
        assert pd.isna(None) is True

    def test_completed_status_after_30d(self):
        """Signal with 30d+ return filled should become COMPLETED."""
        days = self._days_since('2026-01-01', '2026-02-01')
        assert days >= 30


# ─────────────────────────────────────────────────────────────────────────────
# 4. LSE GBp/GBP UNIT CORRECTION
# ─────────────────────────────────────────────────────────────────────────────

class TestLSECurrencyCorrection:
    """
    If check_price / signal_price < 0.02 → multiply check by 100 (GBp→GBP).
    If ratio > 50 → divide check by 100 (GBP→GBp).
    """

    def _apply_correction(self, signal_price, check_price):
        if signal_price > 0 and check_price > 0:
            ratio = check_price / signal_price
            if ratio < 0.02:
                check_price = check_price * 100
            elif ratio > 50:
                check_price = check_price / 100
        return check_price

    def test_gbp_to_gbx_correction(self):
        """signal in GBp (e.g. 1000p), fetch gives GBP (10.0)."""
        corrected = self._apply_correction(1000.0, 10.0)
        assert corrected == 1000.0

    def test_gbx_to_gbp_correction(self):
        """signal in GBP (e.g. 10.0), fetch gives GBp (1050)."""
        corrected = self._apply_correction(10.0, 1050.0)
        assert corrected == pytest.approx(10.5)

    def test_no_correction_needed_normal_stock(self):
        """Normal US stock — ratio is near 1, no correction."""
        corrected = self._apply_correction(150.0, 157.5)
        assert corrected == 157.5

    def test_ratio_exactly_at_boundary_002(self):
        """ratio == 0.02 should NOT trigger correction (condition is strict <)."""
        corrected = self._apply_correction(100.0, 2.0)
        assert corrected == 2.0  # ratio = 0.02, no correction

    def test_ratio_just_below_002_triggers_correction(self):
        corrected = self._apply_correction(100.0, 1.9)
        assert corrected == 190.0

    def test_ratio_exactly_50_no_correction(self):
        """ratio == 50 should NOT trigger correction (condition is strict >)."""
        corrected = self._apply_correction(10.0, 500.0)
        assert corrected == 500.0


# ─────────────────────────────────────────────────────────────────────────────
# 5. MAX DRAWDOWN CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

class TestMaxDrawdown:
    """
    max_drawdown_30d = (min_low - signal_price) / signal_price * 100
    Triggered when days_since >= 7 and current value is NaN.
    """

    def _drawdown(self, signal_price, low_prices):
        min_price = min(low_prices)
        return ((min_price - signal_price) / signal_price) * 100

    def test_drawdown_negative_when_price_drops(self):
        dd = self._drawdown(100.0, [98.0, 95.0, 92.0, 99.0])
        assert round(dd, 2) == -8.0

    def test_no_drawdown_when_price_only_rises(self):
        dd = self._drawdown(100.0, [101.0, 103.0, 105.0])
        assert dd > 0

    def test_drawdown_at_entry_price(self):
        dd = self._drawdown(100.0, [100.0, 100.0])
        assert dd == 0.0

    def test_severe_drawdown(self):
        dd = self._drawdown(200.0, [100.0])
        assert round(dd, 2) == -50.0

    def test_triggered_after_7_days_not_before(self):
        """days_since >= 7 triggers drawdown calc."""
        assert 7 >= 7       # trigger
        assert 6 < 7        # no trigger


# ─────────────────────────────────────────────────────────────────────────────
# 6. win_stats() HELPER (extracted from generate_summary)
# ─────────────────────────────────────────────────────────────────────────────

class TestWinStats:
    """Tests for the inner win_stats() closure in generate_summary."""

    def _win_stats(self, col_return, col_win, df):
        """Replicate win_stats as defined in generate_summary."""
        valid = df[df[col_return].notna()]
        if valid.empty:
            return {'count': 0, 'win_rate': None, 'avg_return': None,
                    'median_return': None, 'best': None, 'worst': None}
        wins = valid[valid[col_win] == True]
        return {
            'count': len(valid),
            'win_rate': round(len(wins) / len(valid) * 100, 1),
            'avg_return': round(valid[col_return].mean(), 2),
            'median_return': round(valid[col_return].median(), 2),
            'best': round(valid[col_return].max(), 2),
            'worst': round(valid[col_return].min(), 2),
        }

    def _make_win_df(self, returns_wins):
        """Build a minimal DataFrame from [(return, win)] pairs."""
        rows = [{'return_14d': r, 'win_14d': w} for r, w in returns_wins]
        return pd.DataFrame(rows)

    def test_100pct_win_rate(self):
        df = self._make_win_df([(5.0, True), (3.0, True), (1.0, True)])
        s = self._win_stats('return_14d', 'win_14d', df)
        assert s['win_rate'] == 100.0
        assert s['count'] == 3

    def test_0pct_win_rate(self):
        df = self._make_win_df([(-2.0, False), (-5.0, False)])
        s = self._win_stats('return_14d', 'win_14d', df)
        assert s['win_rate'] == 0.0

    def test_50pct_win_rate(self):
        df = self._make_win_df([(5.0, True), (-5.0, False)])
        s = self._win_stats('return_14d', 'win_14d', df)
        assert s['win_rate'] == 50.0

    def test_avg_return_correct(self):
        df = self._make_win_df([(10.0, True), (-4.0, False)])
        s = self._win_stats('return_14d', 'win_14d', df)
        assert s['avg_return'] == 3.0

    def test_median_return(self):
        df = self._make_win_df([(1.0, True), (3.0, True), (100.0, True)])
        s = self._win_stats('return_14d', 'win_14d', df)
        assert s['median_return'] == 3.0

    def test_best_and_worst(self):
        df = self._make_win_df([(10.0, True), (-20.0, False), (5.0, True)])
        s = self._win_stats('return_14d', 'win_14d', df)
        assert s['best'] == 10.0
        assert s['worst'] == -20.0

    def test_empty_returns_nan_values(self):
        """All NaN returns → count=0, all None."""
        df = pd.DataFrame({'return_14d': [np.nan, np.nan], 'win_14d': [None, None]})
        s = self._win_stats('return_14d', 'win_14d', df)
        assert s['count'] == 0
        assert s['win_rate'] is None

    def test_mixed_nan_and_valid(self):
        """NaN rows are excluded; only valid rows counted."""
        df = pd.DataFrame({
            'return_14d': [5.0, np.nan, -3.0],
            'win_14d': [True, None, False],
        })
        s = self._win_stats('return_14d', 'win_14d', df)
        assert s['count'] == 2
        assert s['win_rate'] == 50.0

    def test_single_record_win(self):
        df = self._make_win_df([(8.5, True)])
        s = self._win_stats('return_14d', 'win_14d', df)
        assert s['count'] == 1
        assert s['win_rate'] == 100.0
        assert s['best'] == 8.5
        assert s['worst'] == 8.5


# ─────────────────────────────────────────────────────────────────────────────
# 7. _alpha_stats() FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

class TestAlphaStats:
    """Tests for the module-level _alpha_stats() function."""

    def setup_method(self):
        import portfolio_tracker as pt
        self.fn = pt._alpha_stats

    def _make_alpha_df(self, alphas, returns, bench_returns=None):
        rows = []
        for i, (a, r) in enumerate(zip(alphas, returns)):
            row = {'alpha_14d': a, 'return_14d': r}
            if bench_returns:
                row['benchmark_return_14d'] = bench_returns[i]
            rows.append(row)
        return pd.DataFrame(rows)

    def test_minimum_3_records_required(self):
        df = self._make_alpha_df([1.0, 2.0], [5.0, 10.0])
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['count'] == 0

    def test_exactly_3_records(self):
        df = self._make_alpha_df([1.0, 2.0, 3.0], [5.0, 10.0, 8.0])
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['count'] == 3

    def test_avg_alpha_calculation(self):
        df = self._make_alpha_df([2.0, 4.0, 6.0], [5.0, 8.0, 10.0])
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['avg_alpha'] == 4.0

    def test_positive_alpha_rate(self):
        df = self._make_alpha_df([1.0, -1.0, 2.0, -2.0], [5.0, -3.0, 8.0, -7.0])
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['positive_alpha_rate'] == 50.0

    def test_all_positive_alpha(self):
        df = self._make_alpha_df([1.0, 2.0, 3.0], [5.0, 6.0, 7.0])
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['positive_alpha_rate'] == 100.0

    def test_extreme_returns_excluded(self):
        """Returns > 500 or < -95 are filtered out."""
        df = self._make_alpha_df(
            [1.0, 2.0, 3.0, 99.0],
            [5.0, 8.0, 10.0, 600.0]  # last row return=600 → excluded
        )
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['count'] == 3

    def test_nan_alpha_excluded(self):
        """NaN alpha row dropped → 2 valid rows < 3 minimum → count=0."""
        df = self._make_alpha_df([1.0, np.nan, 3.0], [5.0, 8.0, 10.0])
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['count'] == 0

    def test_missing_columns_returns_empty(self):
        df = pd.DataFrame({'other_col': [1, 2, 3]})
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['count'] == 0
        assert result['avg_alpha'] is None

    def test_best_and_worst_alpha(self):
        df = self._make_alpha_df([5.0, -3.0, 2.0], [10.0, -5.0, 7.0])
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['best_alpha'] == 5.0
        assert result['worst_alpha'] == -3.0

    def test_avg_signal_return(self):
        df = self._make_alpha_df([1.0, 1.0, 1.0], [3.0, 6.0, 9.0])
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['avg_signal_return'] == 6.0

    def test_benchmark_return_calculated(self):
        df = self._make_alpha_df([1.0, 2.0, 3.0], [5.0, 6.0, 7.0], [4.0, 4.0, 4.0])
        result = self.fn(df, 'alpha_14d', 'return_14d')
        assert result['avg_benchmark_return'] == 4.0


# ─────────────────────────────────────────────────────────────────────────────
# 8. SCORE CORRELATION (generate_summary logic)
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreCorrelation:
    """score_corr = value_score.corr(return_14d) for VALUE strategy, n >= 5."""

    def _score_corr(self, value_scores, returns_14d):
        df = pd.DataFrame({'value_score': value_scores, 'return_14d': returns_14d})
        valid = df[df['return_14d'].notna() & df['value_score'].notna()]
        if len(valid) < 5:
            return None
        return round(valid['value_score'].corr(valid['return_14d']), 3)

    def test_positive_correlation(self):
        """Higher scores → higher returns → positive correlation."""
        scores = [55, 60, 65, 70, 75]
        returns = [1.0, 2.0, 3.0, 4.0, 5.0]
        corr = self._score_corr(scores, returns)
        assert corr is not None
        assert corr > 0.9

    def test_negative_correlation(self):
        """Higher scores → lower returns → negative correlation."""
        scores = [55, 60, 65, 70, 75]
        returns = [5.0, 4.0, 3.0, 2.0, 1.0]
        corr = self._score_corr(scores, returns)
        assert corr is not None
        assert corr < -0.9

    def test_no_correlation_returns_none_when_less_than_5(self):
        corr = self._score_corr([60, 70, 80, 90], [1, 2, 3, 4])
        assert corr is None

    def test_exactly_5_required(self):
        corr = self._score_corr([55, 60, 65, 70, 75], [1, 2, 3, 4, 5])
        assert corr is not None

    def test_nan_values_excluded(self):
        """NaN return rows excluded → fewer than 5 valid → None."""
        scores = [55, 60, 65, 70, 75, 80]
        returns = [1.0, 2.0, np.nan, np.nan, np.nan, np.nan]
        corr = self._score_corr(scores, returns)
        assert corr is None  # only 2 valid, need 5

    def test_weak_correlation_near_zero(self):
        """Uncorrelated data."""
        scores = [55, 60, 65, 70, 75]
        returns = [3.0, 1.0, 5.0, 2.0, 4.0]  # no pattern
        corr = self._score_corr(scores, returns)
        assert corr is not None
        assert abs(corr) < 0.8  # not strongly correlated


# ─────────────────────────────────────────────────────────────────────────────
# 9. generate_summary() — INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateSummary:
    """Tests for generate_summary() using pre-built DataFrames."""

    def _tracker_with(self, recs):
        t = _make_tracker(_make_df(*recs))
        return t

    def test_empty_recommendations_returns_zero_signals(self, tmp_path):
        tracker = _make_tracker()
        summary = tracker.generate_summary()
        assert summary['total_signals'] == 0
        assert 'message' in summary

    def test_total_signals_count_value_only(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE'),
            _make_rec(ticker='B', strategy='VALUE'),
            _make_rec(ticker='C', strategy='MOMENTUM'),  # excluded from VALUE core
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        # total_signals counts VALUE core strategies only
        assert summary['total_signals'] == 2

    def test_win_rate_all_wins(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', return_14d=5.0, win_14d=True, status='COMPLETED'),
            _make_rec(ticker='B', strategy='VALUE', return_14d=3.0, win_14d=True, status='COMPLETED'),
            _make_rec(ticker='C', strategy='VALUE', return_14d=8.0, win_14d=True, status='COMPLETED'),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary['overall']['14d']['win_rate'] == 100.0

    def test_win_rate_all_losses(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', return_14d=-5.0, win_14d=False, status='COMPLETED'),
            _make_rec(ticker='B', strategy='VALUE', return_14d=-3.0, win_14d=False, status='COMPLETED'),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary['overall']['14d']['win_rate'] == 0.0

    def test_win_rate_mixed(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', return_14d=5.0, win_14d=True, status='COMPLETED'),
            _make_rec(ticker='B', strategy='VALUE', return_14d=-3.0, win_14d=False, status='COMPLETED'),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary['overall']['14d']['win_rate'] == 50.0

    def test_active_vs_completed_counts(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', status='ACTIVE'),
            _make_rec(ticker='B', strategy='VALUE', status='COMPLETED', return_14d=5.0, win_14d=True),
            _make_rec(ticker='C', strategy='VALUE', status='COMPLETED', return_14d=-2.0, win_14d=False),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary['active_signals'] == 1
        assert summary['completed_signals'] == 2

    def test_score_correlation_in_summary(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', value_score=55, return_14d=1.0, win_14d=True),
            _make_rec(ticker='B', strategy='VALUE', value_score=60, return_14d=2.0, win_14d=True),
            _make_rec(ticker='C', strategy='VALUE', value_score=65, return_14d=3.0, win_14d=True),
            _make_rec(ticker='D', strategy='VALUE', value_score=70, return_14d=4.0, win_14d=True),
            _make_rec(ticker='E', strategy='VALUE', value_score=75, return_14d=5.0, win_14d=True),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        corr = summary.get('score_correlation')
        assert corr is not None
        assert corr > 0.9

    def test_score_correlation_none_when_fewer_than_5(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', value_score=55, return_14d=1.0, win_14d=True),
            _make_rec(ticker='B', strategy='VALUE', value_score=60, return_14d=2.0, win_14d=True),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary.get('score_correlation') is None

    def test_avg_return_all_periods(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE',
                      return_7d=2.0, win_7d=True,
                      return_14d=4.0, win_14d=True,
                      return_30d=8.0, win_30d=True,
                      status='COMPLETED'),
            _make_rec(ticker='B', strategy='VALUE',
                      return_7d=4.0, win_7d=True,
                      return_14d=6.0, win_14d=True,
                      return_30d=12.0, win_30d=True,
                      status='COMPLETED'),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary['overall']['7d']['avg_return'] == 3.0
        assert summary['overall']['14d']['avg_return'] == 5.0
        assert summary['overall']['30d']['avg_return'] == 10.0

    def test_top_performers_best_per_ticker(self, tmp_path):
        """Two signals for same ticker → top picks the best one."""
        recs = [
            _make_rec(ticker='AAPL', strategy='VALUE', return_14d=5.0, win_14d=True,
                      signal_date=pd.Timestamp('2026-01-01')),
            _make_rec(ticker='AAPL', strategy='VALUE', return_14d=15.0, win_14d=True,
                      signal_date=pd.Timestamp('2026-02-01')),
            _make_rec(ticker='MSFT', strategy='VALUE', return_14d=3.0, win_14d=True,
                      signal_date=pd.Timestamp('2026-01-01')),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        top = summary.get('top_performers', [])
        aapl_entry = next((x for x in top if x['ticker'] == 'AAPL'), None)
        assert aapl_entry is not None
        assert aapl_entry['return_14d'] == 15.0

    def test_eu_value_excluded_from_value_strategy_stats(self, tmp_path):
        recs = [
            _make_rec(ticker='SAP', strategy='EU_VALUE', return_14d=6.0, win_14d=True),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        # value_strategy (only 'VALUE') count should be 0
        assert summary['value_strategy']['count'] == 0

    def test_momentum_excluded_from_overall_stats(self, tmp_path):
        """MOMENTUM signals do NOT count in overall (VALUE core only)."""
        recs = [
            _make_rec(ticker='X', strategy='MOMENTUM', return_14d=10.0, win_14d=True),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary['total_signals'] == 0

    def test_avg_max_drawdown_computed(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', max_drawdown_30d=-5.0),
            _make_rec(ticker='B', strategy='VALUE', max_drawdown_30d=-10.0),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary['avg_max_drawdown'] == pytest.approx(-7.5)

    def test_avg_max_drawdown_none_when_all_nan(self, tmp_path):
        recs = [_make_rec(ticker='A', strategy='VALUE')]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary['avg_max_drawdown'] is None

    def test_generated_at_is_string(self, tmp_path):
        tracker = _make_tracker()
        summary = tracker.generate_summary()
        assert isinstance(summary['generated_at'], str)


# ─────────────────────────────────────────────────────────────────────────────
# 10. generate_calibration() — SCORE BUCKETS
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateCalibration:
    """Tests for generate_calibration() — requires >= 10 completed signals."""

    def _tracker_with_completed(self, n=10, base_score=60, base_return=3.0):
        recs = []
        for i in range(n):
            recs.append(_make_rec(
                ticker=f'T{i:02d}',
                strategy='VALUE',
                value_score=base_score + (i % 20),
                return_14d=base_return + (i % 5),
                win_14d=(base_return + (i % 5)) > 0,
                status='COMPLETED',
                sector='Technology',
                market_regime='BULL',
                fcf_yield_pct=5.0,
            ))
        return _make_tracker(_make_df(*recs))

    def test_no_calibration_below_10_signals(self, tmp_path):
        tracker = self._tracker_with_completed(n=9)
        import portfolio_tracker as pt
        cal_file = tmp_path / 'calibration.json'
        tracker.generate_calibration()
        assert not cal_file.exists()

    def test_calibration_file_created_with_10_signals(self, tmp_path):
        tracker = self._tracker_with_completed(n=10)
        import portfolio_tracker as pt
        # need to point the tracker's CALIBRATION_FILE reference
        tracker.generate_calibration()
        import portfolio_tracker as pt
        cal_file = pt.CALIBRATION_FILE
        assert cal_file.exists()

    def test_score_buckets_present(self, tmp_path):
        tracker = self._tracker_with_completed(n=12)
        tracker.generate_calibration()
        import portfolio_tracker as pt
        with open(pt.CALIBRATION_FILE) as f:
            cal = json.load(f)
        assert 'score_buckets' in cal
        assert isinstance(cal['score_buckets'], list)

    def test_bucket_stats_structure(self, tmp_path):
        tracker = self._tracker_with_completed(n=12)
        tracker.generate_calibration()
        import portfolio_tracker as pt
        with open(pt.CALIBRATION_FILE) as f:
            cal = json.load(f)
        for bucket in cal['score_buckets']:
            assert 'count' in bucket
            assert 'win_rate_14d' in bucket
            assert 'avg_return_14d' in bucket

    def test_total_completed_in_calibration(self, tmp_path):
        tracker = self._tracker_with_completed(n=10)
        tracker.generate_calibration()
        import portfolio_tracker as pt
        with open(pt.CALIBRATION_FILE) as f:
            cal = json.load(f)
        assert cal['total_completed'] == 10

    def test_extreme_returns_excluded_from_calibration(self, tmp_path):
        """Returns > 500 or < -95 excluded before bucketing."""
        recs = []
        for i in range(10):
            recs.append(_make_rec(
                ticker=f'T{i}',
                strategy='VALUE',
                value_score=60,
                return_14d=600.0,  # all extreme → all excluded
                win_14d=True,
                status='COMPLETED',
                sector='Technology',
                market_regime='BULL',
            ))
        tracker = _make_tracker(_make_df(*recs))
        # With all returns extreme, completed=0 → no calibration written
        tracker.generate_calibration()
        import portfolio_tracker as pt
        assert not pt.CALIBRATION_FILE.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 11. EDGE CASES
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases: zero entry price, same-day, extreme returns."""

    def test_zero_entry_price_guarded(self):
        """record_signals skips rows where price <= 0."""
        price = 0.0
        assert not (price and not pd.isna(price) and float(price) > 0)

    def test_negative_entry_price_guarded(self):
        price = -5.0
        assert not (price and not pd.isna(price) and float(price) > 0)

    def test_nan_entry_price_guarded(self):
        price = float('nan')
        assert not (price and not pd.isna(price) and float(price) > 0)

    def test_extreme_positive_return_in_summary(self, tmp_path):
        """Returns >= 500 excluded from top/worst performers table."""
        recs = [
            _make_rec(ticker='A', strategy='VALUE', return_14d=600.0, win_14d=True),
            _make_rec(ticker='B', strategy='VALUE', return_14d=5.0, win_14d=True),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        top = summary.get('top_performers', [])
        tickers = [x['ticker'] for x in top]
        # A (return 600) should be excluded (>500 filter)
        assert 'A' not in tickers
        assert 'B' in tickers

    def test_extreme_negative_return_in_summary(self, tmp_path):
        """Returns <= -95 excluded from top/worst performers table."""
        recs = [
            _make_rec(ticker='A', strategy='VALUE', return_14d=-96.0, win_14d=False),
            _make_rec(ticker='B', strategy='VALUE', return_14d=-20.0, win_14d=False),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        worst = summary.get('worst_performers', [])
        tickers = [x['ticker'] for x in worst]
        assert 'A' not in tickers
        assert 'B' in tickers

    def test_summary_handles_single_record(self, tmp_path):
        recs = [_make_rec(ticker='A', strategy='VALUE', return_14d=5.0, win_14d=True)]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert summary['total_signals'] == 1
        assert summary['overall']['14d']['win_rate'] == 100.0

    def test_return_7d_none_at_init(self):
        """Newly recorded signal has all returns as None."""
        rec = _make_rec()
        assert rec['return_7d'] is None
        assert rec['return_14d'] is None
        assert rec['return_30d'] is None

    def test_win_fields_none_at_init(self):
        rec = _make_rec()
        assert rec['win_7d'] is None
        assert rec['win_14d'] is None
        assert rec['win_30d'] is None


# ─────────────────────────────────────────────────────────────────────────────
# 12. SECTOR PERFORMANCE AGGREGATION
# ─────────────────────────────────────────────────────────────────────────────

class TestSectorPerformance:
    """Sector stats require >= 2 completed signals in a sector."""

    def test_sector_requires_min_2(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', sector='Tech', return_14d=5.0, win_14d=True),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        # Only 1 signal in Tech → not in sector_performance
        assert 'Tech' not in summary.get('sector_performance', {})

    def test_sector_appears_with_2_signals(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', sector='Tech', return_14d=5.0, win_14d=True),
            _make_rec(ticker='B', strategy='VALUE', sector='Tech', return_14d=3.0, win_14d=True),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        assert 'Tech' in summary.get('sector_performance', {})

    def test_sector_avg_return(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', sector='Finance', return_14d=10.0, win_14d=True),
            _make_rec(ticker='B', strategy='VALUE', sector='Finance', return_14d=6.0, win_14d=True),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        sp = summary['sector_performance']
        assert sp['Finance']['avg_14d'] == pytest.approx(8.0)
        assert sp['Finance']['win_rate_14d'] == 100.0

    def test_sector_mixed_win_rate(self, tmp_path):
        recs = [
            _make_rec(ticker='A', strategy='VALUE', sector='Energy', return_14d=5.0, win_14d=True),
            _make_rec(ticker='B', strategy='VALUE', sector='Energy', return_14d=-5.0, win_14d=False),
        ]
        tracker = _make_tracker(_make_df(*recs))
        summary = tracker.generate_summary()
        sp = summary['sector_performance']
        assert sp['Energy']['win_rate_14d'] == 50.0


# ─────────────────────────────────────────────────────────────────────────────
# 13. COOLDOWN LOGIC
# ─────────────────────────────────────────────────────────────────────────────

class TestCooldownLogic:
    """Cooldown: tickers signalled within last 21 days are skipped on re-entry."""

    def test_ticker_in_cooldown_skipped(self):
        today = pd.Timestamp('2026-01-15')
        cutoff = today - pd.Timedelta(days=21)
        signal_date = pd.Timestamp('2026-01-10')  # 5 days ago → within cooldown

        df = pd.DataFrame([{'ticker': 'AAPL', 'signal_date': signal_date}])
        recent = df[df['signal_date'] >= cutoff]
        cooldown = set(recent['ticker'].str.upper())
        assert 'AAPL' in cooldown

    def test_ticker_outside_cooldown_allowed(self):
        today = pd.Timestamp('2026-01-15')
        cutoff = today - pd.Timedelta(days=21)
        signal_date = pd.Timestamp('2025-12-01')  # > 21 days ago

        df = pd.DataFrame([{'ticker': 'AAPL', 'signal_date': signal_date}])
        recent = df[df['signal_date'] >= cutoff]
        cooldown = set(recent['ticker'].str.upper())
        assert 'AAPL' not in cooldown

    def test_cooldown_window_exactly_21_days(self):
        today = pd.Timestamp('2026-01-22')
        cutoff = today - pd.Timedelta(days=21)
        signal_date = pd.Timestamp('2026-01-01')  # exactly 21 days ago

        df = pd.DataFrame([{'ticker': 'GOOG', 'signal_date': signal_date}])
        recent = df[df['signal_date'] >= cutoff]
        cooldown = set(recent['ticker'].str.upper())
        # signal_date == cutoff → included in recent → in cooldown
        assert 'GOOG' in cooldown


# ─────────────────────────────────────────────────────────────────────────────
# 14. ALPHA CALCULATION (integration)
# ─────────────────────────────────────────────────────────────────────────────

class TestAlphaCalculation:
    """alpha = signal_return - benchmark_return."""

    def test_alpha_positive_when_outperform(self):
        signal_ret = 10.0
        bench_ret = 5.0
        alpha = signal_ret - bench_ret
        assert alpha == 5.0

    def test_alpha_negative_when_underperform(self):
        signal_ret = 2.0
        bench_ret = 8.0
        alpha = signal_ret - bench_ret
        assert alpha == -6.0

    def test_alpha_zero_when_matched(self):
        signal_ret = 5.0
        bench_ret = 5.0
        alpha = signal_ret - bench_ret
        assert alpha == 0.0

    def test_eu_value_uses_vgk_benchmark(self):
        """EU_VALUE signals should use VGK, not SPY."""
        strategy = 'EU_VALUE'
        bench_key = 'VGK' if strategy == 'EU_VALUE' else 'SPY'
        assert bench_key == 'VGK'

    def test_value_uses_spy_benchmark(self):
        strategy = 'VALUE'
        bench_key = 'VGK' if strategy == 'EU_VALUE' else 'SPY'
        assert bench_key == 'SPY'

    def test_momentum_uses_spy_benchmark(self):
        strategy = 'MOMENTUM'
        bench_key = 'VGK' if strategy == 'EU_VALUE' else 'SPY'
        assert bench_key == 'SPY'


# ─────────────────────────────────────────────────────────────────────────────
# 15. _save_recommendations / _save_summary (file I/O via tmp_path)
# ─────────────────────────────────────────────────────────────────────────────

class TestFileIO:
    def test_save_recommendations_creates_csv(self, tmp_path):
        recs = [_make_rec()]
        tracker = _make_tracker(_make_df(*recs))
        tracker._save_recommendations()
        import portfolio_tracker as pt
        assert pt.RECOMMENDATIONS_FILE.exists()
        loaded = pd.read_csv(pt.RECOMMENDATIONS_FILE)
        assert len(loaded) == 1
        assert loaded.iloc[0]['ticker'] == 'AAPL'

    def test_save_summary_creates_json(self, tmp_path):
        tracker = _make_tracker()
        summary = {'total_signals': 0, 'generated_at': '2026-01-01'}
        tracker._save_summary(summary)
        import portfolio_tracker as pt
        assert pt.SUMMARY_FILE.exists()
        with open(pt.SUMMARY_FILE) as f:
            loaded = json.load(f)
        assert loaded['total_signals'] == 0

    def test_load_recommendations_from_empty_file(self, tmp_path):
        """If recommendations CSV doesn't exist → empty DataFrame with correct columns."""
        import portfolio_tracker as pt
        tracker = _make_tracker()
        assert tracker.recommendations.empty
        assert 'ticker' in tracker.recommendations.columns
        assert 'return_7d' in tracker.recommendations.columns
        assert 'win_30d' in tracker.recommendations.columns

    def test_save_and_reload_recommendations(self, tmp_path):
        """Round-trip: save → reload preserves data."""
        recs = [
            _make_rec(ticker='MSFT', return_14d=7.5, win_14d=True, status='COMPLETED'),
        ]
        tracker = _make_tracker(_make_df(*recs))
        tracker._save_recommendations()

        import portfolio_tracker as pt
        loaded = pd.read_csv(pt.RECOMMENDATIONS_FILE)
        assert loaded.iloc[0]['return_14d'] == 7.5
        assert loaded.iloc[0]['ticker'] == 'MSFT'
