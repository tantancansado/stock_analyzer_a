"""Unit tests for thesis_drift_monitor — open VALUE position thesis integrity."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import thesis_drift_monitor as tdm


def _pos(**overrides):
    base = dict(
        ticker='AAPL', company_name='Apple', strategy='VALUE',
        signal_date='2026-04-15', value_score=70.0, stop_loss=90.0,
        price_7d=100.0, price_14d=100.0, price_30d=100.0,
    )
    base.update(overrides)
    return base


def _fund(**overrides):
    base = dict(fundamental_score=70.0, analyst_upside_pct=15.0, earnings_warning='none')
    base.update(overrides)
    return base


class TestEvaluate:
    def test_intact_thesis_no_findings(self):
        assert tdm._evaluate(_pos(), _fund()) == []

    def test_stop_breached(self):
        f = tdm._evaluate(_pos(stop_loss=110.0, price_30d=100.0), _fund())
        assert any(x['type'] == 'STOP_BREACHED' and x['severity'] == 'HIGH' for x in f)

    def test_stop_not_breached_at_boundary(self):
        # price == stop is not below stop
        f = tdm._evaluate(_pos(stop_loss=100.0, price_30d=100.0), _fund())
        assert not any(x['type'] == 'STOP_BREACHED' for x in f)

    def test_upside_value_trap(self):
        f = tdm._evaluate(_pos(), _fund(analyst_upside_pct=39.0))
        assert any(x['type'] == 'THESIS_BROKEN' and 'value trap' in x['reason'] for x in f)

    def test_upside_just_below_trap_ok(self):
        f = tdm._evaluate(_pos(), _fund(analyst_upside_pct=29.9))
        assert not any('value trap' in x['reason'] for x in f)

    def test_negative_upside_overvalued(self):
        f = tdm._evaluate(_pos(), _fund(analyst_upside_pct=-5.0))
        assert any(x['type'] == 'THESIS_BROKEN' and 'sobrevalorado' in x['reason'] for x in f)

    def test_fundamental_collapse(self):
        f = tdm._evaluate(_pos(), _fund(fundamental_score=44.0))
        assert any(x['type'] == 'THESIS_BROKEN' and 'colapsó' in x['reason'] for x in f)

    def test_fundamental_deterioration(self):
        # value_score 70 at signal, now 59 → 11pt drop ≥ threshold
        f = tdm._evaluate(_pos(value_score=70.0), _fund(fundamental_score=59.0))
        assert any(x['type'] == 'FUND_DETERIORATING' for x in f)

    def test_fundamental_small_drop_no_alert(self):
        # 70 → 64 = 6pt drop < 10pt threshold
        f = tdm._evaluate(_pos(value_score=70.0), _fund(fundamental_score=64.0))
        assert not any(x['type'] == 'FUND_DETERIORATING' for x in f)

    def test_earnings_warning_active(self):
        f = tdm._evaluate(_pos(), _fund(earnings_warning='guidance cut'))
        assert any(x['type'] == 'THESIS_BROKEN' and 'earnings_warning' in x['reason'] for x in f)

    def test_no_fundamentals_only_price_checked(self):
        # fund=None: must not invent a fundamental verdict, but still checks stop
        f = tdm._evaluate(_pos(stop_loss=110.0, price_30d=100.0), None)
        assert [x['type'] for x in f] == ['STOP_BREACHED']

    def test_missing_data_no_false_positive(self):
        # all fundamental fields missing → no thesis verdict invented
        f = tdm._evaluate(_pos(value_score=None),
                          _fund(fundamental_score=None, analyst_upside_pct=None, earnings_warning='nan'))
        assert f == []


class TestNumCoercion:
    def test_num_handles_missing(self):
        assert tdm._num(None) is None
        assert tdm._num('nan') is None
        assert tdm._num(float('nan')) is None

    def test_num_parses_value(self):
        assert tdm._num('42.5') == 42.5
        assert tdm._num(15) == 15.0
