#!/usr/bin/env python3
"""Tests de las tres capas nuevas de verificación — sin red."""
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bounce_catalyst_check as bcc
import why_cheap_analyzer as wc


def _fake_groq(content: str):
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=content))])
    return client


class TestWhyCheap:
    def test_deterioro_con_fuentes(self):
        j = ('{"veredicto": "DETERIORO", "resumen": "Guidance retirada en julio", '
             '"confianza": 85, "fuentes": ["https://ir.example.com/q2"]}')
        with patch.object(wc, '_get_client', return_value=_fake_groq(j)):
            r = wc.analyze_ticker('XYZ', 'Ejemplo SA', -25.0, -20.0)
        assert r['veredicto'] == 'DETERIORO' and r['confianza'] == 85

    def test_veredicto_sin_fuentes_degrada_a_sin_datos(self):
        # Sin URL podría venir de la memoria del modelo: no se acepta
        j = '{"veredicto": "DETERIORO", "resumen": "Creo que van mal", "fuentes": []}'
        with patch.object(wc, '_get_client', return_value=_fake_groq(j)):
            assert wc.analyze_ticker('XYZ', 'X', -25.0)['veredicto'] == 'SIN_DATOS'

    def test_categoria_inventada_degrada(self):
        j = '{"veredicto": "MUY_MALA", "fuentes": ["https://x.com/a"]}'
        with patch.object(wc, '_get_client', return_value=_fake_groq(j)):
            assert wc.analyze_ticker('XYZ', 'X', -25.0)['veredicto'] == 'SIN_DATOS'

    def test_api_caida_no_rompe(self):
        with patch.object(wc, '_get_client', return_value=None):
            assert wc.analyze_ticker('XYZ', 'X', -25.0)['veredicto'] == 'SIN_DATOS'

    def test_solo_analiza_los_que_han_caido(self):
        rows = [
            {'ticker': 'CAIDA', 'company_name': 'A', 'proximity_to_52w_high': -25.0},
            {'ticker': 'MAXIMOS', 'company_name': 'B', 'proximity_to_52w_high': -2.0},
        ]
        j = '{"veredicto": "CICLICO", "resumen": "ok", "fuentes": ["https://x.com/a"]}'
        with patch.object(wc, '_get_client', return_value=_fake_groq(j)):
            out = wc.analyze_picks(rows, min_drop_pct=8.0)
        assert 'CAIDA' in out and 'MAXIMOS' not in out

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


class TestBounceCatalyst:
    def test_peligro_descarta_el_setup(self):
        j = ('{"veredicto": "PELIGRO", "motivo": "Profit warning el lunes", '
             '"fuentes": ["https://news.example.com/x"]}')
        with patch.object(bcc, '_get_client', return_value=_fake_groq(j)):
            limpios, fuera = bcc.filter_setups([{'ticker': 'AEP'}])
        assert limpios == [] and fuera[0]['ticker'] == 'AEP'

    def test_limpio_sigue_adelante(self):
        j = '{"veredicto": "LIMPIO", "motivo": "Debilidad de mercado", "fuentes": ["https://x.com/a"]}'
        with patch.object(bcc, '_get_client', return_value=_fake_groq(j)):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}])
        assert len(limpios) == 1 and fuera == []

    def test_peligro_sin_fuentes_no_descarta(self):
        # No se tira un setup técnicamente válido por una afirmación sin respaldo
        j = '{"veredicto": "PELIGRO", "motivo": "me suena mal", "fuentes": []}'
        with patch.object(bcc, '_get_client', return_value=_fake_groq(j)):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}])
        assert len(limpios) == 1 and fuera == []

    def test_api_caida_deja_pasar_los_setups(self):
        with patch.object(bcc, '_get_client', return_value=None):
            limpios, fuera = bcc.filter_setups([{'ticker': 'MO'}, {'ticker': 'AEP'}])
        assert len(limpios) == 2 and fuera == []

    def test_lista_vacia(self):
        assert bcc.filter_setups([]) == ([], [])
