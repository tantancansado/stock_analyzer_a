#!/usr/bin/env python3
"""
Tests for the critical hard rules in FundamentalScorer and the value-scoring
logic in SuperScoreIntegrator that consumes fundamental_scorer output.

Covered rules (8 total):
  1. negative_roe == True → value_score = 0 (HARD REJECT)
  2. analyst_upside_pct < 0 → value_score = 0 (OVERVALUED)
  3. dividendYield from yfinance is already % (0.38 = 0.38%), NOT decimal
  4. ml_score == 50.0 means missing → must NOT contribute to score
  5. fundamental_score == 50.0 means missing → must NOT contribute to score
  6. profit_margin_pct lives in earnings_details, NOT health_details
  7. MA filter rate-limit failure must NOT penalize (-20pts skipped)
  8. No analyst coverage → value_score × 0.85
"""

import os
import sys
import ast
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: replicate the exact SSI scoring helpers (kept in sync via grep tests)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SCORE = 50.0
EPSILON = 0.1


def _fund_contribution(df: pd.DataFrame) -> pd.DataFrame:
    """super_score_integrator.py — fundamental contribution block."""
    df = df.copy()
    if 'value_score' not in df.columns:
        df['value_score'] = 0.0
    if 'fundamental_score' in df.columns:
        fund = pd.to_numeric(df['fundamental_score'], errors='coerce')
        valid = fund.notna() & ((fund - DEFAULT_SCORE).abs() > EPSILON)
        df.loc[valid, 'value_score'] += (df.loc[valid, 'fundamental_score'] / 100) * 40
    return df


def _ml_contribution(df: pd.DataFrame) -> pd.DataFrame:
    """super_score_integrator.py — ML contribution block."""
    df = df.copy()
    if 'value_score' not in df.columns:
        df['value_score'] = 0.0
    if 'ml_score' in df.columns:
        ml = pd.to_numeric(df['ml_score'], errors='coerce')
        valid = ml.notna() & ((ml - DEFAULT_SCORE).abs() > EPSILON)
        df.loc[valid, 'value_score'] += (df.loc[valid, 'ml_score'] / 100) * 5
    return df


