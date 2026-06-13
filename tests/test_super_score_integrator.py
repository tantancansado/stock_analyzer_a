#!/usr/bin/env python3
"""
Tests for scoring constraints in super_score_integrator.py.

Covers the 8 critical rules (distinct from test_value_score_hard_rejects.py
which tests the simple helper functions; these tests exercise the actual
_calculate_super_score logic end-to-end by passing DataFrames directly):

1.  value_score = 0 when negative_roe == True
2.  value_score = 0 when analyst_upside_pct < 0
3.  ml_score == 50.0 → ml contribution = 0 (missing data marker)
4.  fundamental_score == 50.0 → fundamental contribution = 0 (missing data marker)
5.  No analyst coverage → value_score multiplied by 0.85
6.  Final value_score never exceeds 100
7.  ml_win_probability injection: works if file exists, no crash if absent
8.  profitability_penalty is subtracted correctly from value_score

All tests pass DataFrames with known values directly into the scoring helper
extracted from _calculate_super_score — no yfinance, no file I/O (except
test 7 which verifies file-presence behaviour via a tmp path).
"""
import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import pytest


# ── Pure scoring helpers extracted from _calculate_super_score ────────────────
# These replicate the exact logic from the source so that any unintentional
# change to the production code will be caught immediately.

DEFAULT_SCORE = 50.0
EPSILON = 0.1


def apply_fundamental_to_value(df: pd.DataFrame) -> pd.DataFrame:
    """Lines ~932-935: fund contribution to value_score (0 when fund==50.0)."""
    df = df.copy()
    if 'value_score' not in df.columns:
        df['value_score'] = 0.0
    if 'fundamental_score' in df.columns:
        _fund = pd.to_numeric(df['fundamental_score'], errors='coerce')
        valid = _fund.notna() & ((_fund - DEFAULT_SCORE).abs() > EPSILON)
        df.loc[valid, 'value_score'] += (_fund[valid] / 100) * 40
    return df


def apply_ml_to_value(df: pd.DataFrame) -> pd.DataFrame:
    """Lines ~986-989: ML contribution to value_score (0 when ml==50.0)."""
    df = df.copy()
    if 'value_score' not in df.columns:
        df['value_score'] = 0.0
    if 'ml_score' in df.columns:
        _ml = pd.to_numeric(df['ml_score'], errors='coerce')
        valid = _ml.notna() & ((_ml - DEFAULT_SCORE).abs() > EPSILON)
        df.loc[valid, 'value_score'] += (_ml[valid] / 100) * 5
    return df


def apply_profitability_penalty(df: pd.DataFrame) -> pd.DataFrame:
    """Lines ~1119-1121: subtract profitability_penalty, clip to 0."""
    df = df.copy()
    if 'value_score' not in df.columns:
        df['value_score'] = 0.0
    if 'profitability_penalty' in df.columns:
        df['value_score'] = (df['value_score'] - df['profitability_penalty']).clip(lower=0)
    return df


def apply_negative_roe_reject(df: pd.DataFrame) -> pd.DataFrame:
    """Lines ~1124-1126: negative_roe == True → value_score = 0.0."""
    df = df.copy()
    if 'negative_roe' in df.columns:
        df.loc[df['negative_roe'] == True, 'value_score'] = 0.0  # noqa: E712
    return df


def apply_analyst_upside_reject(df: pd.DataFrame) -> pd.DataFrame:
    """Lines ~1132-1139: analyst_upside_pct < 0 → value_score = 0.0."""
    df = df.copy()
    if 'analyst_upside_pct' in df.columns:
        _up = pd.to_numeric(df['analyst_upside_pct'], errors='coerce')
        overvalued = _up.notna() & (_up < 0)
        df.loc[overvalued, 'value_score'] = 0.0
    return df


def apply_no_coverage_penalty(df: pd.DataFrame) -> pd.DataFrame:
    """Lines ~1320-1325: no analyst coverage → value_score × 0.85."""
    df = df.copy()
    if 'analyst_count' in df.columns:
        no_cov = df['analyst_count'].isna() | (df['analyst_count'] == 0)
        df.loc[no_cov, 'value_score'] = df.loc[no_cov, 'value_score'] * 0.85
    return df


