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

    def test_dividend_yield_lowers_delta(self):
        # Una dividendera (q>0) tiene menos delta que la misma call sin dividendo —
        # el forward price es más bajo, así que ITM real es menor de lo que parece.
        d_no_div = la.bs_call_delta(100, 70, 1.5, 0.04, 0.35, div_yield=0.0)
        d_with_div = la.bs_call_delta(100, 70, 1.5, 0.04, 0.35, div_yield=0.04)
        assert d_with_div < d_no_div

    def test_dividend_yield_defaults_to_zero(self):
        # Omitir div_yield debe dar exactamente el mismo resultado que pasar 0.0
        # (no debe romper ninguna llamada existente que no conozca el dividendo)
        d_default = la.bs_call_delta(100, 70, 1.5, 0.04, 0.35)
        d_explicit_zero = la.bs_call_delta(100, 70, 1.5, 0.04, 0.35, div_yield=0.0)
        assert d_default == d_explicit_zero


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

    def test_dividend_yield_lowers_reported_leverage(self):
        # Una dividendera reporta menos leverage que la misma call sin dividendo —
        # antes de este fix, el leverage de bancos/energía salía sobreestimado.
        no_div = la.leaps_metrics(spot=100, strike=70, t_years=1.5, premium=35, iv=0.35, div_yield=0.0)
        with_div = la.leaps_metrics(spot=100, strike=70, t_years=1.5, premium=35, iv=0.35, div_yield=0.04)
        assert with_div['delta'] < no_div['delta']
        assert with_div['leverage'] < no_div['leverage']

    def test_total_annual_cost_includes_forgone_dividend(self):
        # El coste real de holding = carry + dividendo renunciado. En una
        # dividendera al 4%, un carry del ~3% es en realidad ~7%/año.
        no_div = la.leaps_metrics(spot=100, strike=70, t_years=1.5, premium=35, iv=0.35, div_yield=0.0)
        with_div = la.leaps_metrics(spot=100, strike=70, t_years=1.5, premium=35, iv=0.35, div_yield=0.04)
        assert no_div['forgone_dividend_pct'] == 0.0
        assert no_div['total_annual_cost_pct'] == no_div['annual_carry_pct']
        assert with_div['forgone_dividend_pct'] == 4.0
        assert abs(with_div['total_annual_cost_pct']
                   - (with_div['annual_carry_pct'] + 4.0)) < 0.01


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

    def test_situation_shifts_score(self):
        # Filosofía value: caída circunstancial sube, dip de ganador baja
        caida = la.opportunity_score(70, 60, 70, 30, 'CAIDA_CIRCUNSTANCIAL')
        base  = la.opportunity_score(70, 60, 70, 30, None)
        dip   = la.opportunity_score(70, 60, 70, 30, 'DIP_GANADOR')
        assert caida > base > dip

    def test_weighted_combination_in_range(self):
        s = la.opportunity_score(80, 80, 80, None)
        assert 0 <= s <= 100
        # 0.34*80 + 0.28*80 + 0.38*80 = 80
        assert s == pytest.approx(80.0, abs=0.5)


# ── Clasificador de situación (filosofía value aplicada a LEAPS) ─────────────

class TestClassifySituation:
    def test_caida_circunstancial(self):
        # Caída fuerte desde máximos, fundamentales intactos, con upside, sin haber subido en el año
        assert la.classify_situation(-30, 2, 70, 20, 65) == 'CAIDA_CIRCUNSTANCIAL'

    def test_calidad_razonable(self):
        # No se ha disparado ni hundido, negocio sólido
        assert la.classify_situation(-8, -5, 70, 25, 65) == 'CALIDAD_RAZONABLE'

    def test_en_maximos_multiplo_sano_es_calidad(self):
        # En máximos pero a múltiplo razonable (el caro se filtra antes) → no se penaliza
        assert la.classify_situation(-0.7, 1.5, 69, 14, 60) == 'CALIDAD_RAZONABLE'

    def test_dip_de_ganador(self):
        # Subió mucho en el año y ahora corrige (pero no pegada al máximo)
        assert la.classify_situation(-13, 18, 62, 16, 60) == 'DIP_GANADOR'

    def test_deterioro_por_fundamental(self):
        assert la.classify_situation(-25, -10, 40, 20, 35) == 'DETERIORO'

    def test_deterioro_por_negative_roe(self):
        assert la.classify_situation(-25, -5, 70, 20, 65, negative_roe=True) == 'DETERIORO'

    def test_fundamental_50_es_dato_ausente(self):
        # 50.0 exacto = dato ausente → no cuenta como deterioro ni como calidad fuerte
        assert la.classify_situation(-30, 2, 50.0, 20, None) == 'CAIDA_CIRCUNSTANCIAL'


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


