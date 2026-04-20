"""Tests for the per-run CSV cache in cerebro.py."""
import sys
import os
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cerebro


class TestCsvCache:

    def setup_method(self):
        cerebro._reset_csv_cache()

    def test_cache_hit_returns_equal_dataframe(self, tmp_path):
        p = tmp_path / "t.csv"
        p.write_text("ticker,score\nAAPL,85\n")
        df1 = cerebro.load_csv(p)
        df2 = cerebro.load_csv(p)
        assert df1.equals(df2)

    def test_cache_returns_independent_copies(self, tmp_path):
        """Caller mutation must not affect cache entry or other callers."""
        p = tmp_path / "t.csv"
        p.write_text("ticker,score\nAAPL,85\nMSFT,72\n")
        df1 = cerebro.load_csv(p)
        df1.loc[0, "ticker"] = "MUTATED"
        df2 = cerebro.load_csv(p)
        assert df2.iloc[0]["ticker"] == "AAPL"

    def test_cache_misses_on_different_paths(self, tmp_path):
        p1 = tmp_path / "a.csv"; p1.write_text("x\n1\n")
        p2 = tmp_path / "b.csv"; p2.write_text("x\n2\n")
        df1 = cerebro.load_csv(p1)
        df2 = cerebro.load_csv(p2)
        assert df1.iloc[0]["x"] == 1
        assert df2.iloc[0]["x"] == 2

    def test_missing_file_also_cached(self, tmp_path):
        # Non-existent path returns empty DF; cache should still work
        p = tmp_path / "missing.csv"
        df1 = cerebro.load_csv(p)
        df2 = cerebro.load_csv(p)
        assert df1.empty
        assert df2.empty

    def test_reset_clears_cache(self, tmp_path):
        p = tmp_path / "t.csv"
        p.write_text("x\n1\n")
        cerebro.load_csv(p)
        assert str(p) in cerebro._CSV_CACHE
        cerebro._reset_csv_cache()
        assert len(cerebro._CSV_CACHE) == 0
