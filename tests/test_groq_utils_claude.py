#!/usr/bin/env python3
"""Contrato de claude_chat: qué modelos aceptan temperature, y fail-open."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import groq_utils as g


def _resp(texto='ok'):
    bloque = MagicMock()
    bloque.type = 'text'
    bloque.text = texto
    r = MagicMock()
    r.content = [bloque]
    return r


def _llamar(model):
    c = MagicMock()
    c.messages.create.return_value = _resp()
    with patch.object(g, '_get_anthropic_client', return_value=c):
        g.claude_chat([{'role': 'user', 'content': 'x'}], model=model)
    return c.messages.create.call_args.kwargs


class TestSamplingPorModelo:
    def test_sonnet5_sin_temperature(self):
        # Sonnet 5 devuelve 400 si recibe temperature. daily_briefing lo usa,
        # así que mandarla habría roto el briefing en su primer envío.
        kw = _llamar('claude-sonnet-5')
        assert 'temperature' not in kw
        assert kw['thinking'] == {'type': 'adaptive'}

    def test_opus5_sin_temperature(self):
        assert 'temperature' not in _llamar(g.CLAUDE_OPUS)

    def test_haiku_conserva_temperature(self):
        assert 'temperature' in _llamar('claude-haiku-4-5')

    def test_sonnet46_conserva_temperature(self):
        assert 'temperature' in _llamar('claude-sonnet-4-6')

    def test_no_se_decide_por_la_palabra_opus(self):
        # El bug original miraba "opus" in model — Sonnet 5 se colaba
        assert 'temperature' not in _llamar('claude-sonnet-5')
        assert 'temperature' in _llamar('claude-haiku-4-5')


class TestFailOpen:
    def test_api_caida_devuelve_none(self):
        # Propagar aquí tumbaría el paso crítico del pipeline
        c = MagicMock()
        c.messages.create.side_effect = RuntimeError('API caída')
        with patch.object(g, '_get_anthropic_client', return_value=c):
            assert g.claude_chat([{'role': 'user', 'content': 'x'}],
                                 model='claude-sonnet-5') is None

    def test_sin_api_key_devuelve_none(self):
        with patch.object(g, '_get_anthropic_client', return_value=None):
            assert g.claude_chat([{'role': 'user', 'content': 'x'}]) is None


class TestModelosActuales:
    def test_apuntan_a_la_generacion_5(self):
        assert g.CLAUDE_SONNET == 'claude-sonnet-5'
        assert g.CLAUDE_OPUS == 'claude-opus-5'
