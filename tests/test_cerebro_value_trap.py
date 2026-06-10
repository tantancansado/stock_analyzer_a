"""Unit tests for score_value_trap — preserves cerebro.py rules exactly."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cerebro_lib.scoring import score_value_trap


def _base(**overrides):
    """Default 'clean' ticker — no trap flags should fire."""
    defaults = dict(
        piotroski=7,
        fcf_yield_pct=5.0,
        fundamental_score=70,
        analyst_count=8,
        analyst_recommendation="buy",
        value_score=75,
        debt_to_equity=0.5,
        operating_margin_pct=20,
    )
    defaults.update(overrides)
    return defaults


class TestScoreValueTrap:

    def test_clean_ticker_no_trap(self):
        score, flags = score_value_trap(**_base())
        assert score == 0
        assert flags == []

    def test_piotroski_very_weak(self):
        score, flags = score_value_trap(**_base(piotroski=1))
        assert score == 4
        assert any("muy débil" in f for f in flags)

    def test_piotroski_weak(self):
        score, flags = score_value_trap(**_base(piotroski=3))
        assert score == 2
        assert any("Piotroski débil" in f for f in flags)

    def test_piotroski_at_boundary_5_no_flag(self):
        # ≤4 triggers weak; 5 does not
        score, _ = score_value_trap(**_base(piotroski=5))
        assert score == 0

    def test_piotroski_none_skipped(self):
        score, _ = score_value_trap(**_base(piotroski=None))
        assert score == 0

    def test_fcf_negative(self):
        score, flags = score_value_trap(**_base(fcf_yield_pct=-2.5))
        assert score == 3
        assert any("FCF negativo" in f for f in flags)

    def test_fcf_zero_not_flagged(self):
        score, _ = score_value_trap(**_base(fcf_yield_pct=0))
        assert score == 0

    def test_fundamental_near_default(self):
        # Flag only fires when Piotroski is NOT strong (≥7): a high-Piotroski
        # company with missing fundamental data is missing data, not a trap.
        for s in [48, 50, 53]:
            score, flags = score_value_trap(**_base(fundamental_score=s, piotroski=5))
            assert score == 2, f"fund_s={s} should flag"
            assert any("cerca de default" in f for f in flags)

    def test_fundamental_near_default_suppressed_when_piotroski_strong(self):
        # Piotroski ≥7 overrides the missing-data trap indicator.
        for s in [48, 50, 53]:
            score, flags = score_value_trap(**_base(fundamental_score=s, piotroski=7))
            assert score == 0, f"fund_s={s} should NOT flag with strong Piotroski"
            assert not any("cerca de default" in f for f in flags)

    def test_fundamental_outside_default_band(self):
        score, _ = score_value_trap(**_base(fundamental_score=47, piotroski=5))
        assert score == 0
        score, _ = score_value_trap(**_base(fundamental_score=54, piotroski=5))
        assert score == 0

    def test_no_analyst_coverage_high_score(self):
        score, flags = score_value_trap(**_base(analyst_count=1, value_score=70))
        assert score == 2
        assert any("Sin cobertura" in f for f in flags)

    def test_no_analyst_coverage_low_score_skipped(self):
        # value_score must be > 65 for flag to fire
        score, _ = score_value_trap(**_base(analyst_count=0, value_score=60))
        assert score == 0

    def test_analyst_count_none_counts_as_missing(self):
        score, flags = score_value_trap(**_base(analyst_count=None, value_score=80))
        assert score == 2
        assert any("Sin cobertura" in f for f in flags)

    def test_analyst_hold_on_high_score(self):
        score, flags = score_value_trap(**_base(analyst_recommendation="HOLD", value_score=80))
        assert score == 2
        assert any("'hold'" in f for f in flags)

    def test_analyst_sell_on_high_score(self):
        score, flags = score_value_trap(**_base(analyst_recommendation="sell", value_score=80))
        assert score == 2
        assert any("'sell'" in f for f in flags)

    def test_analyst_buy_not_flagged(self):
        score, _ = score_value_trap(**_base(analyst_recommendation="buy", value_score=80))
        assert score == 0

    def test_high_debt_low_margin(self):
        score, flags = score_value_trap(
            **_base(debt_to_equity=2.5, operating_margin_pct=3)
        )
        assert score == 2
        assert any("Deuda alta" in f for f in flags)

    def test_high_debt_healthy_margin_not_flagged(self):
        score, _ = score_value_trap(
            **_base(debt_to_equity=3.0, operating_margin_pct=15)
        )
        assert score == 0

    def test_multiple_flags_stack(self):
        # Piotroski muy débil (4) + FCF negativo (3) + near-default fund (2) = 9
        score, flags = score_value_trap(
            **_base(piotroski=1, fcf_yield_pct=-3, fundamental_score=50)
        )
        assert score == 9
        assert len(flags) == 3

    def test_empty_rec_string(self):
        score, _ = score_value_trap(**_base(analyst_recommendation=""))
        assert score == 0
