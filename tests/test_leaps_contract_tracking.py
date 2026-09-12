#!/usr/bin/env python3
"""LEAPS: medir el CONTRATO, no solo la acción.

Durante meses portfolio_tracker registró únicamente el subyacente y lo
justificaba así: "el precio de la opción depende del strike y no se puede
seguir con yfinance". Es falso — los contratos tienen símbolo OCC y yfinance
los sirve como cualquier ticker (comprobado el 12-sep-2026 contra
MSFT280121C00370000, AXP280121C00250000 e ICE280121C00115000).

Consecuencia: de la sección que el usuario considera de las más lucrativas no
se sabía nada. Con apalancamiento ~2,5x el retorno de la acción NO dice el del
contrato.

Lo que sí es cierto es la iliquidez: de las últimas 20 sesiones, dos de esos
tres contratos solo tenían 4 cierres. De ahí la ventana de tolerancia.
"""
import os
import sys
from datetime import timedelta
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import portfolio_tracker as pt


class TestSimboloOCC:
    def test_construye_el_simbolo_estandar(self):
        assert pt.PortfolioTracker._occ_symbol('MSFT', '2028-01-21', 370.0) == 'MSFT280121C00370000'

    def test_strike_con_decimales(self):
        assert pt.PortfolioTracker._occ_symbol('ICE', '2028-01-21', 115.5) == 'ICE280121C00115500'

    def test_puts(self):
        assert pt.PortfolioTracker._occ_symbol('AXP', '2028-01-21', 250.0, 'P') == 'AXP280121P00250000'

    @pytest.mark.parametrize('args', [
        ('MSFT', None, 370.0), ('MSFT', '2028-01-21', None),
        ('MSFT', 'fecha-mala', 370.0), ('', '2028-01-21', 370.0),
        ('MSFT', '2028-01-21', 0),
    ])
    def test_datos_incompletos_no_inventan_simbolo(self, args):
        assert pt.PortfolioTracker._occ_symbol(*args) is None


def _tracker(filas, tmp_path):
    t = pt.PortfolioTracker.__new__(pt.PortfolioTracker)
    t.recommendations = pd.DataFrame(filas)
    t._save_recommendations = lambda: None
    return t


def _fila(dias_atras, **extra):
    base = {
        'ticker': 'MSFT', 'strategy': 'LEAPS',
        'signal_date': pd.Timestamp.now().normalize() - timedelta(days=dias_atras),
        'signal_price': 491.85,
        'option_symbol': 'MSFT280121C00370000', 'option_entry_price': 100.0,
        'option_return_7d': None, 'option_price_7d': None,
        'option_return_14d': None, 'option_price_14d': None,
        'option_return_30d': None, 'option_price_30d': None,
        'option_return_90d': None, 'option_price_90d': None,
        'option_return_180d': None, 'option_price_180d': None,
    }
    base.update(extra)
    return base


def _hist(fechas_precios):
    idx = pd.DatetimeIndex([pd.Timestamp(f) for f, _ in fechas_precios])
    return pd.DataFrame({'Close': [p for _, p in fechas_precios]}, index=idx)


class TestMedicionDelContrato:
    def test_calcula_el_retorno_sobre_el_precio_del_CONTRATO(self, tmp_path):
        hoy = pd.Timestamp.now().normalize()
        emision = hoy - timedelta(days=10)
        t = _tracker([_fila(10)], tmp_path)
        h = _hist([(emision + timedelta(days=7), 130.0)])
        with patch.object(pt.yf, 'Ticker', lambda s: type('T', (), {'history': lambda *a, **k: h})()):
            t.update_leaps_contracts()
        # entrada 100 -> 130 en el contrato = +30%, aunque la ACCIÓN se moviera un +12%
        assert t.recommendations.at[0, 'option_return_7d'] == 30.0
        assert t.recommendations.at[0, 'option_price_7d'] == 130.0

    def test_registra_perdidas(self, tmp_path):
        hoy = pd.Timestamp.now().normalize()
        emision = hoy - timedelta(days=10)
        t = _tracker([_fila(10)], tmp_path)
        h = _hist([(emision + timedelta(days=7), 72.0)])
        with patch.object(pt.yf, 'Ticker', lambda s: type('T', (), {'history': lambda *a, **k: h})()):
            t.update_leaps_contracts()
        assert t.recommendations.at[0, 'option_return_7d'] == -28.0

    def test_no_rellena_un_horizonte_que_aun_no_ha_vencido(self, tmp_path):
        hoy = pd.Timestamp.now().normalize()
        emision = hoy - timedelta(days=10)
        t = _tracker([_fila(10)], tmp_path)
        h = _hist([(emision + timedelta(days=d), 130.0) for d in (7, 14, 30)])
        with patch.object(pt.yf, 'Ticker', lambda s: type('T', (), {'history': lambda *a, **k: h})()):
            t.update_leaps_contracts()
        assert t.recommendations.at[0, 'option_return_7d'] == 30.0
        assert pd.isna(t.recommendations.at[0, 'option_return_14d']), "solo han pasado 10 días"
        assert pd.isna(t.recommendations.at[0, 'option_return_30d'])


