#!/usr/bin/env python3
"""Tests del verificador IA — sin red: se simula la respuesta de Claude."""
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_pick_verifier as v


ROWS = [
    {'ticker': 'MCO', 'value_score': 69.5, 'fcf_yield_pct': 3.11, 'current_price': 478.38},
    {'ticker': 'ATLKY', 'value_score': 79.0, 'fcf_yield_pct': 25.05, 'current_price': 21.22},
]


class TestVerifyPicks:
    def test_parses_verdicts(self):
        fake = '{"resultados": [{"ticker": "MCO", "veredicto": "OK", "problemas": []}, ' \
               '{"ticker": "ATLKY", "veredicto": "BLOCK", "problemas": ["FCF yield del 25% sugiere divisa sin convertir"]}]}'
        with patch.object(v, 'claude_chat', return_value=fake):
            out = v.verify_picks(ROWS)
        assert out['MCO']['veredicto'] == 'OK'
        assert out['ATLKY']['veredicto'] == 'BLOCK'

    def test_strips_markdown_fence(self):
        fake = '```json\n{"resultados": [{"ticker": "MCO", "veredicto": "OK"}]}\n```'
        with patch.object(v, 'claude_chat', return_value=fake):
            assert v.verify_picks(ROWS)['MCO']['veredicto'] == 'OK'

    def test_api_down_does_not_block_anything(self):
        with patch.object(v, 'claude_chat', return_value=None):
            assert v.verify_picks(ROWS) == {}

    def test_garbage_response_does_not_block_anything(self):
        with patch.object(v, 'claude_chat', return_value='lo siento, no puedo'):
            assert v.verify_picks(ROWS) == {}

    def test_unknown_verdict_downgraded_to_warn(self):
        fake = '{"resultados": [{"ticker": "MCO", "veredicto": "PERFECTO"}]}'
        with patch.object(v, 'claude_chat', return_value=fake):
            assert v.verify_picks(ROWS)['MCO']['veredicto'] == 'WARN'

    def test_empty_input_skips_the_call(self):
        with patch.object(v, 'claude_chat', side_effect=AssertionError('no debe llamarse')):
            assert v.verify_picks([]) == {}


class TestApplyVerdicts:
    def test_removes_only_blocked(self):
        df = pd.DataFrame(ROWS)
        out, blocked = v.apply_verdicts(df, {'ATLKY': {'veredicto': 'BLOCK', 'problemas': []}})
        assert list(out['ticker']) == ['MCO']
        assert blocked == ['ATLKY']

    def test_warn_stays_in_the_list(self):
        df = pd.DataFrame(ROWS)
        out, blocked = v.apply_verdicts(df, {'ATLKY': {'veredicto': 'WARN', 'problemas': []}})
        assert len(out) == 2 and blocked == []

    def test_no_verdicts_leaves_list_untouched(self):
        # La IA veta, no autoriza: sin veredictos la lista sale entera
        df = pd.DataFrame(ROWS)
        out, blocked = v.apply_verdicts(df, {})
        assert len(out) == 2 and blocked == []


class TestElVacioDeliberado:
    """El auditor sacó de la lista a BR, MSFT, MA, COST, V, INTU y cinco más.

    17-sep-2026: once de veinticinco fichas bloqueadas, y once veces el mismo
    motivo — «upside_triangulated_pct es NaN pero modelos_acuerdo dice
    CONTRADICEN». Tenía razón en que el hueco estaba; lo que no sabía es que lo
    habíamos puesto nosotros la tarde anterior, a propósito: cuando el DCF dice
    barata y el P/E dice cara, su mediana no estima nada y no se publica.

    BR sacaba 87,8/100, la segunda mejor de la lista. No eran once empresas
    malas: era un campo de la ficha sin explicar.
    """

    def test_el_hueco_a_proposito_va_explicado_no_vacio(self):
        import ai_pick_verifier as v
        f = v._ficha({'ticker': 'BR', 'modelos_acuerdo': 'CONTRADICEN',
                      'upside_triangulated_pct': float('nan')})
        assert 'a propósito' in f['upside_triangulated_pct']

    def test_un_hueco_sin_motivo_se_calla_no_se_inventa(self):
        """Si los modelos NO se contradicen, el NaN no tiene excusa: se omite
        en vez de mandar una explicación que no aplica."""
        import ai_pick_verifier as v
        f = v._ficha({'ticker': 'BR', 'modelos_acuerdo': 'COHERENTES',
                      'upside_triangulated_pct': float('nan')})
        assert 'upside_triangulated_pct' not in f

    def test_ningun_nan_llega_al_modelo(self):
        """`json.dumps` escribe el NaN como el literal `NaN`, que ni es JSON
        válido ni significa nada para quien lo lee."""
        import json

        import ai_pick_verifier as v
        f = v._ficha({'ticker': 'BR', 'peg_ratio': float('nan'),
                      'fcf_yield_pct': 6.2, 'dividend_yield_pct': None})
        crudo = json.dumps([f], ensure_ascii=False, allow_nan=False)
        assert 'NaN' not in crudo
        assert f['fcf_yield_pct'] == 6.2

    def test_el_prompt_le_cuenta_que_los_dos_flags_miden_cosas_distintas(self):
        """`modelos_acuerdo` es DCF contra P/E; `upside_divergence` es el
        analista contra los dos. KO y COST se bloquearon por leerlos como si
        fueran el mismo."""
        import ai_pick_verifier as v
        assert 'modelos_acuerdo' in v.SYSTEM and 'upside_divergence' in v.SYSTEM
        assert 'CONTRADICEN' in v.SYSTEM

    def test_los_campos_con_vacio_deliberado_se_le_ensenan_al_auditor(self):
        """Explicar un campo que la ficha no manda no sirve de nada."""
        import ai_pick_verifier as v
        for campo in v._VACIO_DELIBERADO:
            assert campo in v.FICHA_FIELDS
