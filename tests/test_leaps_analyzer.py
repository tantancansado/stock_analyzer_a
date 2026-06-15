#!/usr/bin/env python3
"""
Tests para la matemática LEAPS — funciones puras de leaps_analyzer.py.

Validan greeks Black-Scholes, métricas del contrato (extrínseco, carry, leverage,
break-even) y el scoring. Si alguien cambia los umbrales (delta band, MAX_CARRY,
pesos del opportunity_score) sin querer, aquí salta.

No tocan red ni ficheros (solo funciones puras + math).
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import leaps_analyzer as la


# ── Black-Scholes delta ──────────────────────────────────────────────────────

class TestBsDelta:
    def test_deep_itm_call_delta_near_one(self):
        # Strike muy por debajo del spot → delta cerca de 1
        d = la.bs_call_delta(spot=100, strike=50, t_years=1.5, rate=0.04, iv=0.4)
        assert 0.90 < d < 1.0

    def test_atm_call_delta_above_half(self):
        # ATM con drift positivo (rate>0, T largo) → delta algo > 0.5
        d = la.bs_call_delta(spot=100, strike=100, t_years=1.5, rate=0.04, iv=0.4)
        assert 0.55 < d < 0.75

    def test_otm_call_delta_below_half(self):
        d = la.bs_call_delta(spot=100, strike=130, t_years=1.5, rate=0.04, iv=0.4)
        assert d < 0.5

    def test_invalid_inputs_return_nan(self):
        assert math.isnan(la.bs_call_delta(100, 50, 1.5, 0.04, 0))      # iv=0
        assert math.isnan(la.bs_call_delta(100, 50, 0, 0.04, 0.4))      # T=0
        assert math.isnan(la.bs_call_delta(0, 50, 1.5, 0.04, 0.4))      # spot=0

    def test_delta_monotonic_in_strike(self):
        # A menor strike, mayor delta
        d_low = la.bs_call_delta(100, 60, 1.5, 0.04, 0.4)
        d_high = la.bs_call_delta(100, 90, 1.5, 0.04, 0.4)
        assert d_low > d_high


# ── Métricas del contrato ────────────────────────────────────────────────────

class TestLeapsMetrics:
    def test_intrinsic_and_extrinsic_split(self):
        # spot 100, strike 70, prima 35 → intrínseco 30, extrínseco 5
        m = la.leaps_metrics(spot=100, strike=70, t_years=1.0, premium=35, iv=0.4)
        assert m['intrinsic'] == 30.0
        assert m['extrinsic'] == 5.0
        assert m['extrinsic_pct'] == 5.0   # 5/100

    def test_annual_carry_divides_by_years(self):
        # extrínseco 5% en 2 años → 2.5%/año
        m = la.leaps_metrics(spot=100, strike=70, t_years=2.0, premium=35, iv=0.4)
        assert m['extrinsic_pct'] == 5.0
        assert m['annual_carry_pct'] == 2.5

    def test_leverage_formula(self):
        # leverage = spot*delta / premium
        m = la.leaps_metrics(spot=100, strike=70, t_years=1.5, premium=35, iv=0.4)
        expected = (100 * m['delta']) / 35
        assert m['leverage'] == pytest.approx(round(expected, 2))
        assert 2.0 < m['leverage'] < 3.0

    def test_breakeven_is_strike_plus_premium(self):
        m = la.leaps_metrics(spot=100, strike=70, t_years=1.5, premium=35, iv=0.4)
        assert m['breakeven'] == 105.0
        assert m['breakeven_move_pct'] == 5.0   # (105-100)/100

    def test_premium_below_intrinsic_clamps_extrinsic_to_zero(self):
        # prima por debajo del intrínseco (arbitraje teórico) → extrínseco 0, no negativo
        m = la.leaps_metrics(spot=100, strike=70, t_years=1.0, premium=28, iv=0.4)
        assert m['extrinsic'] == 0.0
        assert m['annual_carry_pct'] == 0.0


# ── Scoring del contrato ─────────────────────────────────────────────────────

class TestContractScore:
    def _metrics(self, delta, carry, leverage):
        return {'delta': delta, 'annual_carry_pct': carry, 'leverage': leverage}

    def test_ideal_contract_scores_high(self):
        # delta sweet spot, carry barato, leverage ideal, buena liquidez
        s = la.score_contract(self._metrics(0.80, 3.0, 2.1), open_interest=600, spread_pct=4)
        assert s > 90

    def test_expensive_carry_scores_lower(self):
        cheap = la.score_contract(self._metrics(0.80, 3.0, 2.1), 600, 4)
        pricey = la.score_contract(self._metrics(0.80, 13.0, 2.1), 600, 4)
        assert pricey < cheap

    def test_far_from_sweet_delta_penalized(self):
        good = la.score_contract(self._metrics(0.80, 5.0, 2.1), 600, 4)
        deep = la.score_contract(self._metrics(0.95, 5.0, 1.3), 600, 4)
        assert deep < good

    def test_missing_metrics_returns_zero(self):
        assert la.score_contract({'delta': None, 'annual_carry_pct': 5, 'leverage': 2}, 600, 4) == 0.0


# ── Quality score (regla del proyecto: 50.0 = dato ausente) ──────────────────

class TestQualityScore:
    def test_fundamental_50_treated_as_missing(self):
        # Solo fundamental_score=50.0 → sin otra señal → None (no puntuar)
        assert la.quality_score({'fundamental_score': 50.0}) is None

    def test_fundamental_50_with_other_signals_still_scores(self):
        q = la.quality_score({'fundamental_score': 50.0, 'financial_health_score': 80,
                              'conviction_grade': 'A'})
        assert q is not None and q > 0

    def test_real_fundamental_scores(self):
        q = la.quality_score({'fundamental_score': 75.0})
        assert q == pytest.approx(75.0, abs=0.1)

    def test_no_data_returns_none(self):
        assert la.quality_score({}) is None

    def test_conviction_grade_lifts_score(self):
        base = la.quality_score({'fundamental_score': 60.0})
        with_grade = la.quality_score({'fundamental_score': 60.0, 'conviction_grade': 'A+'})
        assert with_grade > base


# ── Timing score ─────────────────────────────────────────────────────────────

class TestTimingScore:
    def test_uptrend_stage2_bullish_scores_high(self):
        t = la.timing_score({'trend_direction': 'uptrend', 'is_stage2': True,
                             'technical_bias': 'bullish', 'entry_verdict': 'ENTER'})
        assert t > 80

    def test_downtrend_avoid_scores_low(self):
        t = la.timing_score({'trend_direction': 'downtrend', 'technical_bias': 'bearish',
                             'entry_verdict': 'AVOID'})
        assert t < 30

    def test_neutral_is_midrange(self):
        assert 45 <= la.timing_score({}) <= 55

    def test_at_52w_high_penalized(self):
        chasing = la.timing_score({'proximity_to_52w_high': 99})
        healthy = la.timing_score({'proximity_to_52w_high': 85})
        assert chasing < healthy

    def test_bounded_0_100(self):
        # Acumular todos los negativos no baja de 0
        t = la.timing_score({'trend_direction': 'downtrend', 'technical_bias': 'bearish',
                            'entry_verdict': 'AVOID', 'proximity_to_52w_high': 99})
        assert 0 <= t <= 100


# ── Opportunity score (combinación + reglas del proyecto) ────────────────────

class TestOpportunityScore:
    def test_no_quality_means_no_opportunity(self):
        # Regla del proyecto: sin calidad medible no inventamos score
        assert la.opportunity_score(None, 80, 90, 20) == 0.0

    def test_target_return_adds_bonus(self):
        # El reward escala con el rendimiento apalancado en el escenario alcista
        no_ret = la.opportunity_score(70, 60, 70, None)
        with_ret = la.opportunity_score(70, 60, 70, 40)   # +40% al target
        assert with_ret > no_ret

    def test_negative_target_return_no_bonus(self):
        # Rendimiento <=0 al target no suma (esas oportunidades se filtran antes)
        neg = la.opportunity_score(70, 60, 70, -13)
        base = la.opportunity_score(70, 60, 70, None)
        assert neg == base

    def test_target_bonus_capped(self):
        # El bonus por rendimiento al target está topado en 15 pts (+60% → 15)
        huge = la.opportunity_score(70, 60, 70, 200)
        cap  = la.opportunity_score(70, 60, 70, 60)
        assert huge == cap

    def test_weighted_combination_in_range(self):
        s = la.opportunity_score(80, 80, 80, None)
        assert 0 <= s <= 100
        # 0.34*80 + 0.28*80 + 0.38*80 = 80
        assert s == pytest.approx(80.0, abs=0.5)


# ── Sincronización con el source (umbrales críticos) ─────────────────────────

class TestSourceConstants:
    def test_delta_band_and_carry_thresholds(self):
        assert la.DELTA_MIN == 0.70
        assert la.DELTA_MAX == 0.92
        assert la.MAX_CARRY_PCT == 14.0
        assert la.MIN_DTE >= 365   # LEAPS = >1 año

    def test_min_target_return_filter_exists(self):
        # Debe exigirse un rendimiento mínimo positivo en el escenario alcista
        assert la.MIN_TARGET_RETURN_PCT > 0
