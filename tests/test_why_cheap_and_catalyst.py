#!/usr/bin/env python3
"""Tests de las capas de verificación con Claude — sin red."""
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bounce_catalyst_check as bcc
import why_cheap_analyzer as wc

URL = 'https://ir.example.com/q2-results'


class TestWhyCheapCoste:
    """El 25-ago-2026 esta llamada salía a $0.33 — el 44% del gasto mensual
    con solo 12 llamadas — usando los valores por defecto de ask_with_search
    (6 búsquedas, max_tokens 2000, effort medium). El coste no es lineal en
    nº de búsquedas: cada ronda dentro de la misma llamada reenvía el
    contexto de las anteriores, así que crece con el cuadrado. Este test fija
    los parámetros recortados para que si alguien los sube sin darse cuenta
    (p.ej. "probando si mejora la calidad"), salte aquí y no en la factura."""

    def test_usa_menos_busquedas_y_effort_bajo(self):
        captured = {}

        def _fake(prompt, system, **kwargs):
            captured.update(kwargs)
            return '{"veredicto": "SIN_DATOS"}', []

        with patch.object(wc, 'ask_with_search', side_effect=_fake):
            wc.analyze_ticker('XYZ', 'Ejemplo SA', -25.0, -20.0)

        assert captured.get('max_searches') == 3
        assert captured.get('max_tokens') == 1200
        assert captured.get('effort') == 'low'


class TestWhyCheap:
    def test_deterioro_con_busquedas_detras(self):
        j = '{"veredicto": "DETERIORO", "resumen": "Guidance retirada en julio", "confianza": 85}'
        with patch.object(wc, 'ask_with_search', return_value=(j, [URL])):
            r = wc.analyze_ticker('XYZ', 'Ejemplo SA', -25.0, -20.0)
        assert r['veredicto'] == 'DETERIORO'
        assert r['confianza'] == 85 and r['fuentes'] == [URL]

    def test_veredicto_sin_busquedas_degrada_a_sin_datos(self):
        # Las fuentes salen de la herramienta: si no buscó, el veredicto podría
        # venir de la memoria del modelo y no se acepta
        j = '{"veredicto": "DETERIORO", "resumen": "Creo que van mal", "confianza": 90}'
        with patch.object(wc, 'ask_with_search', return_value=(j, [])):
            assert wc.analyze_ticker('XYZ', 'X', -25.0)['veredicto'] == 'SIN_DATOS'

    def test_categoria_inventada_degrada(self):
        with patch.object(wc, 'ask_with_search', return_value=('{"veredicto": "MUY_MALA"}', [URL])):
            assert wc.analyze_ticker('XYZ', 'X', -25.0)['veredicto'] == 'SIN_DATOS'

    def test_api_caida_no_rompe(self):
        with patch.object(wc, 'ask_with_search', return_value=('', [])):
            assert wc.analyze_ticker('XYZ', 'X', -25.0)['veredicto'] == 'SIN_DATOS'

    def test_solo_analiza_candidatos_reales(self):
        rows = [
            {'ticker': 'BUENA',   'company_name': 'A', 'proximity_to_52w_high': -25.0, 'value_score': 70},
            {'ticker': 'MAXIMOS', 'company_name': 'B', 'proximity_to_52w_high': -2.0,  'value_score': 80},
            {'ticker': 'FLOJA',   'company_name': 'C', 'proximity_to_52w_high': -30.0, 'value_score': 35},
        ]
        j = '{"veredicto": "CICLICO", "resumen": "ok", "confianza": 60}'
        with patch.object(wc, 'ask_with_search', return_value=(j, [URL])):
            out = wc.analyze_picks(rows)
        # Ni la que está en máximos (nada que explicar) ni la de score bajo
        # (no se compraría igualmente) consumen una búsqueda
        assert list(out) == ['BUENA']

    def test_apply_saca_deterioro_y_deja_el_resto(self):
        df = pd.DataFrame([{'ticker': 'OTIS'}, {'ticker': 'ICE'}])
        veredictos = {
            'OTIS': {'veredicto': 'DETERIORO', 'resumen': 'x', 'fuentes': []},
            'ICE':  {'veredicto': 'CICLICO', 'resumen': 'y', 'fuentes': []},
        }
        out, bloqueados = wc.apply_to_dataframe(df, veredictos)
        assert list(out['ticker']) == ['ICE'] and bloqueados == ['OTIS']

    def test_sin_veredictos_no_toca_la_lista(self):
        df = pd.DataFrame([{'ticker': 'OTIS'}])
        out, bloqueados = wc.apply_to_dataframe(df, {})
        assert len(out) == 1 and bloqueados == []


class TestBounceCatalystCoste:
    """Mismo motivo que TestWhyCheapCoste: fija los parámetros recortados
    (25-ago-2026) para que una subida accidental salte en un test, no en la
    factura. Aquí `effort` se deja en 'medium' a propósito — es un gate de
    seguridad de baja frecuencia (~1 setup/semana), no una clasificación
    cerrada de alto volumen como why_cheap."""

    def test_usa_tres_busquedas_y_effort_medio(self):
        captured = {}

        def _fake(prompt, system, **kwargs):
            captured.update(kwargs)
            return '{"veredicto": "SIN_DATOS"}', []

        with patch.object(bcc, 'ask_with_search', side_effect=_fake):
            bcc.check_ticker('XYZ')

        assert captured.get('max_searches') == 3
        assert captured.get('max_tokens') == 1200
        assert captured.get('effort') == 'medium'


class TestBounceCatalyst:
    def test_peligro_descarta_el_setup(self):
        j = '{"veredicto": "PELIGRO", "motivo": "Profit warning el lunes"}'
        with patch.object(bcc, 'ask_with_search', return_value=(j, [URL])):
            limpios, fuera = bcc.filter_setups([{'ticker': 'AEP'}])
        assert limpios == [] and fuera[0]['ticker'] == 'AEP'

    def test_limpio_sigue_adelante(self):
        j = '{"veredicto": "LIMPIO", "motivo": "Debilidad de mercado"}'
        with patch.object(bcc, 'ask_with_search', return_value=(j, [URL])):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}])
        assert len(limpios) == 1 and fuera == []

    def test_peligro_sin_busquedas_no_descarta(self):
        j = '{"veredicto": "PELIGRO", "motivo": "me suena mal"}'
        with patch.object(bcc, 'ask_with_search', return_value=(j, [])):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}])
        assert len(limpios) == 1 and fuera == []

    def test_api_caida_deja_pasar_los_setups(self):
        with patch.object(bcc, 'ask_with_search', return_value=('', [])):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}, {'ticker': 'AEP'}])
        assert len(limpios) == 2 and fuera == []

    def test_lista_vacia(self):
        assert bcc.filter_setups([]) == ([], [])