def _negative_roe_reject(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'negative_roe' in df.columns:
        df.loc[df['negative_roe'] == True, 'value_score'] = 0.0  # noqa: E712
    return df


def _analyst_upside_reject(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'analyst_upside_pct' in df.columns:
        up = pd.to_numeric(df['analyst_upside_pct'], errors='coerce')
        overvalued = up.notna() & (up < 0)
        df.loc[overvalued, 'value_score'] = 0.0
    return df


def _no_analyst_coverage_penalty(df: pd.DataFrame) -> pd.DataFrame:
    """super_score_integrator.py:1319-1325 — ×0.85 when no coverage."""
    df = df.copy()
    if 'analyst_count' in df.columns:
        no_cov = df['analyst_count'].isna() | (df['analyst_count'] == 0)
        df.loc[no_cov, 'value_score'] *= 0.85
    return df


def _ma_filter_penalty(df: pd.DataFrame) -> pd.DataFrame:
    """super_score_integrator.py:555-559 — skip -20pts when rate-limited."""
    df = df.copy()
    if 'ma_filter_pass' not in df.columns:
        return df
    rate_limited = df['ma_filter_reason'].str.contains(
        'Too Many Requests|rate limit|Rate limit|429', case=False, na=False
    )
    df.loc[(df['ma_filter_pass'] == False) & (~rate_limited), 'filter_penalty'] += 20  # noqa
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Rule 1 — negative_roe == True → value_score = 0
# ─────────────────────────────────────────────────────────────────────────────

class TestNegativeROEHardReject:

    def test_negative_roe_zeroes_high_score(self):
        df = pd.DataFrame({'ticker': ['IP'], 'negative_roe': [True], 'value_score': [80.0]})
        result = _negative_roe_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "negative_roe=True must force value_score=0 regardless of accumulated points"

    def test_negative_roe_zeroes_low_score(self):
        df = pd.DataFrame({'ticker': ['X'], 'negative_roe': [True], 'value_score': [10.0]})
        result = _negative_roe_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_positive_roe_preserves_score(self):
        df = pd.DataFrame({'ticker': ['MSFT'], 'negative_roe': [False], 'value_score': [75.0]})
        result = _negative_roe_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(75.0)

    def test_mixed_portfolio_selective_reject(self):
        df = pd.DataFrame({
            'ticker':       ['BAD', 'GOOD', 'BAD2', 'GOOD2'],
            'negative_roe': [True,  False,  True,   False],
            'value_score':  [60.0,  70.0,   45.0,   80.0],
        })
        result = _negative_roe_reject(df)
        assert result.loc[result.ticker == 'BAD',   'value_score'].iloc[0] == 0.0
        assert result.loc[result.ticker == 'BAD2',  'value_score'].iloc[0] == 0.0
        assert result.loc[result.ticker == 'GOOD',  'value_score'].iloc[0] == 70.0
        assert result.loc[result.ticker == 'GOOD2', 'value_score'].iloc[0] == 80.0

    def test_negative_roe_flag_set_from_health_details(self):
        """Integration: super_score_integrator reads roe_pct from health_details."""
        import super_score_integrator as ssi
        src = __import__('pathlib').Path(ssi.__file__).read_text()
        # Verify the flag assignment line is present in source
        assert "df.at[idx, 'negative_roe'] = True" in src, \
            "Hard-reject flag assignment for negative_roe removed from SSI source"

    def test_roe_read_from_health_details_not_earnings_details(self):
        """
        The SSI reads roe_pct from health_details, NOT earnings_details.
        This test guards against accidentally moving the key to the wrong dict.
        """
        import super_score_integrator as ssi
        src = __import__('pathlib').Path(ssi.__file__).read_text()
        # health.get('roe_pct') must be present (the correct lookup)
        assert "health.get('roe_pct'" in src, \
            "roe_pct must be read from health_details, not earnings_details"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 2 — analyst_upside_pct < 0 → value_score = 0
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalystUpsideOvervalued:

    def test_negative_upside_zeroes_score(self):
        df = pd.DataFrame({
            'ticker': ['OVERPRICED'], 'analyst_upside_pct': [-12.5], 'value_score': [75.0]
        })
        result = _analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_zero_upside_is_not_rejected(self):
        """Exactly 0% upside: analyst says fair value, not overvalued → no reject."""
        df = pd.DataFrame({
            'ticker': ['FAIR'], 'analyst_upside_pct': [0.0], 'value_score': [60.0]
        })
        result = _analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(60.0)

    def test_positive_upside_preserves_score(self):
        df = pd.DataFrame({
            'ticker': ['UNDERV'], 'analyst_upside_pct': [20.0], 'value_score': [70.0]
        })
        result = _analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(70.0)

    def test_nan_upside_preserves_score(self):
        """NaN = no analyst data — penalised separately via ×0.85 rule, not zeroed."""
        df = pd.DataFrame({
            'ticker': ['NOCOV'], 'analyst_upside_pct': [float('nan')], 'value_score': [60.0]
        })
        result = _analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(60.0)

    def test_very_negative_upside_still_zeroes(self):
        df = pd.DataFrame({
            'ticker': ['TANK'], 'analyst_upside_pct': [-50.0], 'value_score': [50.0]
        })
        result = _analyst_upside_reject(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_source_contains_reject_logic(self):
        import super_score_integrator as ssi
        src = __import__('pathlib').Path(ssi.__file__).read_text()
        assert "df['analyst_upside_pct'] < 0" in src or \
               "(_up < 0)" in src, \
            "Analyst upside < 0 reject logic not found in SSI source"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 3 — dividendYield is already % (0.38 = 0.38%), NOT decimal
# ─────────────────────────────────────────────────────────────────────────────

class TestDividendYieldHandling:

    def _make_scorer(self):
        """Return FundamentalScorer with no yfinance I/O."""
        from fundamental_scorer import FundamentalScorer
        return FundamentalScorer()

    def test_dividend_yield_stored_as_is_not_multiplied(self):
        """
        yfinance dividendYield = 0.38 means 0.38%, not 38%.
        The scorer must store 0.38 directly, NOT multiply by 100.
        """
        scorer = self._make_scorer()
        mock_stock = MagicMock()
        mock_stock.quarterly_cashflow = pd.DataFrame()
        mock_stock.quarterly_financials = pd.DataFrame()
        mock_stock.earnings_dates = None

        info = {
            'currentPrice': 100.0,
            'marketCap': 10_000_000_000,
            'sharesOutstanding': 100_000_000,
            'dividendYield': 0.38,   # yfinance already in % (0.38%)
            'payoutRatio': 0.30,
            'freeCashflow': None,
        }
        result = scorer._calculate_value_quality_metrics(mock_stock, info)
        # Must be stored as 0.38, NOT 38.0
        assert result['dividend_yield_pct'] == pytest.approx(0.38), \
            "dividendYield must be stored as-is (already %). Got: " \
            f"{result['dividend_yield_pct']} — did someone multiply by 100?"

    def test_dividend_yield_not_treated_as_decimal(self):
        """Confirm no ×100 multiplication occurs in the code."""
        from pathlib import Path
        import fundamental_scorer as fs_mod
        src = Path(fs_mod.__file__).read_text()
        # Find the dividendYield assignment section
        # There must NOT be a pattern like: div_yield * 100 near dividendYield
        lines = src.split('\n')
        for i, line in enumerate(lines):
            if 'dividend_yield_pct' in line and '* 100' in line and 'dividendYield' in '\n'.join(lines[max(0,i-5):i+3]):
                pytest.fail(
                    f"Line {i+1} multiplies dividend_yield_pct by 100 — "
                    "yfinance dividendYield is already in %!"
                )

    def test_payout_ratio_is_multiplied_by_100(self):
        """payoutRatio from yfinance IS a decimal (0.30 = 30%) — must be ×100."""
        scorer = self._make_scorer()
        mock_stock = MagicMock()
        mock_stock.quarterly_cashflow = pd.DataFrame()
        mock_stock.quarterly_financials = pd.DataFrame()
        mock_stock.earnings_dates = None

        info = {
            'currentPrice': 100.0,
            'marketCap': 10_000_000_000,
            'payoutRatio': 0.35,   # 35% payout as decimal
            'dividendYield': 1.5,
            'freeCashflow': None,
        }
        result = scorer._calculate_value_quality_metrics(mock_stock, info)
        assert result['payout_ratio_pct'] == pytest.approx(35.0), \
            "payoutRatio=0.35 should be stored as 35.0 (×100). Got: " \
            f"{result['payout_ratio_pct']}"

    def test_zero_dividend_yield_stored_as_none(self):
        """Stocks with no dividend should return None, not 0."""
        scorer = self._make_scorer()
        mock_stock = MagicMock()
        mock_stock.quarterly_cashflow = pd.DataFrame()
        mock_stock.quarterly_financials = pd.DataFrame()
        mock_stock.earnings_dates = None

        info = {
            'currentPrice': 100.0,
            'marketCap': 10_000_000_000,
            'dividendYield': 0,     # no dividend
            'freeCashflow': None,
        }
        result = scorer._calculate_value_quality_metrics(mock_stock, info)
        assert result['dividend_yield_pct'] is None, \
            "Zero dividendYield should result in None, not 0"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 4 — ml_score == 50.0 means missing → contributes 0 pts
# ─────────────────────────────────────────────────────────────────────────────

class TestMLScoreDefaultMissing:

    def test_ml_50_exact_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [50.0], 'value_score': [0.0]})
        result = _ml_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "ml_score=50.0 is a default/missing marker — must contribute 0pts"

    def test_ml_50_with_epsilon_noise_still_zero(self):
        """50.05 is within epsilon of 50.0 — still treated as default."""
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [50.05], 'value_score': [0.0]})
        result = _ml_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_ml_80_contributes_4pts(self):
        """80/100 × 5pts max = 4.0pts"""
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [80.0], 'value_score': [0.0]})
        result = _ml_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(4.0)

    def test_ml_nan_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [float('nan')], 'value_score': [0.0]})
        result = _ml_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_ml_100_contributes_5pts(self):
        df = pd.DataFrame({'ticker': ['X'], 'ml_score': [100.0], 'value_score': [0.0]})
        result = _ml_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(5.0)

    def test_source_epsilon_threshold(self):
        import super_score_integrator as ssi
        src = __import__('pathlib').Path(ssi.__file__).read_text()
        assert "(df['_ml'] - 50.0).abs() > 0.1" in src, \
            "ML default-detection threshold changed in SSI source"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 5 — fundamental_score == 50.0 means missing → contributes 0 pts
