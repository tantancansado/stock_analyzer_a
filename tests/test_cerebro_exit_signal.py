"""Unit tests for score_exit_signal — preserves cerebro.py rules exactly."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cerebro_lib.scoring import score_exit_signal


def _base(**overrides):
    """Healthy open position — no exit signal."""
    defaults = dict(
        ticker_in_value=True,
        entry_score=70,
        current_score=70,
        earnings_warning=False,
        days_to_earnings=None,
        insider_active=True,
    )
    defaults.update(overrides)
    return defaults


class TestScoreExitSignal:

    def test_healthy_position_no_exit(self):
        sev, reasons = score_exit_signal(**_base())
        assert sev == "LOW"
        assert reasons == []

    def test_ticker_dropped_from_value_is_high(self):
        sev, reasons = score_exit_signal(**_base(ticker_in_value=False))
        assert sev == "HIGH"
        assert any("tesis posiblemente rota" in r for r in reasons)

    def test_score_drop_massive_is_high(self):
        # entry 80 → current 50 = drop 30, no piotroski → HIGH
        sev, reasons = score_exit_signal(
            **_base(entry_score=80, current_score=50)
        )
        assert sev == "HIGH"
        assert any("Score cayó 30pts" in r for r in reasons)

    def test_score_drop_massive_strong_piotroski_is_medium(self):
        # drop ≥25 but Piotroski 9 → MEDIUM (momentum weakness, not fundamental)
        sev, reasons = score_exit_signal(
            **_base(entry_score=80, current_score=50, piotroski_score=9)
        )
        assert sev == "MEDIUM"
        assert any("Piotroski" in r for r in reasons)
        assert any("balance sólido" in r for r in reasons)

    def test_score_drop_massive_weak_piotroski_stays_high(self):
        # drop ≥25 and Piotroski 5 → still HIGH
        sev, _ = score_exit_signal(
            **_base(entry_score=80, current_score=50, piotroski_score=5)
        )
        assert sev == "HIGH"

    def test_score_drop_medium(self):
        # entry 80 → current 62 = drop 18 → MEDIUM
        sev, reasons = score_exit_signal(
            **_base(entry_score=80, current_score=62)
        )
        assert sev == "MEDIUM"
        assert any("Score cayó 18pts" in r for r in reasons)

    def test_score_drop_below_threshold_no_alert(self):
        # drop 10 < 15 threshold
        sev, reasons = score_exit_signal(
            **_base(entry_score=80, current_score=70)
        )
        assert sev == "LOW"
        assert reasons == []

    def test_earnings_imminent_medium(self):
        sev, reasons = score_exit_signal(
            **_base(earnings_warning=True, days_to_earnings=5)
        )
        assert sev == "MEDIUM"
        assert any("Earnings en 5d" in r for r in reasons)

    def test_earnings_beyond_7_days_no_alert(self):
        sev, reasons = score_exit_signal(
            **_base(earnings_warning=True, days_to_earnings=10)
        )
        assert sev == "LOW"
        assert reasons == []

    def test_earnings_does_not_downgrade_high(self):
        # Already HIGH from ticker-dropped — earnings should not reduce it
        sev, _ = score_exit_signal(
            **_base(ticker_in_value=False, earnings_warning=True, days_to_earnings=3)
        )
        assert sev == "HIGH"

    def test_insider_absent_high_entry_score(self):
        sev, reasons = score_exit_signal(
            **_base(insider_active=False, entry_score=70)
        )
        # Stays LOW per original code (documented as tautology bug)
        assert sev == "LOW"
        assert any("Sin insider buying activo" in r for r in reasons)

    def test_insider_absent_low_entry_score_no_alert(self):
        # entry 50 is not > 65, so no alert
        sev, reasons = score_exit_signal(
            **_base(insider_active=False, entry_score=50)
        )
        assert sev == "LOW"
        assert reasons == []

    def test_multiple_reasons_accumulate(self):
        sev, reasons = score_exit_signal(
            ticker_in_value=True, entry_score=80, current_score=55,
            earnings_warning=True, days_to_earnings=3,
            insider_active=False,
        )
        # Score drop 25 → HIGH; earnings doesn't downgrade; insider adds reason
        assert sev == "HIGH"
        assert len(reasons) == 3

    def test_ticker_not_in_value_beats_score_drop(self):
        # When ticker_in_value is False, we use the `elif` branch; score drop
        # is not also reported (only one of the two fires)
        sev, reasons = score_exit_signal(
            ticker_in_value=False, entry_score=80, current_score=50,
            earnings_warning=False, days_to_earnings=None,
            insider_active=True,
        )
        assert sev == "HIGH"
        # Only the "ya no aparece" reason, not also the score drop
        assert len(reasons) == 1
        assert "tesis posiblemente rota" in reasons[0]
