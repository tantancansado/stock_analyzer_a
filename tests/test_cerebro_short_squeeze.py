"""Unit tests for score_short_squeeze — preserves cerebro.py rules exactly."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cerebro_lib.scoring import score_short_squeeze


def _base(**overrides):
    defaults = dict(
        short_pct_float=12.0,
        insider_buying=False,
        piotroski=5,
        hedge_fund_present=False,
        value_score=50,
    )
    defaults.update(overrides)
    return defaults


class TestScoreShortSqueeze:

    def test_short_very_high(self):
        score, flags = score_short_squeeze(**_base(short_pct_float=30))
        assert score == 40
        assert any("muy alto" in f for f in flags)

    def test_short_elevated(self):
        score, flags = score_short_squeeze(**_base(short_pct_float=20))
        assert score == 25
        assert any("elevado" in f for f in flags)

    def test_short_moderate(self):
        # Caller filters <10, so we test >=10 <15
        score, flags = score_short_squeeze(**_base(short_pct_float=12))
        assert score == 10
        assert any("moderado" in f for f in flags)

    def test_short_boundary_15_is_elevated(self):
        score, _ = score_short_squeeze(**_base(short_pct_float=15))
        assert score == 25

    def test_short_boundary_25_is_very_high(self):
        score, _ = score_short_squeeze(**_base(short_pct_float=25))
        assert score == 40

    def test_insider_buying_bonus(self):
        score, flags = score_short_squeeze(
            **_base(short_pct_float=20, insider_buying=True)
        )
        assert score == 45  # 25 + 20
        assert any("Insiders comprando" in f for f in flags)

    def test_piotroski_strong(self):
        score, flags = score_short_squeeze(
            **_base(short_pct_float=20, piotroski=7)
        )
        assert score == 40  # 25 + 15
        assert any("calidad mejorando" in f for f in flags)

    def test_piotroski_weak_no_bonus(self):
        score, _ = score_short_squeeze(
            **_base(short_pct_float=20, piotroski=5)
        )
        assert score == 25

    def test_piotroski_none_no_bonus(self):
        score, _ = score_short_squeeze(
            **_base(short_pct_float=20, piotroski=None)
        )
        assert score == 25

    def test_hedge_fund_bonus(self):
        score, flags = score_short_squeeze(
            **_base(short_pct_float=20, hedge_fund_present=True)
        )
        assert score == 40
        assert any("Hedge funds" in f for f in flags)

    def test_value_score_high(self):
        score, _ = score_short_squeeze(
            **_base(short_pct_float=20, value_score=75)
        )
        assert score == 35  # 25 + 10

    def test_value_score_mid(self):
        score, _ = score_short_squeeze(
            **_base(short_pct_float=20, value_score=60)
        )
        assert score == 31  # 25 + 6

    def test_value_score_low_no_bonus(self):
        score, _ = score_short_squeeze(
            **_base(short_pct_float=20, value_score=50)
        )
        assert score == 25

    def test_all_bonuses_stack(self):
        # 40 (short) + 20 (insider) + 15 (piotr) + 15 (HF) + 10 (vscore) = 100
        score, flags = score_short_squeeze(
            short_pct_float=30,
            insider_buying=True,
            piotroski=8,
            hedge_fund_present=True,
            value_score=80,
        )
        assert score == 100
        # flags count: short + insider + piotroski + HF = 4
        assert len(flags) == 4
