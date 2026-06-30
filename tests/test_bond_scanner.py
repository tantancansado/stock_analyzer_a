#!/usr/bin/env python3
"""Tests para bond_scanner._liquidity — rating de liquidez (pura, sin red)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bond_scanner import _liquidity, LIQUIDITY_ALTA_MIN, LIQUIDITY_MEDIA_MIN


class TestLiquidity:
    def test_alta_above_threshold(self):
        r = _liquidity({"averageVolume": LIQUIDITY_ALTA_MIN + 1})
        assert r["liquidity_rating"] == "ALTA"

    def test_media_between_thresholds(self):
        r = _liquidity({"averageVolume": LIQUIDITY_MEDIA_MIN + 1})
        assert r["liquidity_rating"] == "MEDIA"

    def test_baja_below_threshold(self):
        r = _liquidity({"averageVolume": LIQUIDITY_MEDIA_MIN - 1})
        assert r["liquidity_rating"] == "BAJA"

    def test_sin_dato_when_missing(self):
        r = _liquidity({})
        assert r["liquidity_rating"] == "SIN_DATO"
        assert r["avg_volume_3m"] is None

    def test_falls_back_to_3month_field(self):
        r = _liquidity({"averageDailyVolume3Month": LIQUIDITY_ALTA_MIN + 500})
        assert r["liquidity_rating"] == "ALTA"
        assert r["avg_volume_3m"] == LIQUIDITY_ALTA_MIN + 500

    def test_spread_pct_computed_from_bid_ask(self):
        r = _liquidity({"averageVolume": 1, "bid": 19.0, "ask": 21.0})
        # mid = 20, diff = 2 -> 10%
        assert r["spread_pct"] == 10.0

    def test_spread_none_when_bid_or_ask_zero(self):
        r = _liquidity({"averageVolume": 1, "bid": 0.0, "ask": 0.0})
        assert r["spread_pct"] is None

    def test_liquidity_note_present_for_each_rating(self):
        for vol, expected in [
            (LIQUIDITY_ALTA_MIN + 1, "ALTA"),
            (LIQUIDITY_MEDIA_MIN + 1, "MEDIA"),
            (1, "BAJA"),
        ]:
            r = _liquidity({"averageVolume": vol})
            assert r["liquidity_rating"] == expected
            assert r["liquidity_note"]
