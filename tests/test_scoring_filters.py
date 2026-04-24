#!/usr/bin/env python3
"""
Tests para scoring/filters.py — funciones puras extraídas de
SuperScoreIntegrator._apply_advanced_filters (ese método tenía 963 líneas,
imposible de testear en aislamiento).

Cada regla crítica de penalización/bonus tiene su test. Si alguien cambia
los pesos (15/5 market, +7/+3/+2 RS Line, etc.) sin querer, aquí salta.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd

from scoring.filters import (
    derive_market_penalty,
    apply_market_regime_to_df,
    compute_filter_penalty,
    apply_filter_penalty,
    compute_rs_line_bonus,
    apply_rs_line_bonus,
    MARKET_PENALTY_AVOID,
    MARKET_PENALTY_CAUTION,
    MARKET_PENALTY_SAFE,
)


# ── Market regime penalty ─────────────────────────────────────────────────────

class TestMarketPenalty:

    def test_avoid_is_15(self):
        assert derive_market_penalty('AVOID') == 15
        assert MARKET_PENALTY_AVOID == 15

    def test_caution_is_5(self):
        assert derive_market_penalty('CAUTION') == 5
        assert MARKET_PENALTY_CAUTION == 5

    def test_uptrend_is_zero(self):
        assert derive_market_penalty('CONFIRMED_UPTREND') == 0
        assert derive_market_penalty('SAFE_TO_TRADE') == 0
        assert MARKET_PENALTY_SAFE == 0

    def test_none_and_empty_is_zero(self):
        assert derive_market_penalty(None) == 0
        assert derive_market_penalty('') == 0

    def test_case_insensitive(self):
        assert derive_market_penalty('avoid') == 15
        assert derive_market_penalty('  Caution  ') == 5


class TestApplyMarketRegime:

    def test_adds_columns_without_mutating_input(self):
        df = pd.DataFrame({'ticker': ['AAPL', 'MSFT']})
        result = apply_market_regime_to_df(df, 'BULL', 'SAFE_TO_TRADE')
        assert 'market_regime' in result.columns
        assert 'market_recommendation' in result.columns
        assert list(result['market_regime']) == ['BULL', 'BULL']
        assert list(result['market_recommendation']) == ['SAFE_TO_TRADE', 'SAFE_TO_TRADE']
        # Input df was not mutated
        assert 'market_regime' not in df.columns


# ── Filter penalty aggregation ────────────────────────────────────────────────

class TestComputeFilterPenalty:

    def test_market_penalty_only(self):
        """Sin otros factores, penalty = market_penalty."""
        df = pd.DataFrame({'ticker': ['A', 'B', 'C']})
        result = compute_filter_penalty(df, market_penalty=5)
        assert list(result['filter_penalty']) == pytest.approx([5.0, 5.0, 5.0])

    def test_ma_filter_fail_adds_10(self):
        df = pd.DataFrame({
            'ticker': ['PASS', 'FAIL'],
            'ma_filter_pass': [True, False],
        })
        result = compute_filter_penalty(df, market_penalty=0)
        assert result.loc[result['ticker'] == 'PASS', 'filter_penalty'].iloc[0] == pytest.approx(0.0)
        assert result.loc[result['ticker'] == 'FAIL', 'filter_penalty'].iloc[0] == pytest.approx(10.0)

    def test_strong_distribution_adds_15(self):
        df = pd.DataFrame({
            'ticker': ['X'],
            'ad_signal': ['STRONG_DISTRIBUTION'],
        })
        result = compute_filter_penalty(df, market_penalty=0)
        assert result['filter_penalty'].iloc[0] == pytest.approx(15.0)

    def test_distribution_adds_10(self):
        df = pd.DataFrame({
            'ticker': ['X'],
            'ad_signal': ['DISTRIBUTION'],
        })
        result = compute_filter_penalty(df, market_penalty=0)
        assert result['filter_penalty'].iloc[0] == pytest.approx(10.0)

    def test_low_ad_score_adds_5(self):
        df = pd.DataFrame({
            'ticker': ['LOW', 'HIGH'],
            'ad_score': [30.0, 70.0],
        })
        result = compute_filter_penalty(df, market_penalty=0)
        assert result.loc[result['ticker'] == 'LOW', 'filter_penalty'].iloc[0] == pytest.approx(5.0)
        assert result.loc[result['ticker'] == 'HIGH', 'filter_penalty'].iloc[0] == pytest.approx(0.0)

    def test_mega_float_adds_3(self):
        df = pd.DataFrame({
            'ticker': ['MEGA', 'SMALL'],
            'float_category': ['MEGA_FLOAT', 'SMALL_FLOAT'],
        })
        result = compute_filter_penalty(df, market_penalty=0)
        assert result.loc[result['ticker'] == 'MEGA', 'filter_penalty'].iloc[0] == pytest.approx(3.0)
        assert result.loc[result['ticker'] == 'SMALL', 'filter_penalty'].iloc[0] == pytest.approx(0.0)

    def test_penalties_compose(self):
        """Market (15) + MA fail (10) + STRONG_DIST (15) + low AD (5) + MEGA (3) = 48"""
        df = pd.DataFrame({
            'ticker': ['WORST'],
            'ma_filter_pass': [False],
            'ad_signal': ['STRONG_DISTRIBUTION'],
            'ad_score': [20.0],
            'float_category': ['MEGA_FLOAT'],
        })
        result = compute_filter_penalty(df, market_penalty=15)
        assert result['filter_penalty'].iloc[0] == pytest.approx(48.0)

    def test_missing_columns_tolerated(self):
        """Si falta una columna, esa señal no contribuye al penalty."""
        df = pd.DataFrame({'ticker': ['X']})  # no ma_filter_pass, no ad_signal, etc.
        result = compute_filter_penalty(df, market_penalty=5)
        assert result['filter_penalty'].iloc[0] == pytest.approx(5.0)


class TestApplyFilterPenalty:

    def test_subtracts_penalty_and_clips_to_zero(self):
        df = pd.DataFrame({
            'ticker': ['A', 'B'],
            'super_score_ultimate': [80.0, 50.0],
            'filter_penalty':       [30.0, 60.0],  # second would go negative
        })
        result = apply_filter_penalty(df)
        assert result.loc[result['ticker'] == 'A', 'super_score_ultimate'].iloc[0] == pytest.approx(50.0)
        assert result.loc[result['ticker'] == 'B', 'super_score_ultimate'].iloc[0] == pytest.approx(0.0)  # clipped

    def test_preserves_original_score_in_before_column(self):
        df = pd.DataFrame({
            'ticker': ['X'],
            'super_score_ultimate': [70.0],
            'filter_penalty':       [20.0],
        })
        result = apply_filter_penalty(df)
        assert result['super_score_before_filters'].iloc[0] == pytest.approx(70.0)
        assert result['super_score_ultimate'].iloc[0] == pytest.approx(50.0)

    def test_no_penalty_column_treats_as_zero(self):
        df = pd.DataFrame({
            'ticker': ['X'],
            'super_score_ultimate': [60.0],
        })
        result = apply_filter_penalty(df)
        assert result['super_score_ultimate'].iloc[0] == pytest.approx(60.0)
        assert 'super_score_before_filters' in result.columns


# ── RS Line bonus ─────────────────────────────────────────────────────────────

class TestRSLineBonus:

    def test_new_high_gives_7(self):
        df = pd.DataFrame({'rs_line_at_new_high': [True, False]})
        result = compute_rs_line_bonus(df)
        assert result['rs_line_bonus'].iloc[0] == pytest.approx(7.0)
        assert result['rs_line_bonus'].iloc[1] == pytest.approx(0.0)

    def test_high_percentile_gives_3(self):
        df = pd.DataFrame({'rs_line_percentile': [80.0, 60.0]})
        result = compute_rs_line_bonus(df)
        assert result['rs_line_bonus'].iloc[0] == pytest.approx(3.0)
        assert result['rs_line_bonus'].iloc[1] == pytest.approx(0.0)

    def test_trend_up_gives_2(self):
        df = pd.DataFrame({'rs_line_trend': ['up', 'down']})
        result = compute_rs_line_bonus(df)
        assert result['rs_line_bonus'].iloc[0] == pytest.approx(2.0)
        assert result['rs_line_bonus'].iloc[1] == pytest.approx(0.0)

    def test_all_signals_compose_and_clip_at_10(self):
        """new_high(7) + high_pct(3) + up(2) = 12 → clipped to 10."""
        df = pd.DataFrame({
            'rs_line_at_new_high': [True],
            'rs_line_percentile':  [90.0],
            'rs_line_trend':       ['up'],
        })
        result = compute_rs_line_bonus(df)
        assert result['rs_line_bonus'].iloc[0] == pytest.approx(10.0)

    def test_missing_columns_tolerated(self):
        df = pd.DataFrame({'ticker': ['X']})
        result = compute_rs_line_bonus(df)
        assert result['rs_line_bonus'].iloc[0] == pytest.approx(0.0)


class TestApplyRSLineBonus:

    def test_adds_bonus_and_clips_at_100(self):
        df = pd.DataFrame({
            'ticker': ['HIGH', 'TOPPED'],
            'super_score_ultimate': [85.0, 95.0],
            'rs_line_bonus':        [10.0, 10.0],  # second would go to 105
        })
        result = apply_rs_line_bonus(df)
        assert result.loc[result['ticker'] == 'HIGH',   'super_score_ultimate'].iloc[0] == pytest.approx(95.0)
        assert result.loc[result['ticker'] == 'TOPPED', 'super_score_ultimate'].iloc[0] == pytest.approx(100.0)

    def test_no_bonus_no_change(self):
        df = pd.DataFrame({
            'ticker': ['X'],
            'super_score_ultimate': [50.0],
            'rs_line_bonus':        [0.0],
        })
        result = apply_rs_line_bonus(df)
        assert result['super_score_ultimate'].iloc[0] == pytest.approx(50.0)


# ── Integration guard: verifica que los pesos del código real coinciden ───────

class TestSourceCodeAlignment:
    """Lee super_score_integrator.py y verifica que los pesos no han cambiado."""

    def test_market_penalty_constants_in_source(self):
        from pathlib import Path
        import super_score_integrator as ssi
        src = Path(ssi.__file__).read_text()
        assert "market_penalty = 15" in src, "Market AVOID penalty cambió en source"
        assert "market_penalty = 5"  in src, "Market CAUTION penalty cambió en source"

    def test_filter_penalty_weights_in_source(self):
        from pathlib import Path
        import super_score_integrator as ssi
        src = Path(ssi.__file__).read_text()
        # A/D penalties
        assert "'STRONG_DISTRIBUTION'" in src and "+= 15" in src
        assert "'DISTRIBUTION'" in src and "+= 10" in src
        assert "'MEGA_FLOAT'" in src and "+= 3" in src

    def test_rs_line_bonus_weights_in_source(self):
        from pathlib import Path
        import super_score_integrator as ssi
        src = Path(ssi.__file__).read_text()
        assert "+= 7.0" in src, "RS Line new-high bonus (+7) cambió"
        assert "+= 3.0" in src, "RS Line percentile bonus (+3) cambió"
        assert "+= 2.0" in src, "RS Line trend bonus (+2) cambió"
        assert "clip(upper=10.0)" in src, "RS Line cap (10) cambió"
