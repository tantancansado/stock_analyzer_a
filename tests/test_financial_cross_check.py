#!/usr/bin/env python3
"""Tests del cuadre contable — el caso ATLKY del 3-ago-2026."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from financial_cross_check import check_coherence, derive_from_statements


class TestSharesPriceCoherence:
    def test_us_stock_cuadra(self):
        # MCO real: 173.180.984 × 478.38 = 82.846.319.126 ≈ marketCap
        info = {'sharesOutstanding': 173180984, 'currentPrice': 478.38,
                'marketCap': 82846326784}
        res = check_coherence(info, 'MCO')
        assert res['per_share_reliable'] is True
        assert abs(res['shares_price_ratio'] - 1.0) < 0.001

    def test_adr_no_cuadra(self):
        # ATLKY real: acciones ordinarias suecas contra precio del ADS
        info = {'sharesOutstanding': 3317744716, 'currentPrice': 21.25,
                'marketCap': 103670685696}
        res = check_coherence(info, 'ATLKY')
        assert res['per_share_reliable'] is False
        assert res['shares_price_ratio'] == 0.6801
        assert 'ADR' in res['issues'][0]

    def test_datos_incompletos_no_bloquean(self):
        # Sin los tres datos no hay cuadre que hacer; no se asume lo peor
        assert check_coherence({'currentPrice': 10.0})['per_share_reliable'] is True

    def test_desviacion_pequena_tolerada(self):
        # Recompras entre el corte del dato y el precio de hoy
        info = {'sharesOutstanding': 100, 'currentPrice': 10.0, 'marketCap': 1020}
        assert check_coherence(info)['per_share_reliable'] is True


class TestFcfCrossCheck:
    def test_fcf_declarado_coherente_con_ocf_menos_capex(self):
        info = {'freeCashflow': 2579124992, 'operatingCashflow': 3319000064,
                'capitalExpenditure': -739875072}
        assert check_coherence(info)['issues'] == []

    def test_fcf_declarado_divergente_se_reporta(self):
        info = {'freeCashflow': 9000000000, 'operatingCashflow': 3319000064,
                'capitalExpenditure': -739875072}
        res = check_coherence(info, 'X')
        assert any('derivado' in i for i in res['issues'])
        # Divergencia se reporta pero no invalida los ratios por acción
        assert res['per_share_reliable'] is True


class _FakeStock:
    def __init__(self, cashflow=None):
        self.cashflow = cashflow if cashflow is not None else pd.DataFrame()
        self.financials = pd.DataFrame()
        self.balance_sheet = pd.DataFrame()


class TestDeriveFromStatements:
    def test_rellena_desde_el_estado_de_flujos(self):
        cf = pd.DataFrame(
            {pd.Timestamp('2025-12-31'): [25972000768.0, -3000000.0]},
            index=['Free Cash Flow', 'Capital Expenditure'],
        )
        info, filled = derive_from_statements(_FakeStock(cf), {'freeCashflow': None})
        assert info['freeCashflow'] == 25972000768.0
        assert 'freeCashflow' in filled

    def test_no_toca_lo_que_ya_existe(self):
        cf = pd.DataFrame({pd.Timestamp('2025-12-31'): [999.0]}, index=['Free Cash Flow'])
        info, filled = derive_from_statements(_FakeStock(cf), {'freeCashflow': 123.0})
        assert info['freeCashflow'] == 123.0 and filled == []

    def test_deriva_fcf_de_ocf_menos_capex(self):
        cf = pd.DataFrame(
            {pd.Timestamp('2025-12-31'): [3319000064.0, -739875072.0]},
            index=['Operating Cash Flow', 'Capital Expenditure'],
        )
        info, filled = derive_from_statements(_FakeStock(cf), {'freeCashflow': None})
        assert info['freeCashflow'] == 3319000064.0 - 739875072.0
        assert any('derivado' in f for f in filled)

    def test_estados_vacios_no_rompen(self):
        info, filled = derive_from_statements(_FakeStock(), {'freeCashflow': None})
        assert info['freeCashflow'] is None and filled == []
