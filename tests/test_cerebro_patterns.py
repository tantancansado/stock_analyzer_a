"""Unit tests for cerebro_lib.patterns."""
import sys
import os

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cerebro_lib.patterns import compute_stats, tier_column


def _hist(rows):
    """Quick factory for a portfolio_tracker-shaped dataframe."""
    return pd.DataFrame(rows)


class TestComputeStats:

    def test_below_min_n_returns_none(self):
        df = _hist([{"win_7d": 1, "return_7d": 5.0}] * 2)
        assert compute_stats(df, "tiny", 50.0, 0.0) is None

    def test_basic_stats(self):
        df = _hist([
            {"win_7d": 1, "return_7d": 10.0},
            {"win_7d": 1, "return_7d": 4.0},
            {"win_7d": 0, "return_7d": -2.0},
        ])
        # wr = 2/3 = 66.7%, ret = 4.0
        r = compute_stats(df, "slice", base_wr=50.0, base_ret=1.0)
        assert r["label"] == "slice"
        assert r["win_rate_7d"] == 66.7
        assert r["avg_return_7d"] == 4.0
        assert r["n"] == 3
        assert r["vs_baseline_wr"] == 16.7
        assert r["vs_baseline_ret"] == 3.0
        assert r["avg_return_14d"] is None

    def test_return_14d_when_present(self):
        df = _hist([
            {"win_7d": 1, "return_7d": 5, "return_14d": 8.0},
            {"win_7d": 1, "return_7d": 5, "return_14d": 12.0},
            {"win_7d": 1, "return_7d": 5, "return_14d": 10.0},
        ])
        r = compute_stats(df, "x", 50.0, 0.0)
        assert r["avg_return_14d"] == 10.0

    def test_return_14d_all_nan_skipped(self):
        df = _hist([
            {"win_7d": 1, "return_7d": 5, "return_14d": float("nan")},
            {"win_7d": 1, "return_7d": 5, "return_14d": float("nan")},
            {"win_7d": 1, "return_7d": 5, "return_14d": float("nan")},
        ])
        r = compute_stats(df, "x", 50.0, 0.0)
        assert r["avg_return_14d"] is None

    def test_missing_win_7d_column(self):
        df = _hist([{"return_7d": 5.0}] * 3)
        r = compute_stats(df, "x", 50.0, 0.0)
        assert r["win_rate_7d"] == 0.0

    def test_custom_min_n(self):
        df = _hist([{"win_7d": 1, "return_7d": 5.0}])
        # with min_n=1, 1 row should return stats
        assert compute_stats(df, "x", 50.0, 0.0, min_n=1) is not None


class TestTierColumn:

    def test_buckets_rows_correctly(self):
        df = _hist([
            {"value_score": 95, "win_7d": 1, "return_7d": 10},
            {"value_score": 92, "win_7d": 1, "return_7d": 8},
            {"value_score": 91, "win_7d": 0, "return_7d": -1},
            {"value_score": 85, "win_7d": 1, "return_7d": 5},
            {"value_score": 84, "win_7d": 1, "return_7d": 4},
            {"value_score": 82, "win_7d": 0, "return_7d": -2},
        ])
        tiers = tier_column(df, "value_score", [(90, 101), (80, 90)], 50.0, 0.0)
        assert len(tiers) == 2
        assert tiers[0]["label"] == "90–101"
        assert tiers[0]["n"] == 3
        assert tiers[1]["label"] == "80–90"
        assert tiers[1]["n"] == 3

    def test_empty_buckets_excluded(self):
        df = _hist([{"value_score": 95, "win_7d": 1, "return_7d": 5}] * 3)
        tiers = tier_column(df, "value_score", [(90, 101), (80, 90), (70, 80)], 50.0, 0.0)
        # Only the 90-101 bucket has rows
        assert len(tiers) == 1
        assert tiers[0]["label"] == "90–101"

    def test_bucket_with_too_few_rows_skipped(self):
        df = _hist([{"value_score": 95, "win_7d": 1, "return_7d": 5}] * 2)
        tiers = tier_column(df, "value_score", [(90, 101)], 50.0, 0.0)
        assert tiers == []
