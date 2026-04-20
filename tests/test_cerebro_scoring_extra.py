"""Unit tests for the rest of cerebro_lib.scoring."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cerebro_lib.scoring import (
    score_smart_money,
    score_insider_cluster,
    score_dividend_safety,
    classify_piotroski_trend,
    classify_piotroski_signal,
)


class TestScoreSmartMoney:
    def test_base_formula(self):
        # 2 funds × 15 + 3 insiders × 10 + 80 × 0.3 = 30+30+24 = 84
        assert score_smart_money(n_hedge_funds=2, n_insiders=3, value_score=80) == 84

    def test_caps_at_100(self):
        assert score_smart_money(n_hedge_funds=10, n_insiders=10, value_score=100) == 100

    def test_value_score_none_treated_as_zero(self):
        # 1×15 + 1×10 + 0 = 25
        assert score_smart_money(n_hedge_funds=1, n_insiders=1, value_score=None) == 25

    def test_returns_int(self):
        r = score_smart_money(n_hedge_funds=1, n_insiders=1, value_score=75)
        assert isinstance(r, int)
        # 15 + 10 + 22.5 = 47.5 → round to 48
        assert r == 48


class TestScoreInsiderCluster:
    def test_base(self):
        # 3 tickers × 20 + 5 purchases × 2 = 70
        assert score_insider_cluster(ticker_count=3, total_purchases=5) == 70

    def test_caps_at_100(self):
        assert score_insider_cluster(ticker_count=10, total_purchases=50) == 100

    def test_zero(self):
        assert score_insider_cluster(ticker_count=0, total_purchases=0) == 0


class TestScoreDividendSafety:

    def test_clean_dividend_is_safe(self):
        s, rating, flags = score_dividend_safety(
            dividend_yield_pct=3.0,
            payout_ratio_pct=40,
            fcf_yield_pct=6.0,
            interest_coverage=10,
        )
        # base 100 + 10 (payout<50) = 110 capped → 100
        assert s == 100
        assert rating == "SAFE"
        assert flags == []

    def test_high_payout_insostenible(self):
        s, rating, flags = score_dividend_safety(
            dividend_yield_pct=3, payout_ratio_pct=95,
            fcf_yield_pct=5, interest_coverage=5,
        )
        assert s == 60  # 100 - 40
        assert rating == "WATCH"
        assert any("insostenible" in f for f in flags)

    def test_high_payout_zona_riesgo(self):
        s, _, flags = score_dividend_safety(
            dividend_yield_pct=3, payout_ratio_pct=80,
            fcf_yield_pct=5, interest_coverage=5,
        )
        assert s == 80  # 100 - 20
        assert any("zona de riesgo" in f for f in flags)

    def test_payout_at_boundary_75_not_flagged(self):
        # >75 triggers; exactly 75 does not
        s, _, flags = score_dividend_safety(
            dividend_yield_pct=3, payout_ratio_pct=75,
            fcf_yield_pct=5, interest_coverage=5,
        )
        assert s == 100
        assert flags == []

    def test_fcf_negative(self):
        s, rating, flags = score_dividend_safety(
            dividend_yield_pct=4, payout_ratio_pct=60,
            fcf_yield_pct=-1.5, interest_coverage=5,
        )
        # 100 - 35 = 65 → SAFE (rating boundary is <65)
        assert s == 65
        assert rating == "SAFE"
        assert any("FCF negativo" in f for f in flags)

    def test_fcf_below_dividend(self):
        # FCF 2% < div 4% → cobertura ajustada
        s, _, flags = score_dividend_safety(
            dividend_yield_pct=4, payout_ratio_pct=60,
            fcf_yield_pct=2, interest_coverage=5,
        )
        assert s == 85  # 100 - 15
        assert any("cobertura ajustada" in f for f in flags)

    def test_low_interest_coverage(self):
        s, _, flags = score_dividend_safety(
            dividend_yield_pct=3, payout_ratio_pct=60,
            fcf_yield_pct=5, interest_coverage=1.5,
        )
        assert s == 85  # 100 - 15
        assert any("deuda consume caja" in f for f in flags)

    def test_multiple_risks_at_risk_rating(self):
        # payout 95 (-40) + FCF neg (-35) = 25 → AT_RISK
        s, rating, flags = score_dividend_safety(
            dividend_yield_pct=4, payout_ratio_pct=95,
            fcf_yield_pct=-2, interest_coverage=3,
        )
        assert s == 25
        assert rating == "AT_RISK"
        assert len(flags) == 2

    def test_score_never_negative(self):
        s, _, _ = score_dividend_safety(
            dividend_yield_pct=5, payout_ratio_pct=95,
            fcf_yield_pct=-5, interest_coverage=0.5,
        )
        # 100-40-35-15 = 10 (also FCF<yield could stack → but FCF<0 wins)
        assert s >= 0

    def test_missing_metrics_skipped(self):
        s, rating, flags = score_dividend_safety(
            dividend_yield_pct=3,
            payout_ratio_pct=None, fcf_yield_pct=None, interest_coverage=None,
        )
        assert s == 100
        assert rating == "SAFE"
        assert flags == []


class TestPiotroskiTrend:
    def test_improving(self):
        assert classify_piotroski_trend(7, 4) == ("IMPROVING", 3)

    def test_slight_up(self):
        assert classify_piotroski_trend(6, 5) == ("SLIGHT_UP", 1)

    def test_deteriorating(self):
        assert classify_piotroski_trend(3, 6) == ("DETERIORATING", -3)

    def test_slight_down(self):
        assert classify_piotroski_trend(5, 6) == ("SLIGHT_DOWN", -1)

    def test_stable(self):
        assert classify_piotroski_trend(5, 5) == ("STABLE", 0)

    def test_no_previous_is_stable(self):
        assert classify_piotroski_trend(7, None) == ("STABLE", 0.0)

    def test_fractional_delta_under_1(self):
        # delta 0.5 → STABLE (no label)
        trend, delta = classify_piotroski_trend(6.5, 6.0)
        assert trend == "STABLE"
        assert delta == 0.5


class TestPiotroskiSignal:
    def test_strong(self):
        assert classify_piotroski_signal(9) == "STRONG"
        assert classify_piotroski_signal(7) == "STRONG"

    def test_weak(self):
        assert classify_piotroski_signal(0) == "WEAK"
        assert classify_piotroski_signal(3) == "WEAK"

    def test_neutral(self):
        for s in [4, 5, 6]:
            assert classify_piotroski_signal(s) == "NEUTRAL"
