"""Unit tests for score_quality_decay — preserves cerebro.py rules exactly."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cerebro_lib.scoring import score_quality_decay


def _stable(**overrides):
    """Everything unchanged vs snapshot — no decay flags."""
    defaults = dict(
        curr_piotroski=7, prev_piotroski=7,
        curr_fcf_yield_pct=5.0, prev_fcf_yield_pct=5.0,
        curr_health_score=75, prev_health_score=75,
        curr_op_margin_pct=20, prev_op_margin_pct=20,
    )
    defaults.update(overrides)
    return defaults


class TestScoreQualityDecay:

    def test_no_change_no_decay(self):
        score, flags = score_quality_decay(**_stable())
        assert score == 0
        assert flags == []

    def test_piotroski_big_drop(self):
        score, flags = score_quality_decay(
            **_stable(curr_piotroski=4, prev_piotroski=7)
        )
        assert score == 4
        assert any("cayó 3pts" in f for f in flags)

    def test_piotroski_small_drop(self):
        score, flags = score_quality_decay(
            **_stable(curr_piotroski=6, prev_piotroski=7)
        )
        assert score == 2
        assert any("bajó 1pt" in f for f in flags)

    def test_piotroski_missing_prev_skipped(self):
        score, _ = score_quality_decay(
            **_stable(prev_piotroski=None)
        )
        assert score == 0

    def test_piotroski_improvement_ignored(self):
        # Drop negative = improvement; should not trigger decay
        score, _ = score_quality_decay(
            **_stable(curr_piotroski=8, prev_piotroski=5)
        )
        assert score == 0

    def test_fcf_big_drop(self):
        score, flags = score_quality_decay(
            **_stable(curr_fcf_yield_pct=2.0, prev_fcf_yield_pct=6.0)
        )
        assert score == 3
        assert any("FCF yield cayó 4.0pp" in f for f in flags)

    def test_fcf_small_drop(self):
        score, flags = score_quality_decay(
            **_stable(curr_fcf_yield_pct=3.0, prev_fcf_yield_pct=5.0)
        )
        assert score == 1
        assert any("FCF yield cayó 2.0pp" in f for f in flags)

    def test_fcf_below_1_5pp_not_flagged(self):
        # Exactly 1.5pp triggers; 1.0pp does not
        score, _ = score_quality_decay(
            **_stable(curr_fcf_yield_pct=4.0, prev_fcf_yield_pct=5.0)
        )
        assert score == 0

    def test_health_big_drop(self):
        score, flags = score_quality_decay(
            **_stable(curr_health_score=60, prev_health_score=75)
        )
        assert score == 3
        assert any("Salud financiera cayó 15pts" in f for f in flags)

    def test_health_small_drop(self):
        score, flags = score_quality_decay(
            **_stable(curr_health_score=68, prev_health_score=75)
        )
        assert score == 1
        assert any("Salud financiera cayó 7pts" in f for f in flags)

    def test_margin_drop(self):
        score, flags = score_quality_decay(
            **_stable(curr_op_margin_pct=12, prev_op_margin_pct=20)
        )
        assert score == 3
        assert any("Margen op. cayó 8.0pp" in f for f in flags)

    def test_margin_below_5pp_not_flagged(self):
        score, _ = score_quality_decay(
            **_stable(curr_op_margin_pct=17, prev_op_margin_pct=20)
        )
        assert score == 0

    def test_systemic_bonus_fires_at_three_flags(self):
        # Big drops in Piotroski (+4) + FCF (+3) + Health (+3) = 10 + systemic +2 = 12
        score, flags = score_quality_decay(
            curr_piotroski=4, prev_piotroski=7,
            curr_fcf_yield_pct=2.0, prev_fcf_yield_pct=6.0,
            curr_health_score=60, prev_health_score=75,
            curr_op_margin_pct=20, prev_op_margin_pct=20,
        )
        assert score == 12
        assert any("Deterioro sistémico" in f for f in flags)

    def test_two_flags_no_systemic_bonus(self):
        # Only 2 flags — no systemic bonus
        score, flags = score_quality_decay(
            curr_piotroski=4, prev_piotroski=7,    # +4
            curr_fcf_yield_pct=2.0, prev_fcf_yield_pct=6.0,  # +3
            curr_health_score=None, prev_health_score=None,
            curr_op_margin_pct=None, prev_op_margin_pct=None,
        )
        assert score == 7
        assert not any("sistémico" in f for f in flags)

    def test_all_none_no_score(self):
        score, flags = score_quality_decay(
            curr_piotroski=None, prev_piotroski=None,
            curr_fcf_yield_pct=None, prev_fcf_yield_pct=None,
            curr_health_score=None, prev_health_score=None,
            curr_op_margin_pct=None, prev_op_margin_pct=None,
        )
        assert score == 0
        assert flags == []
