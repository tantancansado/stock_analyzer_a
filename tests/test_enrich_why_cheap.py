#!/usr/bin/env python3
"""Tests para enrich_why_cheap.py — cubre US y EU.

Hasta el 5-ago-2026 solo procesaba value_opportunities.csv (US): la lista
europea nunca entraba en la selección de candidatos, mismo bug que tuvo
technical_filter.py con el timing técnico antes de arreglarse.
"""
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import enrich_why_cheap as ewc

COLS = ['ticker', 'company_name', 'value_score', 'proximity_to_52w_high',
       'relative_strength_6m']


def _row(ticker, score, drop=-20.0):
    return {'ticker': ticker, 'company_name': ticker, 'value_score': score,
            'proximity_to_52w_high': drop, 'relative_strength_6m': -5.0}


def _fake_veredicto(veredicto='CICLICO'):
    return {'veredicto': veredicto, 'resumen': 'test', 'fuentes': []}


@pytest.fixture
def universos(tmp_path, monkeypatch):
    us_csv = tmp_path / 'value_opportunities.csv'
    eu_csv = tmp_path / 'european_value_opportunities.csv'
    monkeypatch.setattr(ewc, 'TARGET_CSVS', [us_csv, eu_csv])
    return us_csv, eu_csv


class TestCandidatosDeAmbosUniversos:
    def test_eu_entra_en_la_seleccion(self, universos, monkeypatch):
        us_csv, eu_csv = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        pd.DataFrame([_row('SAP.DE', 70.0)], columns=COLS).to_csv(eu_csv, index=False)
        monkeypatch.setattr(ewc, 'MAX_TICKERS', 5)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)

        vistos = []

        def _fake_analyze(ticker, *a, **kw):
            vistos.append(ticker)
            return _fake_veredicto()

        with patch.object(ewc, 'analyze_ticker', side_effect=_fake_analyze):
            ewc.main()

        assert 'SAP.DE' in vistos  # antes del fix, nunca

    def test_presupuesto_de_candidatos_es_compartido_no_por_csv(self, universos, monkeypatch):
        us_csv, eu_csv = universos
        us_rows = [_row(f'US{i}', 90.0 - i) for i in range(5)]
        eu_rows = [_row(f'EU{i}', 89.0 - i) for i in range(5)]
        pd.DataFrame(us_rows, columns=COLS).to_csv(us_csv, index=False)
        pd.DataFrame(eu_rows, columns=COLS).to_csv(eu_csv, index=False)
        monkeypatch.setattr(ewc, 'MAX_TICKERS', 3)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)

        vistos = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: (vistos.append(t), _fake_veredicto())[1]):
            ewc.main()

        # 3 en TOTAL, no 3 de cada uno (serían 6)
        assert len(vistos) == 3

    def test_resultados_se_escriben_en_el_csv_correcto(self, universos, monkeypatch):
        us_csv, eu_csv = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        pd.DataFrame([_row('SAP.DE', 70.0)], columns=COLS).to_csv(eu_csv, index=False)
        monkeypatch.setattr(ewc, 'MAX_TICKERS', 5)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)

        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: _fake_veredicto('EVENTO')):
            ewc.main()

        us_out = pd.read_csv(us_csv)
        eu_out = pd.read_csv(eu_csv)
        assert us_out.set_index('ticker').loc['AAPL', 'why_cheap'] == 'EVENTO'
        assert eu_out.set_index('ticker').loc['SAP.DE', 'why_cheap'] == 'EVENTO'
        # el 'origen_csv' de trabajo interno no se filtra a los CSV publicados
        assert 'origen_csv' not in us_out.columns
        assert 'origen_csv' not in eu_out.columns

    def test_universo_ausente_no_rompe_a_los_demas(self, universos, monkeypatch):
        us_csv, eu_csv = universos  # eu_csv no se crea
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        monkeypatch.setattr(ewc, 'MAX_TICKERS', 5)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)

        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: _fake_veredicto()):
            ewc.main()

        assert pd.read_csv(us_csv).set_index('ticker').loc['AAPL', 'why_cheap'] == 'CICLICO'

    def test_sin_ningun_universo_no_rompe(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ewc, 'TARGET_CSVS', [tmp_path / 'no_existe.csv'])
        ewc.main()  # no debe lanzar

    def test_ambos_vacios_no_rompe(self, universos):
        us_csv, eu_csv = universos
        pd.DataFrame(columns=COLS).to_csv(us_csv, index=False)
        pd.DataFrame(columns=COLS).to_csv(eu_csv, index=False)
        ewc.main()  # no debe lanzar
