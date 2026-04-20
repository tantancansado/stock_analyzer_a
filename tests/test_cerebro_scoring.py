"""Unit tests for cerebro_lib.scoring — pure, no I/O."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cerebro_lib.scoring import compute_convergence_score


class TestComputeConvergenceScore:

    def test_two_strategies_no_value(self):
        # 2 strats × 20 = 40
        assert compute_convergence_score(["MR", "MOMENTUM"], None, 1) == 40

    def test_value_bonus_scales_with_score(self):
        # 2 strats × 20 + VALUE bonus (75/5=15) = 55
        assert compute_convergence_score(["VALUE", "MR"], 75, 1) == 55

    def test_value_bonus_capped_at_20(self):
        # value_score=150 would give 30 but cap is 20
        assert compute_convergence_score(["VALUE", "MR"], 150, 1) == 60

    def test_insiders_flat_bonus(self):
        # 2 strats × 20 + INSIDERS 10 = 50
        assert compute_convergence_score(["INSIDERS", "MR"], None, 1) == 50

    def test_streak_bonus_at_3_days(self):
        # 2 strats × 20 + streak 10 = 50
        assert compute_convergence_score(["MR", "OPTIONS"], None, 3) == 50

    def test_no_streak_bonus_below_3_days(self):
        assert compute_convergence_score(["MR", "OPTIONS"], None, 2) == 40

    def test_all_bonuses_stack_and_cap_at_100(self):
        # 5 strats × 20 = 100 already → capped
        s = compute_convergence_score(
            ["VALUE", "INSIDERS", "MR", "OPTIONS", "MOMENTUM"], 95, 5
        )
        assert s == 100

    def test_single_strategy_still_scored(self):
        # Function doesn't enforce the ≥2 filter — caller does
        assert compute_convergence_score(["VALUE"], 80, 1) == 36

    def test_value_score_zero_skips_bonus(self):
        # Preserves current behavior: `if ... and value_score:` treats 0 as falsy
        # (and a value_score of 0 means hard-reject in the pipeline)
        assert compute_convergence_score(["VALUE", "MR"], 0, 1) == 40

    def test_value_score_none_skips_bonus(self):
        assert compute_convergence_score(["VALUE", "MR"], None, 1) == 40

    def test_returns_int(self):
        # value_score/5 can be fractional → int() truncates
        result = compute_convergence_score(["VALUE", "MR"], 77, 1)
        assert isinstance(result, int)
        # 40 + 77/5 = 40 + 15.4 → int(55.4) = 55
        assert result == 55
