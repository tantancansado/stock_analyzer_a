#!/usr/bin/env python3
"""Tests del guard de integridad — casos reales que llegaron a producción."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_integrity import check_row, filter_dataframe


def _ok_row(**over):
    row = {'ticker': 'MCO', 'current_price': 478.38, 'value_score': 69.5,
           'analyst_upside_pct': 16.8, 'fcf_yield_pct': 3.11,
           'target_price_dcf_upside_pct': 32.0, 'piotroski_score': 8.0}
    row.update(over)
    return row


class TestCheckRow:
    def test_clean_row_passes(self):
        assert check_row(_ok_row())['ok'] is True

    def test_atlky_fcf_yield_blocked(self):
        # 3-ago-2026: FCF en SEK contra market cap en USD → 25.05%
        res = check_row(_ok_row(ticker='ATLKY', fcf_yield_pct=25.05))
        assert res['ok'] is False
        assert any(i['field'] == 'fcf_yield_pct' for i in res['blocking'])

    def test_asazy_extreme_fcf_blocked(self):
        assert check_row(_ok_row(fcf_yield_pct=44.76))['ok'] is False

    def test_broken_dcf_blocked(self):
        # ATLKY daba +568.9% de upside por DCF
        assert check_row(_ok_row(target_price_dcf_upside_pct=568.9))['ok'] is False

    def test_missing_price_blocked(self):
        assert check_row(_ok_row(current_price=None))['ok'] is False

    def test_unreliable_fx_blocked(self):
        assert check_row(_ok_row(fx_reliable=False))['ok'] is False

    def test_dividend_yield_scaling_error_blocked(self):
        # yfinance ya da el dividendo en % (0.38 = 0.38%). Tratarlo como decimal
        # y multiplicar por 100 dispara el valor fuera de lo posible.
        assert check_row(_ok_row(dividend_yield_pct=4.2))['ok'] is True
        assert check_row(_ok_row(dividend_yield_pct=38.0))['ok'] is False

    def test_warn_does_not_block(self):
        res = check_row(_ok_row(peg_ratio=0.07))
        assert res['ok'] is True
        assert any(i['severity'] == 'WARN' for i in res['issues'])

    def test_missing_optional_field_is_not_an_error(self):
        row = _ok_row()
        row.pop('fcf_yield_pct')
        assert check_row(row)['ok'] is True

    def test_nan_is_treated_as_missing(self):
        assert check_row(_ok_row(peg_ratio=float('nan')))['ok'] is True


class TestFilterDataframe:
    def test_blocks_only_the_bad_rows(self):
        df = pd.DataFrame([
            _ok_row(ticker='MCO'),
            _ok_row(ticker='ATLKY', fcf_yield_pct=25.05),
            _ok_row(ticker='UNH', fcf_yield_pct=6.05),
        ])
        out, report = filter_dataframe(df)
        assert list(out['ticker']) == ['MCO', 'UNH']
        assert report['blocked'] == 1
        assert report['detail'][0]['ticker'] == 'ATLKY'

    def test_empty_dataframe_is_safe(self):
        out, report = filter_dataframe(pd.DataFrame())
        assert report['checked'] == 0

    def test_bounce_rows_skip_value_requirements(self):
        # Un setup de rebote no tiene value_score y no por eso es inválido
        df = pd.DataFrame([{'ticker': 'LIN', 'current_price': 478.38}])
        out, report = filter_dataframe(df, require_value_fields=False)
        assert len(out) == 1
        assert report['blocked'] == 0