# ─────────────────────────────────────────────────────────────────────────────

class TestFundamentalScoreDefaultMissing:

    def test_fund_50_exact_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [50.0], 'value_score': [0.0]})
        result = _fund_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0), \
            "fundamental_score=50.0 is default/missing — must contribute 0pts"

    def test_fund_50_epsilon_noise_still_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [50.09], 'value_score': [0.0]})
        result = _fund_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_fund_75_contributes_30pts(self):
        """75/100 × 40pts max = 30.0pts"""
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [75.0], 'value_score': [0.0]})
        result = _fund_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(30.0)

    def test_fund_nan_contributes_zero(self):
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [float('nan')], 'value_score': [0.0]})
        result = _fund_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_fund_100_contributes_40pts(self):
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [100.0], 'value_score': [0.0]})
        result = _fund_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(40.0)

    def test_fund_0_contributes_0pts(self):
        """fund=0 is a real score (error/empty result) but contributes 0 to value_score."""
        df = pd.DataFrame({'ticker': ['X'], 'fundamental_score': [0.0], 'value_score': [0.0]})
        result = _fund_contribution(df)
        assert result['value_score'].iloc[0] == pytest.approx(0.0)

    def test_source_epsilon_threshold(self):
        import super_score_integrator as ssi
        src = __import__('pathlib').Path(ssi.__file__).read_text()
        assert "(df['_fund'] - 50.0).abs() > 0.1" in src, \
            "Fundamental default-detection threshold changed in SSI source"

    def test_get_empty_result_returns_zero_not_50(self):
        """_get_empty_result must return fundamental_score=0.0, NOT 50.0.
        50.0 would look like missing data and be silently ignored."""
        from fundamental_scorer import FundamentalScorer
        scorer = FundamentalScorer()
        empty = scorer._get_empty_result('FAKE')
        assert empty['fundamental_score'] == pytest.approx(0.0), \
            "_get_empty_result must return 0.0, not 50.0 (50.0 = missing data marker)"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 6 — profit_margin_pct lives in earnings_details, NOT health_details
