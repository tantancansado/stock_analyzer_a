#!/usr/bin/env python3
"""Tests para currency_normalizer.normalize_info.

Bug encontrado el 5-ago-2026 en el propio módulo: los campos "por acción"
(trailingEps, forwardEps, bookValue...) se multiplicaban por fx_to_major
como si vinieran en financialCurrency. Verificado cruzando price/trailingEps
contra trailingPE en 9 tickers reales con financialCurrency != currency
(DBOEY, ATLKY, ASAZY, JD, PDD, STLA, NIO, EXPN.L, AUTO.L): SIEMPRE cuadran
ya en la divisa de cotización. El único ajuste real es el ×100 de subunidad
(GBp/ZAc/ILA), independiente de cualquier tipo de cambio.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import currency_normalizer as cn


class TestPerShareFieldsNeverUseFx:
    """Los campos por-acción no dependen de financialCurrency, solo de subunidad."""

    def test_mismatch_no_subunit_leaves_eps_untouched(self):
        # BABA-like: currency=USD, financialCurrency=CNY, sin subunidad.
        # get_fx_rate SÍ se llama (para agregados, aunque este dict no tenga
        # ninguno) pero no debe tocar los campos por-acción.
        info = {'currency': 'USD', 'financialCurrency': 'CNY', 'trailingEps': 6.6, 'bookValue': 67.4}
        with patch.object(cn, 'get_fx_rate', return_value=0.148):
            out, meta = cn.normalize_info(info, 'BABA')
        assert out['trailingEps'] == 6.6  # sin tocar
        assert out['bookValue'] == 67.4

    def test_subunit_same_major_applies_only_100x(self):
        # AUTO.L-like: currency=GBp, financialCurrency=GBP (misma divisa mayor)
        info = {'currency': 'GBp', 'financialCurrency': 'GBP', 'trailingEps': 0.34}
        with patch.object(cn, 'get_fx_rate') as fx:
            out, meta = cn.normalize_info(info, 'AUTO.L')
        assert out['trailingEps'] == 34.0
        fx.assert_not_called()

    def test_subunit_with_currency_mismatch_still_only_100x(self):
        # EXPN.L-like: currency=GBp, financialCurrency=USD — el bug original
        # aplicaba fx_to_major (~0.79) además del ×100, dando 79 en vez de 100
        info = {'currency': 'GBp', 'financialCurrency': 'USD', 'trailingEps': 1.21}
        with patch.object(cn, 'get_fx_rate', return_value=0.79) as fx:
            out, meta = cn.normalize_info(info, 'EXPN.L')
        assert out['trailingEps'] == 121.0  # exactamente ×100, no ×79
        # get_fx_rate solo se llama para los agregados (financialCurrency != currency)
        fx.assert_called_once_with('USD', 'GBP')


class TestAggregateFieldsUseFx:
    """FCF, ingresos, deuda sí vienen en financialCurrency y sí necesitan FX."""

    def test_converts_when_fx_available(self):
        info = {'currency': 'USD', 'financialCurrency': 'CNY', 'freeCashflow': -1000.0}
        with patch.object(cn, 'get_fx_rate', return_value=0.15):
            out, meta = cn.normalize_info(info, 'X')
        assert out['freeCashflow'] == -150.0
        assert meta['fx_reliable'] is True

    def test_marks_unreliable_when_fx_missing(self):
        info = {'currency': 'USD', 'financialCurrency': 'CNY', 'freeCashflow': -1000.0}
        with patch.object(cn, 'get_fx_rate', return_value=None):
            out, meta = cn.normalize_info(info, 'X')
        assert meta['fx_reliable'] is False
        assert out['freeCashflow'] == -1000.0  # no convertido, dato crudo intacto

    def test_missing_fx_does_not_block_per_share_fields(self):
        # Subunidad + agregados sin FX disponible: el ×100 por-acción debe
        # aplicarse igual, no depende del resultado del FX de agregados
        info = {'currency': 'GBp', 'financialCurrency': 'USD',
                'trailingEps': 1.21, 'freeCashflow': -1000.0}
        with patch.object(cn, 'get_fx_rate', return_value=None):
            out, meta = cn.normalize_info(info, 'X')
        assert out['trailingEps'] == 121.0
        assert meta['fx_reliable'] is False
        assert out['freeCashflow'] == -1000.0

    def test_no_conversion_when_same_currency(self):
        info = {'currency': 'USD', 'financialCurrency': 'USD', 'freeCashflow': -1000.0}
        with patch.object(cn, 'get_fx_rate') as fx:
            out, meta = cn.normalize_info(info, 'X')
        assert out['freeCashflow'] == -1000.0
        fx.assert_not_called()


class TestEdgeCases:
    def test_missing_currency_returns_unchanged(self):
        info = {'trailingEps': 1.0}
        out, meta = cn.normalize_info(info, 'X')
        assert out is info
        assert meta['fx_reliable'] is True

    def test_missing_financial_currency_still_applies_subunit(self):
        info = {'currency': 'GBp', 'trailingEps': 1.21}
        out, meta = cn.normalize_info(info, 'X')
        assert out['trailingEps'] == 121.0
