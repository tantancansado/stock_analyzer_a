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