# ─────────────────────────────────────────────────────────────────────────────

class TestProfitMarginKeyLocation:

    def test_earnings_quality_score_puts_profit_margin_in_details(self):
        """
        _calculate_earnings_quality_score stores profit_margin_pct in its
        'details' dict, which becomes earnings_details in the final result.
        """
        from fundamental_scorer import FundamentalScorer
        scorer = FundamentalScorer()

        # Minimal quarterly earnings DataFrame
        earnings_df = pd.DataFrame({'Earnings': [1e9, 0.8e9, 0.9e9, 0.85e9]})

        info = {
            'profitMargins': 0.25,  # 25% profit margin
        }
        result = scorer._calculate_earnings_quality_score(earnings_df, info)
        assert 'profit_margin_pct' in result['details'], \
            "profit_margin_pct must be in earnings_details dict (not health_details)"
        assert result['details']['profit_margin_pct'] == pytest.approx(25.0)

    def test_financial_health_score_does_not_contain_profit_margin(self):
        """
        _calculate_financial_health_score's details go into health_details.
        profit_margin_pct must NOT be there.
        """
        from fundamental_scorer import FundamentalScorer
        scorer = FundamentalScorer()

        info = {
            'returnOnEquity': 0.20,
            'debtToEquity': 40.0,
            'currentRatio': 2.0,
            'operatingMargins': 0.18,
            # No profitMargins key here intentionally
        }
        result = scorer._calculate_financial_health_score({'quarterly_financials': pd.DataFrame(), 'quarterly_balance_sheet': pd.DataFrame()}, info)
        assert 'profit_margin_pct' not in result['details'], \
            "profit_margin_pct must NOT be in health_details"

    def test_score_ticker_result_has_profit_margin_in_earnings_details(self):
        """
        Integration: the assembled result dict puts profit_margin_pct under
        earnings_details key, not health_details.
        """
        from fundamental_scorer import FundamentalScorer
        scorer = FundamentalScorer()

        # Mock a minimal score_ticker call without network I/O
        mock_earnings = {'score': 70.0, 'details': {'profit_margin_pct': 22.5},
                         'eps_growth_yoy': None, 'eps_accelerating': None, 'eps_accel_quarters': 0}
        mock_growth   = {'score': 60.0, 'details': {}, 'rev_growth_yoy': None,
                         'rev_accelerating': None, 'rev_accel_quarters': 0}
        mock_rs       = {'score': 55.0, 'details': {},
                         'rs_line_score': None, 'rs_line_percentile': None,
                         'rs_line_at_new_high': None, 'rs_line_trend': None}
        mock_health   = {'score': 65.0, 'details': {'roe_pct': 20.0, 'operating_margin_pct': 18.0}}
        mock_catalyst = {'score': 50.0, 'details': {}}

        info = {'shortName': 'TestCo', 'currentPrice': 50.0, 'regularMarketPrice': 50.0,
                'marketCap': 1e10, 'sector': 'Tech', 'industry': 'Software',
                'fiftyTwoWeekHigh': 60.0, 'fiftyTwoWeekLow': 30.0,
                'shortPercentOfFloat': None, 'shortRatio': None}

        with patch.object(scorer, '_calculate_earnings_quality_score', return_value=mock_earnings), \
             patch.object(scorer, '_calculate_growth_acceleration_score', return_value=mock_growth), \
             patch.object(scorer, '_calculate_relative_strength_score', return_value=mock_rs), \
             patch.object(scorer, '_calculate_financial_health_score', return_value=mock_health), \
             patch.object(scorer, '_calculate_catalyst_timing_score', return_value=mock_catalyst), \
             patch.object(scorer, '_calculate_value_quality_metrics',
                          return_value={k: None for k in ['fcf_yield_pct', 'fcf_per_share',
                                        'dividend_yield_pct', 'payout_ratio_pct', 'dividend_rate',
                                        'five_yr_avg_dividend_yield_pct', 'buyback_active',
                                        'shares_change_pct', 'interest_coverage',
                                        'analyst_revision_momentum', 'days_to_earnings',
                                        'earnings_date', 'earnings_warning', 'earnings_catalyst']}), \
             patch.object(scorer, '_calculate_piotroski_fscore',
                          return_value={'piotroski_score': None, 'piotroski_label': None}), \
             patch.object(scorer, '_calculate_magic_formula_metrics',
                          return_value={'ebit_ev_yield': None, 'roic_greenblatt': None, 'peg_ratio': None}), \
             patch.object(scorer, '_calculate_iv_metrics',
                          return_value={'hv_30d': None, 'atm_iv': None, 'iv_ratio': None, 'iv_premium_pts': None}), \
             patch.object(scorer, '_calculate_target_prices',
                          return_value={k: None for k in ['target_price_analyst', 'target_price_analyst_high',
                                        'target_price_analyst_low', 'analyst_count', 'analyst_recommendation',
                                        'analyst_upside_pct', 'target_price_dcf', 'target_price_dcf_upside_pct',
                                        'target_price_pe', 'target_price_pe_upside_pct']}), \
             patch('fundamental_scorer._yf_ticker_with_retry') as mock_yf, \
             patch('fundamental_scorer._yf_info_with_retry', return_value=info), \
             patch.object(scorer, '_get_quarterly_earnings', return_value=pd.DataFrame()), \
             patch.object(scorer, '_get_financials',
                          return_value={'quarterly_financials': pd.DataFrame(),
                                        'quarterly_balance_sheet': pd.DataFrame()}), \
             patch.object(scorer, '_get_price_history', return_value=pd.DataFrame()):

            result = scorer.score_ticker('TEST')

        # earnings_details must have profit_margin_pct
        assert 'profit_margin_pct' in result['earnings_details'], \
            "profit_margin_pct must be in earnings_details"
        # health_details must NOT have profit_margin_pct
        assert 'profit_margin_pct' not in result['health_details'], \
            "profit_margin_pct must NOT be in health_details"

    def test_ssi_reads_profit_margin_from_earnings_details(self):
        """
        The super_score_integrator must look up profit_margin_pct in
        earnings_details, NOT health_details.
        """
        import super_score_integrator as ssi
        src = __import__('pathlib').Path(ssi.__file__).read_text()
        assert "earnings.get('profit_margin_pct'" in src, \
            "SSI must read profit_margin_pct from earnings_details"

    def test_ssi_has_comment_documenting_correct_location(self):
        """Guard: ensure the warning comment about the key location is still present."""
        import super_score_integrator as ssi
        src = __import__('pathlib').Path(ssi.__file__).read_text()
        # Either the comment or the pattern it guards is proof of awareness
        assert "earnings_details" in src and "health_details" in src, \
            "SSI must reference both earnings_details and health_details (key-location awareness)"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 7 — MA filter rate-limit failure must NOT penalize (-20pts skipped)
