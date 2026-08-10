#!/usr/bin/env python3
"""Tests del cliente de búsqueda con Claude — sin red.

Cubren el contrato de las herramientas de servidor, donde los fallos NO llegan
como excepción: un error de búsqueda es un HTTP 200 con un bloque cuyo `content`
es un objeto de error, y un turno a medias llega como `stop_reason: pause_turn`.
"""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import claude_research as cr


def _text(t):
    return SimpleNamespace(type='text', text=t)


def _search_ok(*urls):
    return SimpleNamespace(
        type='web_search_tool_result',
        content=[SimpleNamespace(type='web_search_result', url=u) for u in urls],
    )


def _search_error(code='max_uses_exceeded'):
    # En error `content` es un OBJETO, no una lista — iterarlo sin comprobar
    # el tipo revienta o inventa fuentes
    return SimpleNamespace(
        type='web_search_tool_result',
        content=SimpleNamespace(type='web_search_tool_result_error', error_code=code),
    )


def _response(content, stop_reason='end_turn'):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


def _client_returning(*responses):
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


class TestAskWithSearch:
    def test_devuelve_texto_y_urls_de_la_herramienta(self):
        resp = _response([_search_ok('https://a.com/x'), _text('{"veredicto": "CICLICO"}')])
        with patch.object(cr, '_get_client', return_value=_client_returning(resp)):
            texto, urls = cr.ask_with_search('p', 'sys')
        assert 'CICLICO' in texto and urls == ['https://a.com/x']

    def test_error_de_busqueda_no_revienta_ni_inventa_fuentes(self):
        resp = _response([_search_error(), _text('sin resultados')])
        with patch.object(cr, '_get_client', return_value=_client_returning(resp)):
            texto, urls = cr.ask_with_search('p', 'sys')
        assert urls == [] and 'sin resultados' in texto

    def test_pause_turn_no_se_reintenta_y_no_rompe(self):
        """MAX_CONTINUATIONS pasó a 1 el 10-ago-2026 por coste.

        Una continuación reenvía el contexto ENTERO — resultados de búsqueda
        incluidos, ~5k tokens cada uno — así que duplicaba el coste de entrada
        de cada ticker. Con el tope de $10/mes no compensa pagar el doble en
        todas las llamadas para salvar los pocos `pause_turn` que ocurren.
        El comportamiento correcto ahora es rendirse limpiamente: una sola
        llamada, y vacío, que el consumidor trata como "sin datos".
        """
        parcial = _response([_search_ok('https://a.com/1')], stop_reason='pause_turn')
        final = _response([_search_ok('https://a.com/2'), _text('listo')])
        client = _client_returning(parcial, final)
        with patch.object(cr, '_get_client', return_value=client):
            texto, urls = cr.ask_with_search('p', 'sys')
        assert client.messages.create.call_count == 1, 'no debe pagar una segunda llamada'
        assert (texto, urls) == ('', []), 'sin terminar = sin datos, no un veredicto a medias'

    def test_refusal_devuelve_vacio_sin_leer_contenido(self):
        # Los clasificadores devuelven 200 con content vacío o parcial
        resp = _response([], stop_reason='refusal')
        with patch.object(cr, '_get_client', return_value=_client_returning(resp)):
            assert cr.ask_with_search('p', 'sys') == ('', [])

    def test_sin_api_key_devuelve_vacio(self):
        with patch.object(cr, '_get_client', return_value=None):
            assert cr.ask_with_search('p', 'sys') == ('', [])

    def test_excepcion_no_propaga(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError('boom')
        with patch.object(cr, '_get_client', return_value=client):
            assert cr.ask_with_search('p', 'sys') == ('', [])

    def test_pause_turn_infinito_se_corta(self):
        pausas = [_response([_text('x')], stop_reason='pause_turn')] * 10
        with patch.object(cr, '_get_client', return_value=_client_returning(*pausas)):
            assert cr.ask_with_search('p', 'sys') == ('', [])


class TestParseJson:
    def test_json_plano(self):
        assert cr.parse_json('{"a": 1}')['a'] == 1

    def test_quita_el_fence_de_markdown(self):
        assert cr.parse_json('```json\n{"a": 2}\n```')['a'] == 2

    def test_ignora_prosa_alrededor(self):
        assert cr.parse_json('He buscado y esto sale:\n{"a": 3}\nEspero que sirva.')['a'] == 3

    def test_basura_devuelve_vacio(self):
        assert cr.parse_json('no he encontrado nada') == {}

    def test_texto_vacio(self):
        assert cr.parse_json('') == {}


class TestModelo:
    def test_por_defecto_sonnet(self):
        # La tarea es clasificar material ya recuperado, no razonar en cadena
        # larga: Sonnet rinde igual a la mitad de precio
        assert cr.MODEL == 'claude-sonnet-5'

    def test_se_puede_pedir_opus_por_llamada(self):
        resp = _response([_text('{"a": 1}')])
        client = _client_returning(resp)
        with patch.object(cr, '_get_client', return_value=client):
            cr.ask_with_search('p', 'sys', model=cr.MODEL_ANALISIS_PROFUNDO)
        assert client.messages.create.call_args.kwargs['model'] == 'claude-opus-5'

    def test_usa_el_modelo_por_defecto_si_no_se_indica(self):
        resp = _response([_text('{"a": 1}')])
        client = _client_returning(resp)
        with patch.object(cr, '_get_client', return_value=client):
            cr.ask_with_search('p', 'sys')
        assert client.messages.create.call_args.kwargs['model'] == cr.MODEL
