#!/usr/bin/env python3
"""Verificador de campos contra la fuente — sin red.

Las tolerancias no son arbitrarias: están calibradas contra los dos casos
reales del 10-sep-2026 que motivaron el módulo. El máximo de 52 semanas de BR
(255,74 publicado vs 250,03 real) tiene que CONFIRMAR — era un desvío del
propio yfinance y el pick no debía caerse por él. Su crecimiento (39,7% vs
7,5% real) tiene que CONTRADECIR — ese sí era un bug del pipeline.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import source_verifier as sv


def _con_fuente(valor):
    return patch.object(sv, '_valor_en_fuente', lambda t, c: valor)


class TestCasosRealesQueLoMotivaron:
    def test_el_maximo_52s_de_br_confirma(self):
        with _con_fuente(250.03):
            r = sv.verificar_campo('BR', 'fifty_two_week_high', 255.74)
        assert r['estado'] == 'confirma', "2,3% de desvío no puede tumbar un pick"

    def test_el_crecimiento_inflado_de_br_contradice(self):
        with _con_fuente(7.5):
            r = sv.verificar_campo('BR', 'rev_growth_yoy', 39.7)
        assert r['estado'] == 'contradice'
        assert '32.2pp' in r['detalle']

    def test_el_crecimiento_ya_arreglado_confirma(self):
        with _con_fuente(7.5):
            assert sv.verificar_campo('BR', 'rev_growth_yoy', 7.5)['estado'] == 'confirma'


class TestNuncaRevienta:
    """Un verificador que lanza es peor que uno que no sabe: tumbaría el paso
    del pipeline que intenta usarlo."""

    def test_campo_desconocido(self):
        assert sv.verificar_campo('BR', 'inventado', 1)['estado'] == 'sin_fuente'

    def test_valor_no_numerico(self):
        with _con_fuente(10.0):
            assert sv.verificar_campo('BR', 'roe', 'n/d')['estado'] == 'sin_fuente'

    def test_la_fuente_lanza(self):
        def _explota(t, c):
            raise RuntimeError('yfinance caído')
        with patch.object(sv, '_valor_en_fuente', _explota):
            r = sv.verificar_campo('BR', 'roe', 10.0)
        assert r['estado'] == 'sin_fuente'
        assert 'falló' in r['detalle']

    def test_la_fuente_no_tiene_el_dato(self):
        with _con_fuente(None):
            assert sv.verificar_campo('BR', 'roe', 10.0)['estado'] == 'sin_fuente'

    def test_division_por_cero_en_relativo(self):
        with _con_fuente(0.0):
            assert sv.verificar_campo('BR', 'current_price', 10.0)['estado'] == 'sin_fuente'


class TestModoDeComparacion:
    def test_los_porcentajes_se_comparan_en_puntos_no_en_relativo(self):
        # 1% vs 3%: en relativo son un 200% de desvío, pero en puntos son 2pp.
        # Un ROE del 1% frente a uno del 3% no es un dato roto.
        with _con_fuente(3.0):
            assert sv.verificar_campo('X', 'roe', 1.0)['estado'] == 'confirma'

    def test_las_magnitudes_se_comparan_en_relativo(self):
        # Un precio de 10 frente a 100 sí es un dato roto.
        with _con_fuente(100.0):
            assert sv.verificar_campo('X', 'current_price', 10.0)['estado'] == 'contradice'