# ─────────────────────────────────────────────────────────────────────────────

class TestMAFilterRateLimitSkip:

    def _make_df(self, ma_pass, ma_reason):
        return pd.DataFrame({
            'ticker': ['X'],
            'ma_filter_pass': [ma_pass],
            'ma_filter_reason': [ma_reason],
            'filter_penalty': [0.0],
        })

    def test_rate_limit_failure_no_penalty(self):
        df = self._make_df(False, 'Too Many Requests')
        result = _ma_filter_penalty(df)
        assert result['filter_penalty'].iloc[0] == pytest.approx(0.0), \
            "Rate-limited MA fail must NOT add -20pts penalty"

    def test_429_error_no_penalty(self):
        df = self._make_df(False, '429 Too Many Requests from yfinance')
        result = _ma_filter_penalty(df)
        assert result['filter_penalty'].iloc[0] == pytest.approx(0.0)

    def test_rate_limit_lowercase_no_penalty(self):
        df = self._make_df(False, 'rate limit exceeded, backoff 30s')
        result = _ma_filter_penalty(df)
        assert result['filter_penalty'].iloc[0] == pytest.approx(0.0)

    def test_real_failure_adds_20pts_penalty(self):
        """A genuine MA fail (not rate-limited) must still add the 20pt penalty."""
        df = self._make_df(False, 'Price below 200MA')
        result = _ma_filter_penalty(df)
        assert result['filter_penalty'].iloc[0] == pytest.approx(20.0), \
            "Real MA filter failure must add 20pts penalty"

    def test_ma_pass_adds_no_penalty(self):
        df = self._make_df(True, 'Passed all MA criteria')
        result = _ma_filter_penalty(df)
        assert result['filter_penalty'].iloc[0] == pytest.approx(0.0)

    def test_empty_reason_on_fail_adds_penalty(self):
        """No reason provided on fail = not rate-limited → penalize."""
        df = self._make_df(False, '')
        result = _ma_filter_penalty(df)
        assert result['filter_penalty'].iloc[0] == pytest.approx(20.0)

    def test_source_skips_rate_limit_pattern(self):
        import super_score_integrator as ssi
        src = __import__('pathlib').Path(ssi.__file__).read_text()
        assert 'Too Many Requests' in src and 'rate_limited' in src, \
            "SSI source must contain rate-limit exclusion logic for MA filter"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 8 — No analyst coverage → value_score × 0.85