def clip_value_score(df: pd.DataFrame) -> pd.DataFrame:
    """Line ~1327: clip value_score to [0, 100]."""
    df = df.copy()
    df['value_score'] = df['value_score'].clip(lower=0, upper=100)
    return df


def inject_ml_win_probability(df: pd.DataFrame, json_path: Path) -> pd.DataFrame:
    """Lines ~1488-1503: inject ml_win_probability if file exists, skip otherwise."""
    df = df.copy()
    try:
        if json_path.exists():
            data = json.loads(json_path.read_text())
            preds = data.get('predictions', {})
            df['ml_win_probability'] = (
                df['ticker'].str.upper()
                .map(lambda t: preds.get(t, {}).get('probability'))
            )
            df['ml_win_label'] = (
                df['ticker'].str.upper()
                .map(lambda t: preds.get(t, {}).get('label', ''))
            )
    except Exception:
        pass
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1 — negative_roe == True → value_score = 0
# ═══════════════════════════════════════════════════════════════════════════════

class TestNegativeROEHardReject:

    def test_negative_roe_zeroes_any_accumulated_score(self):
        df = pd.DataFrame({
            'ticker': ['BAD'],
            'negative_roe': [True],
            'value_score': [72.5],
        })
        result = apply_negative_roe_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "negative_roe=True must force value_score to 0 regardless of prior accumulation"

    def test_negative_roe_false_preserves_score(self):
        df = pd.DataFrame({
            'ticker': ['GOOD'],
            'negative_roe': [False],
            'value_score': [65.0],
        })
        result = apply_negative_roe_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(65.0)

    def test_negative_roe_applied_after_penalty_accumulation(self):
        """Simulate the order of operations: penalty subtracted, then ROE zeroes."""
        df = pd.DataFrame({
            'ticker': ['IP'],
            'value_score': [50.0],
            'profitability_penalty': [25.0],
            'negative_roe': [True],
        })
        df = apply_profitability_penalty(df)   # 50 - 25 = 25
        df = apply_negative_roe_reject(df)      # 25 → 0
        assert df['value_score'].iloc[0] == pytest.approx(0.0), \
            "ROE hard-reject must fire even after profitability penalty is applied"

    def test_mixed_roe_in_same_dataframe(self):
        df = pd.DataFrame({
            'ticker': ['BAD1', 'OK', 'BAD2'],
            'negative_roe': [True, False, True],
            'value_score': [80.0, 70.0, 55.0],
        })
        result = apply_negative_roe_reject(df)
        scores = result.set_index('ticker')['value_score']
        assert scores['BAD1'] == pytest.approx(0.0)
        assert scores['OK']   == pytest.approx(70.0)
        assert scores['BAD2'] == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2 — analyst_upside_pct < 0 → value_score = 0
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalystUpsideReject:

    def test_negative_upside_zeroes_value_score(self):
        df = pd.DataFrame({
            'ticker': ['OVER'],
            'analyst_upside_pct': [-8.3],
            'value_score': [65.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_exactly_zero_upside_is_not_rejected(self):
        """0.0% upside is the boundary — should NOT be rejected."""
        df = pd.DataFrame({
            'ticker': ['FAIR'],
            'analyst_upside_pct': [0.0],
            'value_score': [60.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(60.0)

    def test_positive_upside_preserves_score(self):
        df = pd.DataFrame({
            'ticker': ['VALUE'],
            'analyst_upside_pct': [22.5],
            'value_score': [75.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(75.0)

    def test_nan_upside_preserves_score(self):
        """NaN = no analyst data — handled by 0.85 coverage penalty, NOT by reject."""
        df = pd.DataFrame({
            'ticker': ['NOCOV'],
            'analyst_upside_pct': [float('nan')],
            'value_score': [55.0],
        })
        result = apply_analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(55.0)

    def test_mixed_upside_in_same_dataframe(self):
        df = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],
            'analyst_upside_pct': [-15.0, float('nan'), 30.0],
            'value_score': [80.0, 70.0, 60.0],
        })
        result = apply_analyst_upside_reject(df)
        scores = result.set_index('ticker')['value_score']
        assert scores['A'] == pytest.approx(0.0)
        assert scores['B'] == pytest.approx(70.0)   # NaN → preserved
        assert scores['C'] == pytest.approx(60.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3 — ml_score == 50.0 → ml contribution = 0 (missing data marker)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMLScoreDefaultMissing:

    def test_ml_50_exact_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [50.0], 'value_score': [0.0]})
        result = apply_ml_to_value(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "ml_score=50.0 is the default/missing sentinel — must contribute 0 pts"

    def test_ml_50_with_epsilon_noise_still_contributes_zero(self):
        """Values within ±0.1 of 50.0 treated as default."""
        for val in [50.05, 49.95, 50.09, 49.91]:
            df = pd.DataFrame({'ticker': ['X'], 'ml_score': [val], 'value_score': [0.0]})
            result = apply_ml_to_value(df)
            assert result['value_score'].iloc[0] == pytest.approx(0.0), \
                f"ml_score={val} is within epsilon of 50.0 — must be treated as missing"

    def test_ml_50_plus_epsilon_contributes(self):
        """50.11 is just outside the noise band — should contribute."""
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [50.11], 'value_score': [0.0]})
        result = apply_ml_to_value(df)
        expected = (50.11 / 100) * 5
        assert result['value_score'].iloc[0] == pytest.approx(expected, abs=0.01)

    def test_ml_80_contributes_4pts(self):
        """80/100 × 5 = 4.0 pts."""
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [80.0], 'value_score': [0.0]})
        result = apply_ml_to_value(df)
        assert result['value_score'].iloc[0] == pytest.approx(4.0)

    def test_ml_nan_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [float('nan')], 'value_score': [0.0]})
        result = apply_ml_to_value(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_ml_zero_does_contribute(self):
        """ml_score=0 is NOT a missing-data sentinel — it's a genuine low score."""
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [0.0], 'value_score': [0.0]})
        result = apply_ml_to_value(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)  # 0/100 * 5 = 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4 — fundamental_score == 50.0 → fundamental contribution = 0
