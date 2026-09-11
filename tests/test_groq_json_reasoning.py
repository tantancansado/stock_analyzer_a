#!/usr/bin/env python3
"""El JSON no cabía: razonamiento y respuesta comparten presupuesto.

11-sep-2026. Todos los modelos de la cadena Groq (gpt-oss 120b/20b, qwen3.6)
son de razonamiento. Con `response_format=json_object` y un tope corto
(200-500 tokens en 8 módulos distintos) el pensamiento consumía el
presupuesto entero y la generación salía VACÍA: Groq devolvía 400
`json_validate_failed` con `failed_generation: ''`.

Un solo run del pipeline: 203 llamadas rotas en 8 pasos — Chart Analyzer,
Owner Earnings, Global Scanner, Entry Verdict, Cerebro, Contrarian, Mean
Reversion y Strategy Agent. Más el gate europeo al 100% (0/33), que ni
aparecía en el recuento porque su `except` mudo se tragaba el error.

La trampa del arreglo: los dos grupos de modelos aceptan conjuntos DISJUNTOS
de `reasoning_effort` y groq_chat hace fallback de uno a otro sobre la
marcha. Un valor fijo para toda la cadena es un 400 nuevo en lugar del viejo.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import groq_utils as gu


class _Cliente:
    """Cliente falso que registra los kwargs de cada intento."""

    def __init__(self, fallan: set[str] | None = None):
        self.llamadas: list[dict] = []
        self.fallan = fallan or set()
        self.chat = type('c', (), {'completions': self})()

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        if kwargs['model'] in self.fallan:
            raise RuntimeError('rate_limit_exceeded: quota')
        return 'respuesta'


JSON = {'type': 'json_object'}


class TestEsfuerzoPorModelo:
    """Los conjuntos válidos son disjuntos — cruzarlos es un 400."""

    def test_qwen_solo_acepta_none(self):
        assert gu._esfuerzo_para('qwen/qwen3.6-27b') == 'none'

    @pytest.mark.parametrize('modelo', ['openai/gpt-oss-120b', 'openai/gpt-oss-20b'])
    def test_gpt_oss_no_puede_recibir_none(self, modelo):
        v = gu._esfuerzo_para(modelo)
        assert v == 'low'
        assert v != 'none', 'gpt-oss NO acepta "none" — sería un 400'

    def test_qwen_no_puede_recibir_low(self):
        assert gu._esfuerzo_para('qwen/qwen3.6-27b') not in ('low', 'medium', 'high'), \
            'qwen NO acepta low/medium/high — sería un 400'

    def test_modelo_desconocido_no_lleva_parametro(self):
        assert gu._esfuerzo_para('meta/algo-nuevo-42b') is None, \
            'ante un modelo que no conocemos, no mandar el parámetro'


class TestPresupuestoDelJson:
    def test_json_sube_el_tope_hasta_el_suelo(self):
        c = _Cliente()
        gu.groq_chat(c, [{'role': 'user', 'content': 'x'}],
                     model=gu.SCOUT_PRIMARY, max_tokens=500, response_format=JSON)
        assert c.llamadas[0]['max_tokens'] >= gu.MIN_TOKENS_JSON
        assert c.llamadas[0]['reasoning_effort'] == 'none'

    def test_no_recorta_un_tope_ya_generoso(self):
        c = _Cliente()
        gu.groq_chat(c, [{'role': 'user', 'content': 'x'}],
                     model=gu.SCOUT_PRIMARY, max_tokens=8000, response_format=JSON)
        assert c.llamadas[0]['max_tokens'] == 8000

    def test_sin_json_no_se_toca_nada(self):
        c = _Cliente()
        gu.groq_chat(c, [{'role': 'user', 'content': 'x'}],
                     model=gu.PRIMARY_MODEL, max_tokens=80)
        assert c.llamadas[0]['max_tokens'] == 80, 'una llamada de texto libre no cambia'
        assert 'reasoning_effort' not in c.llamadas[0]


class TestFallbackEntreFamilias:
    """El caso que convierte el arreglo en un bug nuevo si se hace mal."""

    def test_el_esfuerzo_se_recalcula_al_cambiar_de_modelo(self):
        # qwen agotado -> cae a gpt-oss-20b, que NO acepta el 'none' de qwen
        c = _Cliente(fallan={'qwen/qwen3.6-27b'})
        gu.groq_chat(c, [{'role': 'user', 'content': 'x'}],
                     model=gu.SCOUT_PRIMARY, max_tokens=500, response_format=JSON)
        assert len(c.llamadas) == 2
        assert c.llamadas[0]['reasoning_effort'] == 'none'
        assert c.llamadas[1]['model'].startswith('openai/gpt-oss')
        assert c.llamadas[1]['reasoning_effort'] == 'low', \
            'arrastrar el "none" de qwen a gpt-oss cambia un 400 por otro'

    def test_el_suelo_tambien_se_aplica_al_de_reserva(self):
        c = _Cliente(fallan={'qwen/qwen3.6-27b'})
        gu.groq_chat(c, [{'role': 'user', 'content': 'x'}],
                     model=gu.SCOUT_PRIMARY, max_tokens=200, response_format=JSON)
        assert all(l['max_tokens'] >= gu.MIN_TOKENS_JSON for l in c.llamadas)
