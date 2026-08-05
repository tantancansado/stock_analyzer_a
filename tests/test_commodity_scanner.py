#!/usr/bin/env python3
"""Tests de commodity_scanner — bandas de ciclo/estacionalidad por sector.

El 5-ago-2026 la ficha de UNG (Gas Natural) publicada en la app describía el
mercado del petróleo ("OPEC+ recorta producción... acuerdo nuclear Irán")
porque CYCLE_CONTEXT y SEASONALITY estaban indexados por `commodity_type`
("Energy"), y petróleo WTI, Brent y gas natural comparten ese tipo aunque sus
ciclos no tengan nada que ver entre sí.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commodity_scanner import (CYCLE_CONTEXT, SEASONALITY, _cycle_context,
                               _seasonality_signal)


class TestCycleContextPorSector:
    def test_gas_natural_no_habla_de_petroleo(self):
        # "producción shale" SÍ pertenece a gas natural (~70% de la oferta
        # USA es shale gas) — lo que no pertenece es el lenguaje de mercado
        # del crudo: OPEP no fija cuotas de gas, y el acuerdo nuclear de Irán
        # es un driver de petróleo, no de gas.
        gas = _cycle_context('Gas Natural', 'Energy')
        texto = ' '.join(gas.values()).lower()
        assert 'opec' not in texto
        assert 'irán' not in texto and 'iran' not in texto

    def test_gas_y_petroleo_ya_no_comparten_texto(self):
        assert _cycle_context('Gas Natural', 'Energy') != _cycle_context('Petróleo WTI', 'Energy')

    def test_petroleo_wti_y_brent_tienen_entradas_propias(self):
        # Antes de la separación por sector, ambos ya usaban texto de petróleo
        # (correcto) — se confirma que la especialización no rompió eso
        wti = _cycle_context('Petróleo WTI', 'Energy')
        brent = _cycle_context('Petróleo Brent', 'Energy')
        assert 'opec' in wti['driver'].lower() or 'opec' in wti['bullish'].lower()
        assert 'opec' in brent['driver'].lower() or 'opec' in brent['bullish'].lower()

    def test_sector_sin_entrada_especifica_usa_el_generico_del_tipo(self):
        # Oro no tiene entrada propia — cae al genérico de Precious_Metal
        oro = _cycle_context('Oro', 'Precious_Metal')
        assert oro == CYCLE_CONTEXT['Precious_Metal']

    def test_sector_y_tipo_desconocidos_no_rompen(self):
        assert _cycle_context('Inventado', 'Tambien_Inventado') == {}


class TestSeasonalityPorSector:
    def test_gas_y_petroleo_tienen_calendarios_distintos(self):
        for mes in range(1, 13):
            gas = _seasonality_signal('Gas Natural', 'Energy', mes)
            oil = _seasonality_signal('Petróleo WTI', 'Energy', mes)
            assert gas in ('bullish', 'neutral', 'bearish')
            assert oil in ('bullish', 'neutral', 'bearish')
        # Al menos en algún mes deben discrepar — si no, seguirían siendo la
        # misma tabla en la práctica
        discrepan = any(
            _seasonality_signal('Gas Natural', 'Energy', m) != _seasonality_signal('Petróleo WTI', 'Energy', m)
            for m in range(1, 13)
        )
        assert discrepan

    def test_gas_invierno_alcista_verano_bajista(self):
        # Retirada de almacenamiento en invierno (demanda calefacción) vs
        # inyección en primavera/verano — ciclo físico bien documentado
        assert _seasonality_signal('Gas Natural', 'Energy', 1) == 'bullish'   # enero
        assert _seasonality_signal('Gas Natural', 'Energy', 5) == 'bearish'   # mayo

    def test_mes_fuera_de_rango_no_rompe(self):
        assert _seasonality_signal('Gas Natural', 'Energy', 13) == 'neutral'

    def test_sector_sin_tabla_propia_cae_al_tipo(self):
        assert _seasonality_signal('Oro', 'Precious_Metal', 8) == \
               SEASONALITY['Precious_Metal'][8]


class TestUniverso:
    def test_gas_natural_tiene_alternativa_ucits(self):
        from commodity_scanner import UNIVERSE
        gas = next(u for u in UNIVERSE if u[0] == 'UNG')
        assert gas[3] == 'Gas Natural'
        assert gas[5] == 'NGAS.L'   # comprable en IBKR Ireland