class TestIliquidez:
    """Lo que de verdad distingue una opción de una acción."""

    def test_acepta_un_cierre_dentro_de_la_ventana(self, tmp_path):
        hoy = pd.Timestamp.now().normalize()
        emision = hoy - timedelta(days=20)
        t = _tracker([_fila(20)], tmp_path)
        # no cotizó el día 7; el siguiente cierre real es el día 11
        h = _hist([(emision + timedelta(days=11), 120.0)])
        with patch.object(pt.yf, 'Ticker', lambda s: type('T', (), {'history': lambda *a, **k: h})()):
            t.update_leaps_contracts()
        assert t.recommendations.at[0, 'option_return_7d'] == 20.0

    def test_fuera_de_la_ventana_se_queda_VACIO(self, tmp_path):
        hoy = pd.Timestamp.now().normalize()
        emision = hoy - timedelta(days=40)
        t = _tracker([_fila(40)], tmp_path)
        # 25 días de silencio: usar ese precio sería medir otra cosa
        h = _hist([(emision + timedelta(days=32), 400.0)])
        with patch.object(pt.yf, 'Ticker', lambda s: type('T', (), {'history': lambda *a, **k: h})()):
            t.update_leaps_contracts()
        assert pd.isna(t.recommendations.at[0, 'option_return_7d']), \
            "un precio de 25 días después no es el retorno a 7 días"

    def test_contrato_sin_ninguna_cotizacion_no_revienta(self, tmp_path):
        t = _tracker([_fila(40)], tmp_path)
        vacio = pd.DataFrame({'Close': []}, index=pd.DatetimeIndex([]))
        with patch.object(pt.yf, 'Ticker', lambda s: type('T', (), {'history': lambda *a, **k: vacio})()):
            t.update_leaps_contracts()
        assert pd.isna(t.recommendations.at[0, 'option_return_7d'])

    def test_un_fallo_de_red_no_tumba_el_tracker(self, tmp_path):
        t = _tracker([_fila(40)], tmp_path)
        def boom(_):
            raise RuntimeError('connection reset')
        with patch.object(pt.yf, 'Ticker', lambda s: type('T', (), {'history': lambda *a, **k: boom(s)})()):
            t.update_leaps_contracts()   # no debe propagar
        assert pd.isna(t.recommendations.at[0, 'option_return_7d'])


class TestSenalesSinContrato:
    def test_las_filas_antiguas_sin_contrato_se_ignoran(self, tmp_path):
        t = _tracker([_fila(40, option_symbol=None, option_entry_price=None)], tmp_path)
        llamadas = []
        with patch.object(pt.yf, 'Ticker', lambda s: llamadas.append(s)):
            t.update_leaps_contracts()
        assert not llamadas, "sin símbolo OCC no hay nada que bajar"

    def test_entrada_invalida_no_produce_retorno(self, tmp_path):
        hoy = pd.Timestamp.now().normalize()
        emision = hoy - timedelta(days=10)
        t = _tracker([_fila(10, option_entry_price=0.0)], tmp_path)
        h = _hist([(emision + timedelta(days=7), 130.0)])
        with patch.object(pt.yf, 'Ticker', lambda s: type('T', (), {'history': lambda *a, **k: h})()):
            t.update_leaps_contracts()
        assert pd.isna(t.recommendations.at[0, 'option_return_7d']), "dividir por cero no es un retorno"
