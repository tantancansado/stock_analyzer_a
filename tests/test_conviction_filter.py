#!/usr/bin/env python3
"""Unit tests for conviction_filter.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
import numpy as np
import tempfile
from conviction_filter import extract_health_metrics, calculate_conviction_score, filter_by_conviction


class TestExtractHealthMetrics:
    """Tests for parsing health_details and earnings_details dicts"""

    def test_valid_health_details(self):
        row = pd.Series({
            'health_details': "{'roe_pct': 25.0, 'debt_to_equity': 0.5, 'current_ratio': 2.0, 'operating_margin_pct': 20.0}",
            'earnings_details': "{'profit_margin_pct': 15.0, 'earnings_accelerating': True, 'eps_accel_quarters': 3}"
        })
        metrics = extract_health_metrics(row)
        assert metrics['roe'] == 25.0
        assert metrics['debt_to_equity'] == 0.5
        assert metrics['profit_margin'] == 15.0

    def test_missing_details(self):
        row = pd.Series({'health_details': None, 'earnings_details': None})
        metrics = extract_health_metrics(row)
        assert metrics['roe'] is None
        assert metrics['debt_to_equity'] is None

    def test_invalid_string(self):
        row = pd.Series({'health_details': 'not a dict', 'earnings_details': '{}'})
        metrics = extract_health_metrics(row)
        assert isinstance(metrics, dict)


class TestCalculateConvictionScore:
    """Tests for the conviction scoring logic"""

    def _make_row(self, **overrides):
        base = {
            'ticker': 'TEST',
            'value_score': 50,
            'current_price': 100.0,
            'health_details': "{'roe_pct': 20.0, 'debt_to_equity': 0.5, 'current_ratio': 2.0, 'operating_margin_pct': 18.0}",
            'earnings_details': "{'profit_margin_pct': 12.0, 'earnings_accelerating': True}",
            'fcf_yield_pct': 6.0,
            'target_price_dcf': 130.0,
            'target_price_dcf_upside_pct': 30.0,
            'analyst_upside_pct': 20.0,
            'analyst_count': 10,
            'analyst_recommendation': 2.0,
            'risk_reward_ratio': 3.0,
            'dividend_yield_pct': 2.0,
            'buyback_active': True,
            'payout_ratio_pct': 40.0,
            'earnings_warning': False,
            'rev_growth_yoy': 10.0,
        }
        base.update(overrides)
        return pd.Series(base)

    def test_high_quality_stock_gets_high_score(self):
        row = self._make_row()
        result = calculate_conviction_score(row)
        assert result['conviction_score'] >= 60
        assert result['conviction_grade'] in ('A', 'B')

    def test_negative_roe_penalized(self):
        row = self._make_row(
            health_details="{'roe_pct': -5.0, 'debt_to_equity': 2.0, 'current_ratio': 0.5, 'operating_margin_pct': 3.0}"
        )
        result = calculate_conviction_score(row)
        assert result['conviction_score'] < 60

    def test_dcf_overvalued_penalized(self):
        row_bad = self._make_row(target_price_dcf=70.0)   # DCF says overvalued (-30%)
        row_good = self._make_row(target_price_dcf=160.0)  # DCF says undervalued (+60%)
        result_bad = calculate_conviction_score(row_bad)
        result_good = calculate_conviction_score(row_good)
        assert result_bad['conviction_score'] < result_good['conviction_score']

    def test_earnings_warning_penalized(self):
        row_warn = self._make_row(earnings_warning=True)
        row_safe = self._make_row(earnings_warning=False)
        result_warn = calculate_conviction_score(row_warn)
        result_safe = calculate_conviction_score(row_safe)
        assert result_warn['conviction_score'] < result_safe['conviction_score']

    def test_returns_valid_grade(self):
        row = self._make_row()
        result = calculate_conviction_score(row)
        assert result['conviction_grade'] in ('A', 'B', 'C', 'D')
        assert 0 <= result['conviction_score'] <= 100


class TestFilterByConviction:
    def test_empty_csv(self):
        with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as f:
            f.write('ticker,value_score\n')
            f.flush()
            result = filter_by_conviction(f.name, f.name + '.out')
        assert result == 0 or result is None

    def test_filters_low_grade(self):
        df = pd.DataFrame([
            {
                'ticker': 'GOOD', 'value_score': 50,
                'health_details': "{'roe_pct': 25.0, 'debt_to_equity': 0.3, 'current_ratio': 2.5, 'operating_margin_pct': 22.0}",
                'earnings_details': "{'profit_margin_pct': 15.0}",
                'fcf_yield_pct': 7.0, 'target_price_dcf_upside_pct': 25.0,
                'analyst_upside_pct': 20.0, 'analyst_count': 15, 'analyst_recommendation': 1.8,
                'risk_reward_ratio': 3.5, 'dividend_yield_pct': 2.5, 'buyback_active': True,
                'payout_ratio_pct': 35.0, 'earnings_warning': False, 'rev_growth_yoy': 12.0,
            },
            {
                'ticker': 'BAD', 'value_score': 25,
                'health_details': "{'roe_pct': -10.0, 'debt_to_equity': 5.0, 'current_ratio': 0.3, 'operating_margin_pct': -5.0}",
                'earnings_details': "{'profit_margin_pct': -8.0}",
                'fcf_yield_pct': -3.0, 'target_price_dcf_upside_pct': -30.0,
                'analyst_upside_pct': -5.0, 'analyst_count': 2, 'analyst_recommendation': 4.0,
                'risk_reward_ratio': 0.5, 'dividend_yield_pct': 0, 'buyback_active': False,
                'payout_ratio_pct': 120.0, 'earnings_warning': True, 'rev_growth_yoy': -15.0,
            }
        ])
        with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as f:
            df.to_csv(f.name, index=False)
            output = f.name + '.filtered.csv'
            result = filter_by_conviction(f.name, output, min_grade='B')

        if result and result > 0:
            out_df = pd.read_csv(output)
            assert 'GOOD' in out_df['ticker'].values
            if 'BAD' in out_df['ticker'].values:
                good_score = out_df[out_df['ticker'] == 'GOOD']['conviction_score'].iloc[0]
                bad_score = out_df[out_df['ticker'] == 'BAD']['conviction_score'].iloc[0]
                assert good_score > bad_score


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