# ─── Máximo de 52 semanas: High, no Close ──────────────────────────────────────
# El 5-ago-2026 UNH salía a -6.1% de máximos cuando la distancia real era
# -11.7%: el cálculo usaba h['Close'].max() en vez de h['High'].max(). Un día
# tocó $461.62 intradía y cerró más abajo — Close.max() nunca ve ese pico.
# Verificado contra yfinance real: High.max()=461.62 (16-jul) vs
# Close.max()=436.35 (21-jul, día distinto).

class TestGetPriceContext:
    def test_usa_high_no_close_para_el_maximo(self):
        import pandas as pd

        class _FakeTicker:
            def history(self, period='1y'):
                idx = pd.date_range('2025-08-01', periods=5, freq='D')
                return pd.DataFrame({
                    'Close': [400.0, 410.0, 436.35, 420.0, 407.55],
                    'High':  [405.0, 415.0, 440.0,  461.62, 412.0],
                }, index=idx)

        pct_from_high, ytd, hv = la._get_price_context(_FakeTicker())
        # Con High.max()=461.62 y precio actual 407.55:
        esperado = round((407.55 - 461.62) / 461.62 * 100, 1)
        assert pct_from_high == esperado
        assert pct_from_high < round((407.55 - 436.35) / 436.35 * 100, 1)  # más negativo que con Close

    def test_sin_columna_high_cae_a_close(self):
        import pandas as pd
        idx = pd.date_range('2025-08-01', periods=3, freq='D')

        class _FakeTicker:
            def history(self, period='1y'):
                return pd.DataFrame({'Close': [100.0, 110.0, 95.0]}, index=idx)

        pct_from_high, _, _ = la._get_price_context(_FakeTicker())
        assert pct_from_high == round((95.0 - 110.0) / 110.0 * 100, 1)

    def test_historial_vacio_no_rompe(self):
        import pandas as pd

        class _FakeTicker:
            def history(self, period='1y'):
                return pd.DataFrame()

        assert la._get_price_context(_FakeTicker()) == (None, None, None)


# ─── Prompt de narrativa: sin fact-checking de memoria ─────────────────────────
# El prompt le pedía a Claude "con tu conocimiento de la empresa, comprueba si
# son plausibles" — sin herramienta de búsqueda, eso es pedirle que recuerde
# precios históricos. Produjo una alucinación confirmada: UNH con YTD +23.5%
# (correcto) "corregido" por Claude a -19% comparando contra el cierre de 2024
# en vez del de 2025. El prompt ahora prohíbe explícitamente ese fact-checking
# de memoria y limita data_check a coherencia aritmética entre los números que
# se le dan.

