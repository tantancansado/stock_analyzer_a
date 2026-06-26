"""Unit tests for cerebro.py pure helpers.

Import cerebro module level helpers directly. These are the functions that
will be extracted to cerebro_lib/ — tests are written BEFORE extraction so
we can detect any behavior change during the refactor.
"""
import json
import sys
import os
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cerebro import sf, load_csv, load_json, save_json, _parse_health


class TestSf:
    """sf() = safe-float: returns None for NaN, non-numeric, None."""

    def test_int_returns_float(self):
        assert sf(5) == 5.0
        assert isinstance(sf(5), float)

    def test_float_passthrough(self):
        assert sf(3.14) == 3.14

    def test_numeric_string(self):
        assert sf("42.5") == 42.5

    def test_none_returns_none(self):
        assert sf(None) is None

    def test_nan_returns_none(self):
        assert sf(float("nan")) is None

    def test_empty_string_returns_none(self):
        assert sf("") is None

    def test_garbage_string_returns_none(self):
        assert sf("not a number") is None

    def test_bool_true_is_one(self):
        # Current behavior: bool coerces to 1.0 / 0.0 via float()
        assert sf(True) == 1.0
        assert sf(False) == 0.0

    def test_list_returns_none(self):
        assert sf([1, 2, 3]) is None


class TestLoadCsv:
    def test_missing_file_returns_empty_df(self):
        result = load_csv(Path("/nonexistent/path.csv"))
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_reads_valid_csv(self, tmp_path):
        p = tmp_path / "t.csv"
        p.write_text("ticker,score\nAAPL,85\nMSFT,72\n")
        df = load_csv(p)
        assert len(df) == 2
        assert list(df.columns) == ["ticker", "score"]
        assert df.iloc[0]["ticker"] == "AAPL"

    def test_malformed_csv_returns_empty(self, tmp_path):
        # Pandas is actually tolerant; use a directory to force a read error
        d = tmp_path / "dir.csv"
        d.mkdir()
        result = load_csv(d)
        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestLoadJson:
    def test_missing_file_returns_empty_dict(self):
        assert load_json(Path("/nonexistent/x.json")) == {}

    def test_reads_valid_json(self, tmp_path):
        p = tmp_path / "t.json"
        p.write_text('{"a": 1, "b": [2, 3]}')
        assert load_json(p) == {"a": 1, "b": [2, 3]}

    def test_malformed_json_returns_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json")
        assert load_json(p) == {}


class TestSaveJson:
    def test_writes_pretty_indented(self, tmp_path):
        p = tmp_path / "out.json"
        save_json(p, {"a": 1})
        content = p.read_text()
        assert '"a": 1' in content
        # indent=2 → at least one newline
        assert "\n" in content

    def test_roundtrip(self, tmp_path):
        data = {"ticker": "AAPL", "nested": {"k": [1, 2]}}
        p = tmp_path / "r.json"
        save_json(p, data)
        assert load_json(p) == data

    def test_serializes_non_json_types(self, tmp_path):
        # save_json uses default=str — date/decimal etc should not crash
        from datetime import date
        p = tmp_path / "d.json"
        save_json(p, {"when": date(2026, 1, 15)})
        loaded = load_json(p)
        assert loaded["when"] == "2026-01-15"


class TestParseHealth:
    """_parse_health parses health_details JSON column from a pandas row."""

    def test_dict_passthrough(self):
        row = pd.Series({"health_details": {"roe_pct": 25.0}})
        assert _parse_health(row) == {"roe_pct": 25.0}

    def test_json_string(self):
        row = pd.Series({"health_details": '{"roe_pct": 25.0, "debt_to_equity": 0.5}'})
        result = _parse_health(row)
        assert result["roe_pct"] == 25.0
        assert result["debt_to_equity"] == 0.5

    def test_python_repr_string(self):
        # Real format written by the pipeline: str(dict) via pandas to_csv,
        # single-quoted — NOT valid JSON. json.loads() alone fails on this;
        # this is the format every row in fundamental_scores.csv actually has.
        row = pd.Series({"health_details": "{'roe_pct': 5.9, 'debt_to_equity': 0.37, 'operating_margin_pct': 39.8}"})
        result = _parse_health(row)
        assert result["roe_pct"] == 5.9
        assert result["debt_to_equity"] == 0.37
        assert result["operating_margin_pct"] == 39.8

    def test_missing_column_returns_empty(self):
        row = pd.Series({"ticker": "AAPL"})
        assert _parse_health(row) == {}

    def test_none_returns_empty(self):
        row = pd.Series({"health_details": None})
        assert _parse_health(row) == {}

    def test_empty_string_returns_empty(self):
        row = pd.Series({"health_details": ""})
        assert _parse_health(row) == {}

    def test_malformed_json_returns_empty(self):
        row = pd.Series({"health_details": "{not valid"})
        assert _parse_health(row) == {}

    def test_non_dict_json_returns_empty(self):
        # A JSON array parses successfully but isn't a dict
        row = pd.Series({"health_details": "[1, 2, 3]"})
        assert _parse_health(row) == {}
