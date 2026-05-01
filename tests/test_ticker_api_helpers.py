#!/usr/bin/env python3
"""Tests for ticker_api_helpers — the pure helpers extracted from ticker_api.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd

from ticker_api_helpers import (
    sf, sfl, safe_int, clamp, truthy, first_value, pct_from_ratio, notna_str,
    extract_jwt_sub,
    earnings_history_stats, earnings_estimate_avg, score_contribution,
)


class TestNumericCoercion:

    def test_sf_returns_float_for_valid_number(self):
        assert sf(3.14) == pytest.approx(3.14)
        assert sf('2.5') == pytest.approx(2.5)
        assert sf(0) == pytest.approx(0.0)

    def test_sf_returns_default_for_none_nan_invalid(self):
        assert sf(None) is None
        assert sf(float('nan')) is None
        assert sf('abc') is None
        assert sf(None, default=0.0) == pytest.approx(0.0)

    def test_sfl_is_alias_of_sf(self):
        assert sfl(1.5) == sf(1.5)
        assert sfl(None) is None

    def test_safe_int_parses_strings_and_floats(self):
        assert safe_int('42') == 42
        assert safe_int(3.7) == 3
        assert safe_int(None) is None
        assert safe_int(float('nan')) is None
        assert safe_int('xyz', default=0) == 0


class TestClampAndTruthy:

    def test_clamp_bounds(self):
        assert clamp(5, 0, 10) == 5
        assert clamp(-5, 0, 10) == 0
        assert clamp(15, 0, 10) == 10
        assert clamp(None, 0, 10) is None

    def test_truthy_handles_strings_and_bools(self):
        assert truthy(True) is True
        assert truthy(False) is False
        assert truthy('true') is True
        assert truthy('YES') is True
        assert truthy('si') is True
        assert truthy('1') is True
        assert truthy('0') is False
        assert truthy('no') is False
        assert truthy('') is False


class TestFirstValueAndPct:

    def test_first_value_skips_none_and_empty_strings(self):
        assert first_value(None, '', 'hello') == 'hello'
        assert first_value(None, None, 42) == 42
        assert first_value('   ', 'real') == 'real'
        assert first_value(None, None) is None

    def test_first_value_returns_first_non_empty(self):
        assert first_value(0, 1) == 0  # 0 is not None/empty string

    def test_pct_from_ratio_multiplies_by_100(self):
        assert pct_from_ratio(0.05) == pytest.approx(5.0)
        assert pct_from_ratio(0.123456) == pytest.approx(12.3)
        assert pct_from_ratio(None) is None
        assert pct_from_ratio('invalid') is None


class TestNotnaStr:

    def test_returns_string_for_valid(self):
        row = pd.Series({'name': 'Hello'})
        assert notna_str(row, 'name') == 'Hello'

    def test_returns_fallback_for_nan(self):
        row = pd.Series({'name': float('nan')})
        assert notna_str(row, 'name', fallback='DEFAULT') == 'DEFAULT'

    def test_returns_fallback_for_missing_key(self):
        row = pd.Series({'other': 'x'})
        assert notna_str(row, 'missing', fallback='NO') == 'NO'

    def test_strips_whitespace(self):
        row = pd.Series({'name': '   hello   '})
        assert notna_str(row, 'name') == 'hello'


class TestJWT:

    def test_extract_sub_from_unsigned_jwt(self):
        # JWT con payload {"sub":"user-123","aud":"test"} sin firma válida
        import jwt as pyjwt
        token = pyjwt.encode({'sub': 'user-123'}, 'secret', algorithm='HS256')
        assert extract_jwt_sub(token) == 'user-123'

    def test_invalid_token_returns_none(self):
        assert extract_jwt_sub('not.a.jwt') is None
        assert extract_jwt_sub('') is None


class TestEarningsHelpers:

    def test_earnings_history_stats_with_empty_frame(self):
        assert earnings_history_stats(None) == (None, None, 0)
        assert earnings_history_stats(pd.DataFrame()) == (None, None, 0)

    def test_earnings_history_stats_computes_beat_rate(self):
        # yfinance returns surprisePercent as decimal (0.20 = 20%) — the function × 100 internally.
        df = pd.DataFrame({
            'epsEstimate':     [1.0, 1.0, 1.0, 1.0],
            'epsActual':       [1.2, 0.9, 1.1, 1.3],
            'surprisePercent': [0.20, -0.10, 0.10, 0.30],
        })
        beat_rate, avg_surprise, total = earnings_history_stats(df)
        assert total == 4
        assert beat_rate == pytest.approx(0.75)  # 3 beats / 4
        assert avg_surprise == pytest.approx(12.5)

    def test_earnings_estimate_avg_with_missing_label(self):
        df = pd.DataFrame({'avg': [1.5]}, index=['+1q'])
        assert earnings_estimate_avg(df, '0q') is None

    def test_earnings_estimate_avg_finds_label(self):
        df = pd.DataFrame({'avg': [2.1, 1.8]}, index=['0q', '+1q'])
        assert earnings_estimate_avg(df, '0q') == pytest.approx(2.1)
        assert earnings_estimate_avg(df, '+1q') == pytest.approx(1.8)

    def test_score_contribution_skips_small_deltas(self):
        out: list[dict] = []
        score_contribution(0.5, 'trivial', out)
        assert out == []

    def test_score_contribution_appends_meaningful_delta(self):
        out: list[dict] = []
        score_contribution(3.7, 'meaningful', out)
        assert len(out) == 1
        assert out[0]['impact'] == pytest.approx(3.7)
        assert out[0]['signal'] == 'meaningful'

    def test_score_contribution_rounds_to_1_decimal(self):
        out: list[dict] = []
        score_contribution(2.567, 'desc', out)
        assert out[0]['impact'] == pytest.approx(2.6)