# ─────────────────────────────────────────────────────────────────────────────

class TestNoCoverageAnalystPenalty:

    def test_null_analyst_count_reduces_score_15pct(self):
        df = pd.DataFrame({
            'ticker': ['NOCOV'], 'analyst_count': [None], 'value_score': [60.0]
        })
        result = _no_analyst_coverage_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(51.0), \
            "No analyst coverage must reduce value_score by 15% (×0.85)"

    def test_zero_analyst_count_reduces_score_15pct(self):
        df = pd.DataFrame({
            'ticker': ['NOCOV'], 'analyst_count': [0], 'value_score': [60.0]
        })
        result = _no_analyst_coverage_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(51.0)

    def test_one_analyst_preserves_score(self):
        """Even 1 analyst = has coverage — no penalty."""
        df = pd.DataFrame({
            'ticker': ['COVERED'], 'analyst_count': [1], 'value_score': [60.0]
        })
        result = _no_analyst_coverage_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(60.0)

    def test_many_analysts_preserves_score(self):
        df = pd.DataFrame({
            'ticker': ['COVERED'], 'analyst_count': [15], 'value_score': [80.0]
        })
        result = _no_analyst_coverage_penalty(df)
        assert result['value_score'].iloc[0] == pytest.approx(80.0)

    def test_mixed_coverage(self):
        df = pd.DataFrame({
            'ticker':        ['COV', 'NOCOV', 'ZERO'],
            'analyst_count': [10,    None,    0],
            'value_score':   [70.0,  60.0,   50.0],
        })
        result = _no_analyst_coverage_penalty(df)
        assert result.loc[result.ticker == 'COV',   'value_score'].iloc[0] == pytest.approx(70.0)
        assert result.loc[result.ticker == 'NOCOV', 'value_score'].iloc[0] == pytest.approx(51.0)
        assert result.loc[result.ticker == 'ZERO',  'value_score'].iloc[0] == pytest.approx(42.5)

    def test_source_contains_085_multiplier(self):
        import super_score_integrator as ssi
        src = __import__('pathlib').Path(ssi.__file__).read_text()
        assert '0.85' in src, \
            "SSI source must contain the 0.85 penalty for no analyst coverage"


