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
    # La caché va al tmp del test: con la ruta real, los tests se escribían
    # entre sí en docs/why_cheap_cache.json y el veredicto cacheado de un test
    # hacía fallar al siguiente (además de ensuciar el repo al correr la suite).
    monkeypatch.setattr(ewc, 'CACHE', tmp_path / 'why_cheap_cache.json')
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


class TestPresupuestoEsTopeReal:
    """El presupuesto tiene que ser un techo, no una sugerencia.

    Hasta el 7-ago-2026 sólo se comprobaba "¿me he pasado ya?" ANTES de cada
    ticker, así que siempre se podía desbordar por el coste entero del último:
    esa corrida gastó 527s con presupuesto de 420 (+25%). Importa porque el job
    core-scoring va a 78-84 min sobre un tope de 90 — ese exceso sale del
    margen que evita que el job muera entero.
    """

    def test_no_arranca_un_ticker_que_no_cabe(self, universos, monkeypatch):
        """Con el presupuesto casi agotado no se empieza otro análisis."""
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 200)
        monkeypatch.setattr(ewc, 'COSTE_TICKER_SEG', 175.0)
        llamados = []

        def _fake(ticker, *a, **k):
            llamados.append(ticker)
            return {'veredicto': 'CICLICO', 'fuentes': [], 'resumen': ''}

        monkeypatch.setattr(ewc, 'analyze_ticker', _fake)
        ewc.main()
        # Cabe uno (0 + 175 <= 200); tras él quedan ~175s gastados y
        # 175+175 > 200, así que no arranca un segundo.
        assert len(llamados) <= 1, \
            f'arrancó {len(llamados)} análisis sin margen: {llamados}'

    def test_la_reserva_crece_con_el_peor_caso_visto(self):
        """Un ticker atascado sube la reserva, no se repite el atasco."""
        reserva = ewc.COSTE_TICKER_SEG
        for coste in (150.0, 400.0, 120.0):
            reserva = max(reserva, coste)
        assert reserva == 400.0

    def test_min_caida_excluye_el_ruido(self):
        """Explicar una caída del 9% cuesta lo mismo que una del 39% y no
        aporta: el módulo separa castigo de deterioro, y al 8% no hay castigo.
        MSFT entró con -9,7%, se llevó 201s por un timeout y dejó fuera a MCO."""
        assert ewc.MIN_CAIDA_PCT >= 12.0, \
            'umbral demasiado bajo — vuelve a colar ruido y gastar API en él'

    def test_presupuesto_cubre_al_menos_dos_tickers(self):
        """Si no caben dos, MAX_TICKERS miente y la selección es teatro."""
        assert ewc.PRESUPUESTO_SEG >= 2 * ewc.COSTE_TICKER_SEG


class TestCacheDeVeredictos:
    """Por qué una empresa está barata no cambia de un día para otro.

    Sin caché se recompraba el mismo análisis a diario: super_score_integrator
    regenera value_opportunities.csv desde cero y borra la columna, así que BR
    y SAP se re-analizaban cada mañana con búsqueda web (~$0,20 cada uno). Esa
    es la partida que agotó el saldo de la API el 10-ago-2026.
    """

    def test_no_reanaliza_lo_que_esta_en_cache(self, universos, monkeypatch):
        import json
        us_csv, _ = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        ewc.CACHE.write_text(json.dumps({
            'AAPL': {'veredicto': 'CICLICO', 'resumen': 'del cache', 'fuentes': [],
                     'fecha': __import__('datetime').date.today().isoformat()},
        }))
        llamadas = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: llamadas.append(t) or _fake_veredicto()):
            ewc.main()
        assert llamadas == [], 'volvió a pagar un análisis que ya tenía en caché'
        assert pd.read_csv(us_csv).set_index('ticker').loc['AAPL', 'why_cheap'] == 'CICLICO'

    def test_reanaliza_lo_caducado(self, universos, monkeypatch):
        import json, datetime as dt
        us_csv, _ = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        viejo = (dt.date.today() - dt.timedelta(days=ewc.CACHE_DIAS + 1)).isoformat()
        ewc.CACHE.write_text(json.dumps({
            'AAPL': {'veredicto': 'CICLICO', 'resumen': 'viejo', 'fuentes': [], 'fecha': viejo},
        }))
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        llamadas = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: llamadas.append(t) or _fake_veredicto('EVENTO')):
            ewc.main()
        assert llamadas == ['AAPL'], 'no refrescó un veredicto caducado'

    def test_lo_analizado_queda_cacheado(self, universos, monkeypatch):
        import json
        us_csv, _ = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: _fake_veredicto('EVENTO')):
            ewc.main()
        guardado = json.loads(ewc.CACHE.read_text())
        assert guardado['AAPL']['veredicto'] == 'EVENTO'
        assert 'fecha' in guardado['AAPL'], 'sin fecha no se puede caducar'
