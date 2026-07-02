#!/usr/bin/env python3
"""Tests para bounce_alerts — dedup y construcción del mensaje (sin red)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bounce_alerts as ba


def _setup(ticker='ABC', source='BROAD'):
    return {'ticker': ticker, 'source': source, 'price': 50.0, 'target': 52.0,
            'stop': 48.75, 'rr': 1.6, 'rsi': 8.2, 'note': 'RSI2 ayer 8.2 · vol 1.5x'}


class TestFilterNew:
    def test_new_ticker_passes_and_marks_seen(self):
        seen = {}
        fresh = ba.filter_new([_setup()], seen, '2026-07-02')
        assert len(fresh) == 1
        assert seen['ABC'] == '2026-07-02'

    def test_recent_ticker_suppressed(self):
        seen = {'ABC': '2026-07-01'}   # avisado ayer, dedup 3 días
        fresh = ba.filter_new([_setup()], seen, '2026-07-02')
        assert fresh == []

    def test_old_ticker_realerted(self):
        seen = {'ABC': '2026-06-20'}   # hace 12 días — el setup es otro
        fresh = ba.filter_new([_setup()], seen, '2026-07-02')
        assert len(fresh) == 1
        assert seen['ABC'] == '2026-07-02'

    def test_corrupt_seen_date_does_not_crash(self):
        seen = {'ABC': 'not-a-date'}
        fresh = ba.filter_new([_setup()], seen, '2026-07-02')
        assert len(fresh) == 1


class TestBuildMessage:
    def test_contains_ticker_and_levels(self):
        msg = ba.build_message([_setup()], '2026-07-02')
        assert 'ABC' in msg
        assert '$50.00' in msg and '$52.00' in msg and '$48.75' in msg
        assert 'R:R 1.6' in msg

    def test_handles_missing_numbers(self):
        s = _setup()
        s['price'] = None; s['rr'] = None
        msg = ba.build_message([s], '2026-07-02')
        assert '—' in msg   # sin crash, muestra guión

    def test_caps_at_max_alerts(self):
        setups = [_setup(f'T{i}') for i in range(10)]
        msg = ba.build_message(setups, '2026-07-02')
        assert msg.count('[BROAD]') == ba.MAX_ALERTS
