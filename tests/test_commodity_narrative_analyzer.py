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


class TestCoste:
    """El 8-sep-2026 esta llamada salía a $0.30/llamada -- Sonnet 5 sin
    recortar, max_tokens=4000 para un JSON con resumen de máx. 300
    caracteres. Con MAX_COMMODITIES=10 eso es hasta $3/día si se analiza el
    universo entero. Mismo arreglo que why_cheap_analyzer el mismo día:
    Haiku 4.5 (clasificar en 4 categorías a partir de fuentes ya buscadas es
    síntesis cerrada, no razonamiento en cadena), menos tokens, menos
    búsquedas. Este test fija los parámetros para que si alguien los sube
    sin darse cuenta, salte aquí y no en la factura."""

    def test_usa_haiku_pocas_busquedas_y_pocos_tokens(self):
        captured = {}

        def _fake(prompt, system, **kwargs):
            captured.update(kwargs)
            return '{"veredicto": "SIN_DATOS"}', []

        with patch.object(cna, 'ask_with_search', side_effect=_fake):
            cna.analyze_commodity('UNG', 'Gas Natural', 9.77, 'USD', -42.6, -31.0)

        assert captured.get('model') == 'claude-haiku-4-5'
        # Ver why_cheap: el coste crece con el cuadrado de las búsquedas.
        assert captured.get('max_searches') == 2
        assert captured.get('max_tokens') == 1200


class TestEnrich:
    ROWS = [
        {'ticker': 'GLD', 'sector': 'Oro', 'value_rating': 'CARO', 'price': '250',
         'currency': 'USD', 'pct_from_high': '-1', 'pct_vs_2y_avg': '20', 'eu_alternative': 'SGLN.L'},
        {'ticker': 'UNG', 'sector': 'Gas Natural', 'value_rating': 'MUY_ATRACTIVO', 'price': '9.77',
         'currency': 'USD', 'pct_from_high': '-42.6', 'pct_vs_2y_avg': '-31', 'eu_alternative': 'NGAS.L'},
    ]

    # `enrich` pregunta por todos en UN lote, así que lo que se observa es la
    # lista de prompts, no una secuencia de llamadas. El orden sigue
    # importando: `max_commodities` trunca, y lo que se corta es la cola.
    @staticmethod
    def _capturar(destino, respuesta=('', [])):
        def _fake(prompts, **_):
            destino.extend(prompts)
            return {t: respuesta for t in prompts}
        return _fake

    def test_prioriza_lo_atractivo_sobre_lo_caro(self):
        vistos = []
        with patch.object(cna, 'ask_with_search_lote', self._capturar(vistos)):
            cna.enrich(self.ROWS, max_commodities=10)
        assert vistos[0] == 'UNG'  # MUY_ATRACTIVO antes que CARO

    def test_respeta_el_limite_de_commodities(self):
        # Tickers DISTINTOS: repetir la misma fila no probaba el límite, porque
        # las preguntas van en un dict por ticker y las repetidas se funden en
        # una. (Que se fundan está bien —preguntar dos veces por el mismo sale
        # igual de caro y da lo mismo— pero no es lo que este test mide.)
        muchos = [dict(self.ROWS[0], ticker=f'C{i}') for i in range(10)]
        vistos = []
        with patch.object(cna, 'ask_with_search_lote', self._capturar(vistos)):
            out = cna.enrich(muchos, max_commodities=3)
        # El límite se aplica ANTES de preguntar: si se preguntara por los diez
        # y luego se recortara, el ahorro sería cero y la factura el triple.
        assert len(vistos) == 3
        assert len(out) == 3

    def test_no_pregunta_dos_veces_por_el_mismo_ticker(self):
        vistos = []
        with patch.object(cna, 'ask_with_search_lote', self._capturar(vistos)):
            cna.enrich(self.ROWS * 5, max_commodities=10)
        assert sorted(vistos) == ['GLD', 'UNG']

    def test_cada_veredicto_va_a_su_commodity(self):
        """Cruzar respuestas es el fallo propio de un lote: una TRAMPA_DE_VALOR
        asignada al ticker equivocado marca como trampa algo que no lo es."""
        respuestas = {
            'UNG': ('{"veredicto": "MINIMO_CICLICO", "resumen": "ciclo", "confianza": 70}', [URL]),
            'CORN': ('{"veredicto": "TRAMPA_DE_VALOR", "resumen": "exceso", "confianza": 80}', [URL]),
        }
        with patch.object(cna, 'ask_with_search_lote',
                          lambda prompts, **_: {t: respuestas.get(t, ('', [])) for t in prompts}):
            out = cna.enrich(self.ROWS, max_commodities=10)
        assert out['UNG']['veredicto'] == 'MINIMO_CICLICO'
        if 'CORN' in out:
            assert out['CORN']['veredicto'] == 'TRAMPA_DE_VALOR' 

    def test_lista_vacia_no_rompe(self):
        assert cna.enrich([]) == {}
