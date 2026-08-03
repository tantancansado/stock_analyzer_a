#!/usr/bin/env python3
"""Tests del fetcher con procedencia — un dato sin fuente no entra."""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_data_fetcher import _extract_json, _validated_entry, to_scalar


def _entry(**over):
    e = {'value': 25972000000, 'currency': 'SEK', 'period': 'TTM',
         'as_of': '2026-06-30', 'source_url': 'https://www.atlascopcogroup.com/report'}
    e.update(over)
    return e


class TestValidatedEntry:
    def test_complete_entry_accepted(self):
        val, why = _validated_entry(_entry())
        assert val['value'] == 25972000000 and val['currency'] == 'SEK'
        assert why == ''

    def test_bare_number_rejected(self):
        # El formato antiguo: un float suelto. Sin fuente no se distingue de
        # un dato recordado, así que no entra.
        val, why = _validated_entry(25972000000)
        assert val is None and 'sin fuente' in why

    def test_missing_source_url_rejected(self):
        val, why = _validated_entry(_entry(source_url=''))
        assert val is None and 'URL' in why

    def test_non_http_source_rejected(self):
        val, why = _validated_entry(_entry(source_url='segun mis datos'))
        assert val is None

    def test_missing_period_rejected(self):
        val, why = _validated_entry(_entry(period=None))
        assert val is None and 'periodo' in why

    def test_non_numeric_value_rejected(self):
        assert _validated_entry(_entry(value='mucho'))[0] is None

    def test_null_entry_is_not_an_error(self):
        val, why = _validated_entry(None)
        assert val is None and why == ''

    def test_currency_optional_for_ratios(self):
        val, _ = _validated_entry(_entry(currency=None, value=0.12))
        assert val['currency'] is None and val['value'] == 0.12


class TestExtractJson:
    def test_handles_nested_objects(self):
        raw = '{"freeCashflow": {"value": 1, "source_url": "https://x.com"}}'
        assert _extract_json(raw)['freeCashflow']['value'] == 1

    def test_strips_markdown_fence(self):
        raw = '```json\n{"a": {"value": 2}}\n```'
        assert _extract_json(raw)['a']['value'] == 2

    def test_ignores_surrounding_prose(self):
        raw = 'He buscado y esto es lo que encuentro:\n{"a": {"value": 3}}\nEspero que sirva.'
        assert _extract_json(raw)['a']['value'] == 3

    def test_garbage_returns_empty(self):
        assert _extract_json('no he encontrado nada') == {}


class TestToScalar:
    def test_converts_declared_currency(self):
        # El caso ATLKY: la fuente da SEK y el ticker cotiza en USD
        with patch('currency_normalizer.get_fx_rate', return_value=0.1048):
            out = to_scalar({'freeCashflow': _entry()}, 'USD')
        assert abs(out['freeCashflow'] - 25972000000 * 0.1048) < 1

    def test_same_currency_passes_through(self):
        out = to_scalar({'freeCashflow': _entry(currency='USD')}, 'USD')
        assert out['freeCashflow'] == 25972000000

    def test_ratio_without_currency_passes_through(self):
        out = to_scalar({'earningsGrowth': _entry(currency=None, value=0.12)}, 'USD')
        assert out['earningsGrowth'] == 0.12

    def test_discards_when_no_fx_available(self):
        # Antes un hueco que un número en la divisa equivocada
        with patch('currency_normalizer.get_fx_rate', return_value=None):
            out = to_scalar({'freeCashflow': _entry()}, 'USD')
        assert out['freeCashflow'] is None