# ─────────────────────────────────────────────────────────────────────────────
# Integration: all rules interact correctly on the same DataFrame
# ─────────────────────────────────────────────────────────────────────────────

class TestCombinedRules:

    def test_negative_roe_overrides_good_fundamentals(self):
        """Even fund=90 + ml=90 can't save a negative_roe ticker."""
        df = pd.DataFrame({
            'ticker':          ['BADROE'],
            'fundamental_score': [90.0],
            'ml_score':        [90.0],
            'negative_roe':    [True],
            'analyst_upside_pct': [25.0],
            'analyst_count':   [10],
            'value_score':     [0.0],
        })
        df = _fund_contribution(df)
        df = _ml_contribution(df)
        df = _negative_roe_reject(df)
        assert df['value_score'].iloc[0] == pytest.approx(0.0), \
            "negative_roe must trump all positive contributions"

    def test_negative_upside_overrides_good_fundamentals(self):
        """Analyst says stock is overvalued → always reject from VALUE."""
        df = pd.DataFrame({
            'ticker':          ['OVERVAL'],
            'fundamental_score': [85.0],
            'ml_score':        [80.0],
            'negative_roe':    [False],
            'analyst_upside_pct': [-5.0],
            'analyst_count':   [8],
            'value_score':     [0.0],
        })
        df = _fund_contribution(df)
        df = _ml_contribution(df)
        df = _negative_roe_reject(df)
        df = _analyst_upside_reject(df)
        assert df['value_score'].iloc[0] == pytest.approx(0.0), \
            "analyst_upside_pct < 0 must zero the score even with strong fundamentals"

    def test_default_scores_dont_inflate_no_coverage(self):
        """
        A ticker with default fundamental (50) + default ml (50) + no analyst
        coverage should end up with ~0 value_score after penalties.
        """
        df = pd.DataFrame({
            'ticker':          ['GHOST'],
            'fundamental_score': [50.0],   # default
            'ml_score':        [50.0],     # default
            'negative_roe':    [False],
            'analyst_upside_pct': [float('nan')],
            'analyst_count':   [None],
            'value_score':     [0.0],
        })
        df = _fund_contribution(df)
        df = _ml_contribution(df)
        df = _negative_roe_reject(df)
        df = _analyst_upside_reject(df)
        df = _no_analyst_coverage_penalty(df)
        # fund=50 → 0pts, ml=50 → 0pts, no coverage → ×0.85 on 0 = still 0
        assert df['value_score'].iloc[0] == pytest.approx(0.0), \
            "Default scores + no coverage = 0 (nothing real to reward)"

    def test_strong_ticker_full_pipeline(self):
        """
        fund=80, ml=75, positive roe, 20% upside, 10 analysts:
        value_score = (80/100)*40 + (75/100)*5 = 32 + 3.75 = 35.75
        No rejections or penalties.
        """
        df = pd.DataFrame({
            'ticker':          ['GOOD'],
            'fundamental_score': [80.0],
            'ml_score':        [75.0],
            'negative_roe':    [False],
            'analyst_upside_pct': [20.0],
            'analyst_count':   [10],
            'value_score':     [0.0],
        })
        df = _fund_contribution(df)
        df = _ml_contribution(df)
        df = _negative_roe_reject(df)
        df = _analyst_upside_reject(df)
        df = _no_analyst_coverage_penalty(df)
        assert df['value_score'].iloc[0] == pytest.approx(35.75)
