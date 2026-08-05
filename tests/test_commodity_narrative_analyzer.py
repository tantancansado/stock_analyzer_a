#!/usr/bin/env python3
"""Tests del analizador de narrativa de materias primas — sin red."""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import commodity_narrative_analyzer as cna

URL = 'https://eia.gov/naturalgas/weekly'


class TestAnalyzeCommodity:
    def test_veredicto_con_fuentes_reales(self):
        j = ('{"veredicto": "OPORTUNIDAD_ESTRUCTURAL", '
             '"resumen": "Inventarios sobre la media por invierno suave, demanda GNL sigue fuerte.", '
             '"confianza": 75}')
        with patch.object(cna, 'ask_with_search', return_value=(j, [URL])):
            r = cna.analyze_commodity('UNG', 'Gas Natural', 9.77, 'USD', -42.6, -31.0)
        assert r['veredicto'] == 'OPORTUNIDAD_ESTRUCTURAL'
        assert r['confianza'] == 75 and r['fuentes'] == [URL]

    def test_sin_busquedas_degrada_a_sin_datos(self):
        j = '{"veredicto": "OPORTUNIDAD_ESTRUCTURAL", "resumen": "creo que sí", "confianza": 80}'
        with patch.object(cna, 'ask_with_search', return_value=(j, [])):
            assert cna.analyze_commodity('UNG', 'Gas Natural', 9.77, 'USD', -42.6, -31.0)['veredicto'] == 'SIN_DATOS'

    def test_categoria_inventada_degrada(self):
        with patch.object(cna, 'ask_with_search', return_value=('{"veredicto": "COMPRAR_YA"}', [URL])):
            assert cna.analyze_commodity('UNG', 'Gas Natural', 9.77, 'USD', -42.6, -31.0)['veredicto'] == 'SIN_DATOS'

    def test_api_caida_no_rompe(self):
        with patch.object(cna, 'ask_with_search', return_value=('', [])):
            assert cna.analyze_commodity('UNG', 'Gas Natural', 9.77, 'USD', -42.6, -31.0)['veredicto'] == 'SIN_DATOS'


class TestEnrich:
    ROWS = [
        {'ticker': 'GLD', 'sector': 'Oro', 'value_rating': 'CARO', 'price': '250',
         'currency': 'USD', 'pct_from_high': '-1', 'pct_vs_2y_avg': '20', 'eu_alternative': 'SGLN.L'},
        {'ticker': 'UNG', 'sector': 'Gas Natural', 'value_rating': 'MUY_ATRACTIVO', 'price': '9.77',
         'currency': 'USD', 'pct_from_high': '-42.6', 'pct_vs_2y_avg': '-31', 'eu_alternative': 'NGAS.L'},
    ]

    def test_prioriza_lo_atractivo_sobre_lo_caro(self):
        orden_visto = []

        def _fake(ticker, sector, price, ccy, pfh, pv2y):
            orden_visto.append(ticker)
            return {'veredicto': 'SIN_DATOS', 'resumen': '', 'confianza': 0, 'fuentes': []}

        with patch.object(cna, 'analyze_commodity', side_effect=_fake):
            cna.enrich(self.ROWS, max_commodities=10)
        assert orden_visto[0] == 'UNG'  # MUY_ATRACTIVO antes que CARO

    def test_respeta_el_limite_de_commodities(self):
        muchos = self.ROWS * 10
        with patch.object(cna, 'analyze_commodity',
                          return_value={'veredicto': 'SIN_DATOS', 'resumen': '', 'confianza': 0, 'fuentes': []}):
            out = cna.enrich(muchos, max_commodities=3)
        assert len(out) <= 3

    def test_lista_vacia_no_rompe(self):
        assert cna.enrich([]) == {}