class TestPromptNoFactChecking:
    def _build_prompt(self):
        opp = {
            'ticker': 'TEST', 'company_name': 'Test Co', 'sector': 'Tech',
            'spot': 100.0, 'quality_score': 70, 'analyst_upside_pct': 15.0,
            'pct_from_52w_high': -10.0, 'ytd_pct': 5.0, 'forward_pe': 20.0,
            'trailing_pe': 22.0, 'situation': 'CALIDAD_RAZONABLE',
            'recommended_contract': {
                'strike': 90.0, 'expiry': '2028-01-01', 't_years': 1.5,
                'mid': 15.0, 'cost_per_contract': 1500.0, 'delta': 0.8,
                'leverage': 1.5, 'annual_carry_pct': 4.0,
                'total_annual_cost_pct': 5.0, 'forgone_dividend_pct': 1.0,
                'iv_pct': 30.0, 'iv_richness': 'normal', 'iv_vs_hv': 1.1,
                'roundtrip_spread_usd': 50, 'volume': 20,
                'breakeven': 105.0, 'breakeven_move_pct': 5.0,
            },
            'profit_at_target': {},
        }
        captured = {}

        def _fake_claude_chat(messages, model=None, max_tokens=None, temperature=None):
            captured['prompt'] = messages[0]['content']
            return None  # no hace falta respuesta real, solo capturar el prompt

        import groq_utils
        from unittest.mock import patch
        with patch.object(groq_utils, 'claude_chat', _fake_claude_chat):
            la.add_ai_narrative(opp)
        return captured.get('prompt', '')

    def test_prohibe_explicitamente_el_fact_checking_de_memoria(self):
        prompt = self._build_prompt()
        assert 'NO tienes acceso a precios de mercado en tiempo real' in prompt
        assert 'NUNCA compares' in prompt

    def test_ya_no_invita_a_usar_conocimiento_de_la_empresa(self):
        # La instrucción vieja que causó la alucinación no debe seguir ahí
        prompt = self._build_prompt()
        assert 'con tu conocimiento de la empresa, comprueba si son PLAUSIBLES' not in prompt

    def test_data_check_se_limita_a_coherencia_interna(self):
        prompt = self._build_prompt()
        assert 'COHERENCIA ARITMÉTICA ENTRE LOS NÚMEROS QUE TE DOY' in prompt


class TestVentajaNeta:
    """Lo que decide un LEAPS es cuánto te llevas de MÁS que comprando la
    acción, ya pagado el spread — no el rendimiento bruto de la opción.

    El 18-ago-2026 AXP salía 7ª de 11 con `leverage 2,5x` en la ficha. Su
    ventaja bruta sobre comprar acciones eran $342 y el spread de ida y vuelta
    $335: quedaban SIETE dólares por arriesgar los $11.018 de prima completos.
    Medido sobre las 11 oportunidades, `opportunity_score` correlacionaba con
    el valor real un +0,26 (p=0,45) — nada. Con la ventaja neta, +0,75.
    """

    def test_el_spread_se_descuenta(self):
        from leaps_analyzer import ventaja_neta_pct
        # AXP real: prima 11.018, opción +14,2%, acción +11,1%, spread 335
        v = ventaja_neta_pct(11018, 14.2, 11.1, 335)
        assert v is not None and abs(v - 0.06) < 0.15, f'esperaba ~0, salió {v}'

    def test_sin_spread_la_ventaja_es_la_diferencia(self):
        from leaps_analyzer import ventaja_neta_pct
        assert ventaja_neta_pct(10000, 20.0, 10.0, 0) == 10.0

    def test_puede_ser_negativa(self):
        """SAP y OXY salían perdiendo frente a comprar la acción."""
        from leaps_analyzer import ventaja_neta_pct
        assert ventaja_neta_pct(7625, 15.0, 14.0, 450) < 0

    def test_sin_datos_no_inventa(self):
        from leaps_analyzer import ventaja_neta_pct
        assert ventaja_neta_pct(None, 14.0, 11.0, 300) is None
        assert ventaja_neta_pct(11018, None, 11.0, 300) is None
        assert ventaja_neta_pct(0, 14.0, 11.0, 300) is None

    def test_una_ventaja_negativa_RESTA_en_el_score(self):
        """Si sales perdiendo frente a la acción, el contrato no es una
        oportunidad — antes el score solo sabía sumar."""
        from leaps_analyzer import opportunity_score
        bueno = opportunity_score(70, 60, 80, 14.2, None, ventaja_neta=20.0)
        malo = opportunity_score(70, 60, 80, 14.2, None, ventaja_neta=-9.0)
        assert bueno > malo
        assert malo < opportunity_score(70, 60, 80, 14.2, None, ventaja_neta=0.0)

    def test_sin_ventaja_neta_cae_al_bruto_pero_con_menos_peso(self):
        """Sin precio objetivo o sin spread no se puede calcular; el score usa
        el bruto pero con tope más bajo, para no fiarse de una peor medida."""
        from leaps_analyzer import opportunity_score
        con = opportunity_score(70, 60, 80, 60.0, None, ventaja_neta=20.0)
        sin = opportunity_score(70, 60, 80, 60.0, None, ventaja_neta=None)
        assert con > sin
