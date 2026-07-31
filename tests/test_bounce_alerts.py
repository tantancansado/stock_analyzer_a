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


def _curated_row(**over):
    """Fila de mean_reversion_opportunities.csv que la UI SÍ pintaría."""
    row = {'ticker': 'ABC', 'strategy': 'Oversold Bounce', 'rsi': 24.6,
           'current_price': 100.0, 'risk_reward': 1.8, 'bounce_confidence': 92.0,
           'distance_to_support_pct': 9.9, 'dark_pool_signal': 'ACCUMULATION',
           'earnings_warning': False}
    row.update(over)
    return row


class TestQualityFilters:
    def test_clean_setup_passes(self):
        assert ba.passes_quality_filters(_curated_row())[0] is True

    def test_rr_below_1_rejected(self):
        # Caso real TT 2026-07-31: R:R 0.3 — Telegram lo mandaba, la app no lo pintaba
        ok, why = ba.passes_quality_filters(_curated_row(risk_reward=0.3))
        assert ok is False and 'R:R' in why

    def test_rsi_not_oversold_rejected(self):
        assert ba.passes_quality_filters(_curated_row(rsi=45))[0] is False

    def test_missing_confidence_rejected(self):
        assert ba.passes_quality_filters(_curated_row(bounce_confidence=None))[0] is False

    def test_distribution_with_mid_confidence_rejected(self):
        row = _curated_row(dark_pool_signal='DISTRIBUTION', bounce_confidence=45)
        assert ba.passes_quality_filters(row)[0] is False

    def test_support_lost_rejected(self):
        assert ba.passes_quality_filters(_curated_row(distance_to_support_pct=-8))[0] is False

    def test_earnings_warning_string_rejected(self):
        assert ba.passes_quality_filters(_curated_row(earnings_warning='True'))[0] is False

    def test_missing_earnings_flag_does_not_reject(self):
        assert ba.passes_quality_filters(_curated_row(earnings_warning=float('nan')))[0] is True

    def test_missing_rr_does_not_reject(self):
        assert ba.passes_quality_filters(_curated_row(risk_reward=None))[0] is True


class TestBuildMessage:
    def test_contains_ticker_and_levels(self):
        msg = ba.build_message([_setup()], '2026-07-02')
        assert 'ABC' in msg
        assert '$50.00' in msg and '$52.00' in msg and '$48.75' in msg
        assert 'R:R 1.6' in msg

    def test_link_points_to_the_tab_of_the_setup(self):
        msg = ba.build_message([_setup(source='BROAD')], '2026-07-02')
        assert 'mode=broad' in msg and 'mode=curated' not in msg

    def test_both_links_when_both_sources(self):
        msg = ba.build_message([_setup('AAA', 'BROAD'), _setup('BBB', 'CURADO')], '2026-07-02')
        assert 'mode=broad' in msg and 'mode=curated' in msg

    def test_handles_missing_numbers(self):
        s = _setup()
        s['price'] = None; s['rr'] = None
        msg = ba.build_message([s], '2026-07-02')
        assert '—' in msg   # sin crash, muestra guión

    def test_caps_at_max_alerts(self):
        setups = [_setup(f'T{i}') for i in range(10)]
        msg = ba.build_message(setups, '2026-07-02')
        assert msg.count('[BROAD]') == ba.MAX_ALERTS
