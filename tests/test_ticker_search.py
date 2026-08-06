#!/usr/bin/env python3
"""Tests para /api/search — el buscador de tickers.

Verificado en vivo el 6-ago-2026: buscar "microsoft" devolvía 'MSFTX-USD'
(un token cripto que sigue el precio de la acción, quoteType=CRYPTOCURRENCY)
como segundo resultado, justo debajo de MSFT. Para una app de VALUE
investing, mezclar un wrapper sintético con la acción real es confuso y
potencialmente peligroso si el usuario opera el ticker equivocado.
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ticker_api as api


class FakeSearchResult:
    def __init__(self, quotes):
        self.quotes = quotes


class TestSearchFiltersNonEquityInstruments:
    def test_excluye_tokens_cripto_que_siguen_una_accion(self):
        fake_quotes = [
            {'symbol': 'MSFT', 'longname': 'Microsoft Corporation', 'quoteType': 'EQUITY'},
            {'symbol': 'MSFTX-USD', 'longname': 'Microsoft tokenized stock (xStock) USD',
             'quoteType': 'CRYPTOCURRENCY'},
            {'symbol': 'MSFT34.SA', 'longname': 'Microsoft Corporation', 'quoteType': 'EQUITY'},
        ]
        with patch('yfinance.Search', return_value=FakeSearchResult(fake_quotes)), \
             patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {}  # sin match directo de ticker
            client = api.app.test_client()
            r = client.get('/api/search?q=microsoft')
        tickers = [x['ticker'] for x in r.get_json()['results']]
        assert 'MSFTX-USD' not in tickers
        assert 'MSFT' in tickers

    def test_permite_equity_y_etf(self):
        fake_quotes = [
            {'symbol': 'XYZ', 'longname': 'Xyz Corp', 'quoteType': 'EQUITY'},
            {'symbol': 'XYZE', 'longname': 'Xyz ETF', 'quoteType': 'ETF'},
        ]
        with patch('yfinance.Search', return_value=FakeSearchResult(fake_quotes)), \
             patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {}
            client = api.app.test_client()
            r = client.get('/api/search?q=xyzcorp')
        tickers = [x['ticker'] for x in r.get_json()['results']]
        assert 'XYZ' in tickers
        assert 'XYZE' in tickers

    def test_filtro_no_roba_hueco_a_resultados_reales(self):
        # El filtro va ANTES de cortar a 5 candidatos, no después — si el
        # instrumento sintético cae entre los primeros 5 crudos, no debe
        # dejar fuera a un resultado real que iba 6º.
        fake_quotes = (
            [{'symbol': f'CRYPTO{i}', 'longname': f'Crypto {i}', 'quoteType': 'CRYPTOCURRENCY'}
             for i in range(4)]
            + [{'symbol': 'REAL', 'longname': 'Real Corp', 'quoteType': 'EQUITY'}]
        )
        with patch('yfinance.Search', return_value=FakeSearchResult(fake_quotes)), \
             patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {}
            client = api.app.test_client()
            r = client.get('/api/search?q=realcorp')
        tickers = [x['ticker'] for x in r.get_json()['results']]
        assert 'REAL' in tickers

    def test_query_vacia_no_rompe(self):
        client = api.app.test_client()
        r = client.get('/api/search?q=')
        assert r.get_json()['results'] == []