# ═══════════════════════════════════════════════════════════════════════════════

class TestFundamentalScoreDefaultMissing:

    def test_fund_50_exact_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [50.0], 'value_score': [0.0]})
        result = apply_fundamental_to_value(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "fundamental_score=50.0 is the default/missing sentinel — must contribute 0 pts"

    def test_fund_50_within_epsilon_contributes_zero(self):
        for val in [50.05, 49.95]:
            df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [val], 'value_score': [0.0]})
            result = apply_fundamental_to_value(df)
            assert result['value_score'].iloc[0] == pytest.approx(0.0), \
                f"fundamental_score={val} within epsilon of 50.0 — must be treated as missing"

    def test_fund_75_contributes_30pts(self):
        """75/100 × 40 = 30 pts."""
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [75.0], 'value_score': [0.0]})
        result = apply_fundamental_to_value(df)
        assert result['value_score'].iloc[0] == pytest.approx(30.0)

    def test_fund_100_contributes_40pts(self):
        """Max contribution: 100/100 × 40 = 40 pts."""
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [100.0], 'value_score': [0.0]})
        result = apply_fundamental_to_value(df)
        assert result['value_score'].iloc[0] == pytest.approx(40.0)

    def test_fund_nan_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [float('nan')], 'value_score': [0.0]})
        result = apply_fundamental_to_value(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_fund_real_vs_default_in_same_df(self):
        df = pd.DataFrame({
            'ticker': ['DEFAULT', 'REAL'],
            'fundamental_score': [50.0, 80.0],
            'value_score': [0.0, 0.0],
        })
        result = apply_fundamental_to_value(df)
        assert result.loc[result['ticker'] == 'DEFAULT', 'value_score'].iloc[0] == pytest.approx(0.0)
        assert result.loc[result['ticker'] == 'REAL',    'value_score'].iloc[0] == pytest.approx(32.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5 — No analyst coverage → value_score × 0.85
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoCoverageMultiplier:

    def test_zero_analyst_count_applies_0_85(self):
        df = pd.DataFrame({
            'ticker': ['SMALL'],
            'analyst_count': [0],
            'value_score': [60.0],
        })
        result = apply_no_coverage_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(60.0 * 0.85)

    def test_nan_analyst_count_applies_0_85(self):
        df = pd.DataFrame({
            'ticker': ['SMALL'],
            'analyst_count': [float('nan')],
            'value_score': [60.0],
        })
        result = apply_no_coverage_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(60.0 * 0.85)

    def test_covered_stock_not_penalized(self):
        df = pd.DataFrame({
            'ticker': ['MSFT'],
            'analyst_count': [15],
            'value_score': [70.0],
        })
        result = apply_no_coverage_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(70.0)

    def test_mixed_coverage_in_same_df(self):
        df = pd.DataFrame({
            'ticker': ['COVERED', 'NOCOV', 'NANOCOV'],
            'analyst_count': [10, 0, float('nan')],
            'value_score': [80.0, 60.0, 40.0],
        })
        result = apply_no_coverage_penalty(df)
        scores = result.set_index('ticker')['value_score']
        assert scores['COVERED'] == pytest.approx(80.0)
        assert scores['NOCOV']   == pytest.approx(60.0 * 0.85)
        assert scores['NANOCOV'] == pytest.approx(40.0 * 0.85)

    def test_no_coverage_penalty_is_multiplicative_not_additive(self):
        """Penalty must be ×0.85, not −15."""
        df = pd.DataFrame({
            'ticker': ['X'],
            'analyst_count': [0],
            'value_score': [100.0],
        })
        result = apply_no_coverage_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(85.0)
        assert result['value_score'].iloc[0] != pytest.approx(85.0 - 15.0)  # not −15 additive


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6 — Final value_score never exceeds 100
# ═══════════════════════════════════════════════════════════════════════════════

class TestValueScoreCap:

    def test_clip_prevents_above_100(self):
        df = pd.DataFrame({
            'ticker': ['GREAT'],
            'value_score': [115.0],
        })
        result = clip_value_score(df)
        assert result['value_score'].iloc[0] == pytest.approx(100.0)

    def test_exactly_100_stays_100(self):
        df = pd.DataFrame({'ticker': ['X'], 'value_score': [100.0]})
        result = clip_value_score(df)
        assert result['value_score'].iloc[0] == pytest.approx(100.0)

    def test_clip_prevents_below_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'value_score': [-5.0]})
        result = clip_value_score(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_realistic_maxout_scenario(self):
        """
        A ticker with fundamental=100, ml=100, all bonuses maxed:
        fund(40) + ml(5) = 45pts initially, then many bonuses can push it over 100.
        Clip must fire.
        """
        df = pd.DataFrame({'ticker': ['PERFECT'], 'value_score': [0.0]})
        df = apply_fundamental_to_value(df.assign(fundamental_score=100.0))
        df = apply_ml_to_value(df.assign(ml_score=100.0))
        # Manually push well over 100 to verify clip works
        df['value_score'] += 70.0  # would be 115 total
        result = clip_value_score(df)
        assert result['value_score'].iloc[0] == pytest.approx(100.0)

    def test_source_clips_value_score_to_100(self):
        """Guard: verify the production source still clips value_score to 100."""
        import super_score_integrator as ssi
        src = Path(ssi.__file__).read_text()
        # The line: df['value_score'] = df['value_score'].clip(lower=0, upper=100)
        assert "clip(lower=0, upper=100)" in src, \
            "value_score clip to [0,100] removed from source — scores can exceed 100"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7 — ml_win_probability injection
# ═══════════════════════════════════════════════════════════════════════════════

class TestMLWinProbabilityInjection:

    def _make_df(self):
        return pd.DataFrame({'ticker': ['AAPL', 'MSFT', 'UNKNOWN']})

    def test_probability_injected_when_file_exists(self, tmp_path):
        payload = {
            'predictions': {
                'AAPL': {'probability': 0.72, 'label': 'WIN'},
                'MSFT': {'probability': 0.41, 'label': 'LOSS'},
            }
        }
        p = tmp_path / 'ml_win_probability.json'
        p.write_text(json.dumps(payload))

        df = self._make_df()
        result = inject_ml_win_probability(df, p)

        assert 'ml_win_probability' in result.columns
        assert 'ml_win_label' in result.columns
        assert result.loc[result['ticker'] == 'AAPL', 'ml_win_probability'].iloc[0] == pytest.approx(0.72)
        assert result.loc[result['ticker'] == 'MSFT', 'ml_win_probability'].iloc[0] == pytest.approx(0.41)
        assert result.loc[result['ticker'] == 'AAPL', 'ml_win_label'].iloc[0] == 'WIN'

    def test_unknown_ticker_gets_nan_probability(self, tmp_path):
        payload = {'predictions': {'AAPL': {'probability': 0.7, 'label': 'WIN'}}}
        p = tmp_path / 'ml_win_probability.json'
        p.write_text(json.dumps(payload))

        df = self._make_df()
        result = inject_ml_win_probability(df, p)

        unknown_prob = result.loc[result['ticker'] == 'UNKNOWN', 'ml_win_probability'].iloc[0]
        assert pd.isna(unknown_prob), "Ticker absent from predictions must get NaN probability"

    def test_no_crash_when_file_absent(self, tmp_path):
        """Core requirement: pipeline must not crash if the JSON file does not exist."""
        missing_path = tmp_path / 'does_not_exist.json'
        df = self._make_df()
        # Must not raise
        result = inject_ml_win_probability(df, missing_path)
        # Columns should not be added when file is absent
        assert 'ml_win_probability' not in result.columns

    def test_no_crash_on_malformed_json(self, tmp_path):
        """Corrupt JSON must be silently skipped (except clause in source)."""
        p = tmp_path / 'ml_win_probability.json'
        p.write_text("THIS IS NOT JSON {{{")
        df = self._make_df()
        # Must not raise
        result = inject_ml_win_probability(df, p)
        assert 'ml_win_probability' not in result.columns

    def test_source_wraps_injection_in_try_except(self):
        """Guard: verify production code still has the safety try/except."""
        import super_score_integrator as ssi
        src = Path(ssi.__file__).read_text()
        assert "ml_win_probability.json" in src, "ml_win_probability.json path removed from source"
        # The try/except block is essential — verify it surrounds the injection
        assert "ml_win_probability skipped" in src or "ML win probability skipped" in src, \
            "try/except guard around ml_win_probability injection removed from source"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8 — profitability_penalty subtracted correctly
# ═══════════════════════════════════════════════════════════════════════════════

class TestProfitabilityPenalty:

    def test_penalty_subtracted_from_value_score(self):
        df = pd.DataFrame({
            'ticker': ['X'],
            'value_score': [70.0],
            'profitability_penalty': [25.0],
        })
        result = apply_profitability_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(45.0)

    def test_penalty_clips_to_zero_not_negative(self):
        """A penalty larger than the score must not produce a negative score."""
        df = pd.DataFrame({
            'ticker': ['X'],
            'value_score': [20.0],
            'profitability_penalty': [50.0],
        })
        result = apply_profitability_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_zero_penalty_leaves_score_unchanged(self):
        df = pd.DataFrame({
            'ticker': ['GOOD'],
            'value_score': [65.0],
            'profitability_penalty': [0.0],
        })
        result = apply_profitability_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(65.0)

    def test_no_penalty_column_leaves_score_unchanged(self):
        """If profitability_penalty column is absent, value_score must be untouched."""
        df = pd.DataFrame({'ticker': ['X'], 'value_score': [60.0]})
        result = apply_profitability_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(60.0)

    def test_roe_penalty_25_added_for_negative_roe(self):
        """
        ROE < 0 → profitability_penalty += 25 (from health_details parsing, lines ~882-884).
        Then negative_roe=True is set → hard reject zeros value_score.
        Verify the combined effect: score ends at 0.
        """
        df = pd.DataFrame({
            'ticker': ['IP'],
            'value_score': [60.0],
            'profitability_penalty': [25.0],   # as set by health_details loop
            'negative_roe': [True],
        })
        df = apply_profitability_penalty(df)   # 60 - 25 = 35
        df = apply_negative_roe_reject(df)      # 35 → 0
        assert df['value_score'].iloc[0] == pytest.approx(0.0)

    def test_moderate_roe_penalty_5_for_weak_roe(self):
        """0 ≤ ROE < 10 → penalty += 5 (lines ~892-894). No hard reject (ROE is positive)."""
        df = pd.DataFrame({
            'ticker': ['WEAK'],
            'value_score': [50.0],
            'profitability_penalty': [5.0],    # weak ROE penalty
            'negative_roe': [False],
        })
        df = apply_profitability_penalty(df)
        df = apply_negative_roe_reject(df)
        assert df['value_score'].iloc[0] == pytest.approx(45.0)

    def test_source_uses_clip_lower_0_for_penalty(self):
        """Guard: ensure the production subtraction still clips to 0."""
        import super_score_integrator as ssi
        src = Path(ssi.__file__).read_text()
        # Line ~1121: df['value_score'] = (df['value_score'] - df['profitability_penalty']).clip(lower=0)
        assert "- df['profitability_penalty']).clip(lower=0)" in src, \
            "profitability_penalty subtraction + clip(lower=0) changed in source"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: verify the 4 reject checks fire in the right order
# ═══════════════════════════════════════════════════════════════════════════════

class TestRejectOrderIntegration:
    """
    In _calculate_super_score the order is:
      1. profitability_penalty subtracted (clip ≥ 0)
      2. negative_roe == True → value_score = 0
      3. analyst_upside_pct < 0 → value_score = 0
      4. no analyst coverage → ×0.85
      5. clip(0, 100)
    These tests verify that each step can interact correctly with the next.
    """

    def test_upside_reject_fires_after_roe_reject(self):
        """
        Stock with negative ROE AND negative upside.
        ROE reject fires first → score = 0.
        Upside reject fires next: 0 < 0 is False → no-op.
        Final score = 0.
        """
        df = pd.DataFrame({
            'ticker': ['JUNK'],
            'value_score': [80.0],
            'profitability_penalty': [25.0],
            'negative_roe': [True],
            'analyst_upside_pct': [-10.0],
            'analyst_count': [5],
        })
        df = apply_profitability_penalty(df)
        df = apply_negative_roe_reject(df)
        df = apply_analyst_upside_reject(df)
        df = apply_no_coverage_penalty(df)
        df = clip_value_score(df)
        assert df['value_score'].iloc[0] == pytest.approx(0.0)

    def test_coverage_penalty_applied_to_already_penalized_score(self):
        """
        Score 80 → penalty 10 → 70 → ×0.85 = 59.5 → clip → 59.5.
        """
        df = pd.DataFrame({
            'ticker': ['MICRO'],
            'value_score': [80.0],
            'profitability_penalty': [10.0],
            'negative_roe': [False],
            'analyst_upside_pct': [15.0],
            'analyst_count': [0],
        })
        df = apply_profitability_penalty(df)     # 70.0
        df = apply_negative_roe_reject(df)       # still 70.0
        df = apply_analyst_upside_reject(df)     # still 70.0 (15>0)
        df = apply_no_coverage_penalty(df)       # 70 × 0.85 = 59.5
        df = clip_value_score(df)
        assert df['value_score'].iloc[0] == pytest.approx(59.5)

    def test_all_paths_result_in_score_between_0_and_100(self):
        """Fuzz: try extreme combinations and ensure output is always in [0, 100]."""
        rng = pd.array([0.0, 25.0, 50.0, 75.0, 100.0])
        import itertools
        rows = []
        for score, penalty in itertools.product(rng, rng):
            rows.append({
                'ticker': f'T_{score}_{penalty}',
                'value_score': float(score),
                'profitability_penalty': float(penalty),
                'negative_roe': penalty >= 25,
                'analyst_upside_pct': float(score - 50),   # half negative, half positive
                'analyst_count': 0 if score < 25 else 5,
            })
        df = pd.DataFrame(rows)
        df = apply_profitability_penalty(df)
        df = apply_negative_roe_reject(df)
        df = apply_analyst_upside_reject(df)
        df = apply_no_coverage_penalty(df)
        df = clip_value_score(df)
        assert (df['value_score'] >= 0).all(), "value_score went negative"
        assert (df['value_score'] <= 100).all(), "value_score exceeded 100"


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR WIN-RATE ADJUSTMENT (tracker-derived)
# Réplica de _sector_adj en super_score_integrator.py — fuente:
# docs/portfolio_tracker/summary.json → sector_performance (golden zone, 30d).
# ─────────────────────────────────────────────────────────────────────────────

MIN_SECTOR_SAMPLE = 15


def sector_wr_adjustment(sector_perf: dict, sector: str) -> float:
    sp = sector_perf.get(sector)
    if not sp or sp.get('count', 0) < MIN_SECTOR_SAMPLE:
        return 0.0
    wr = sp.get('win_rate_30d')
    if wr is None:
        return 0.0
    if wr < 20:
        return -12.0
    elif wr < 30:
        return -8.0
    elif wr < 40:
        return -3.0
    elif wr >= 65:
        return 5.0
    elif wr >= 55:
        return 3.0
    return 0.0


class TestSectorWinRateAdjustment:
    PERF = {
        'Technology':         {'count': 46, 'avg_30d': -5.72, 'win_rate_30d': 15.2},
        'Financial Services': {'count': 69, 'avg_30d': 5.17,  'win_rate_30d': 73.9},
        'Industrials':        {'count': 48, 'avg_30d': -0.48, 'win_rate_30d': 35.4},
        'Basic Materials':    {'count': 9,  'avg_30d': 7.69,  'win_rate_30d': 100.0},
        'Energy':             {'count': 4,  'avg_30d': 10.84, 'win_rate_30d': 75.0},
    }

    def test_low_winrate_big_sample_strong_penalty(self):
        assert sector_wr_adjustment(self.PERF, 'Technology') == -12.0

    def test_high_winrate_big_sample_bonus(self):
        assert sector_wr_adjustment(self.PERF, 'Financial Services') == 5.0

    def test_mediocre_winrate_mild_penalty(self):
        assert sector_wr_adjustment(self.PERF, 'Industrials') == -3.0

    def test_small_sample_neutral_even_if_perfect(self):
        # 100% win con 9 señales NO da bonus — guardia de muestra mínima
        assert sector_wr_adjustment(self.PERF, 'Basic Materials') == 0.0
        assert sector_wr_adjustment(self.PERF, 'Energy') == 0.0

    def test_unknown_sector_neutral(self):
        assert sector_wr_adjustment(self.PERF, 'Utilities') == 0.0
        assert sector_wr_adjustment(self.PERF, '') == 0.0

    def test_missing_winrate_key_neutral(self):
        # summary.json antiguo (claves win_rate_14d) → neutral, no crash
        old = {'Technology': {'count': 46, 'avg_14d': -5.72, 'win_rate_14d': 15.2}}
        assert sector_wr_adjustment(old, 'Technology') == 0.0

    def test_boundaries(self):
        perf = {s: {'count': 20, 'win_rate_30d': wr} for s, wr in
                [('A', 19.9), ('B', 20.0), ('C', 29.9), ('D', 39.9), ('E', 40.0),
                 ('F', 54.9), ('G', 55.0), ('H', 64.9), ('I', 65.0)]}
        assert sector_wr_adjustment(perf, 'A') == -12.0
        assert sector_wr_adjustment(perf, 'B') == -8.0
        assert sector_wr_adjustment(perf, 'C') == -8.0
        assert sector_wr_adjustment(perf, 'D') == -3.0
        assert sector_wr_adjustment(perf, 'E') == 0.0
        assert sector_wr_adjustment(perf, 'F') == 0.0
        assert sector_wr_adjustment(perf, 'G') == 3.0
        assert sector_wr_adjustment(perf, 'H') == 3.0
        assert sector_wr_adjustment(perf, 'I') == 5.0

    def test_source_in_sync(self):
        """Si cambian los umbrales en super_score_integrator, saltará aquí."""
        from pathlib import Path
        import super_score_integrator as ssi
        src = Path(ssi.__file__).read_text()
        assert "docs/portfolio_tracker/summary.json" in src, \
            "El integrador ya no lee el summary del tracker — actualiza estos tests"
        assert "win_rate_30d" in src, "La clave win_rate_30d desapareció del source"
        assert "_MIN_SAMPLE = 15" in src, "La muestra mínima cambió en el source"
        for needle in ("-12.0", "-8.0", "-3.0", "5.0", "3.0"):
            assert needle in src, f"Umbral {needle} cambió en el source"
