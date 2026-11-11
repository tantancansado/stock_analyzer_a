#!/usr/bin/env python3
"""Lo que fue Prioridad se vende cuando deja de serlo, no al objetivo (11-nov-2026).

Medido en la reconstrucción 2020-26 (cartera al 10 % por idea, solo EE. UU.): la
misma rentabilidad que esperar al objetivo (+21 % frente a +20 % al año) pero
ganando al S&P en el 87-89 % de los periodos de 12 meses en vez del 75 %. Entra con
el PER por debajo de -1σ y sale por encima de -0,75σ. «No lo sé» no vende.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import portfolio_price_alerts as pa
import position_sizer as ps
import value_bands as vb


def _estado(**kw):
    base = {'ticker': 'AAA', 'value_grupo': 'OBSERVAR', 'motivo_fuera': '', 'per_z': -0.9,
            'ventas_anual_pct': 12.0, 'negative_roe': False, 'analyst_upside_pct': 15.0,
            'bpa_sobre_tendencia_pct': 5.0}
    return pd.DataFrame([{**base, **kw}])


def _motivo(veredictos=None, **kw):
    return vb.motivo_de_venta(_estado(**kw), veredictos).iloc[0]


class TestCuandoSeVende:
    def test_en_prioridad_se_mantiene(self):
        assert _motivo(value_grupo='PRIORIDAD', per_z=-1.4) == ''

    def test_con_el_per_en_el_margen_se_mantiene(self):
        """Entre -1σ y -0,75σ ya no es Prioridad, pero no se vende: sin margen, un PER en
        el borde haría vender y recomprar cada semana."""
        assert _motivo(per_z=-0.9) == ''

    def test_con_el_per_ya_normal_se_vende(self):
        assert 'PER ya no está barato' in _motivo(per_z=-0.6)
        assert '-0,60σ' in _motivo(per_z=-0.6)

    def test_si_las_ventas_dejan_de_crecer_al_10_se_vende(self):
        assert 'menos del 10 %' in _motivo(ventas_anual_pct=7.0)

    def test_si_sale_de_la_puerta_se_dice_por_que(self):
        assert _motivo(value_grupo='', motivo_fuera='nuestra valoración solo le ve +4%') == \
            'nuestra valoración solo le ve +4%'

    @pytest.mark.parametrize('falta', ['sin valoración propia que la respalde',
                                       'sin dato de ventas para ver si el negocio empeora'])
    def test_no_lo_se_no_vende(self, falta):
        assert _motivo(value_grupo='', motivo_fuera=falta) == ''

    def test_sin_historia_de_per_no_vende(self):
        assert _motivo(per_z=np.nan) == ''

    def test_los_descartes_duros_venden(self):
        assert 'pico' in _motivo(value_grupo='', bpa_sobre_tendencia_pct=80.0)
        assert 'ROE' in _motivo(value_grupo='', negative_roe='True')
        assert 'analistas' in _motivo(value_grupo='', analyst_upside_pct=-3.0)

    def test_el_deterioro_vende_aunque_el_integrador_la_tenga_en_prioridad(self):
        assert 'deterioro' in _motivo({'AAA': 'DETERIORO'}, value_grupo='PRIORIDAD', per_z=-1.5)

    def test_el_estado_lleva_tambien_lo_que_queda_fuera(self):
        df = pd.DataFrame([{'ticker': 'AAA', 'value_grupo': '', 'per_z': -0.2, 'otra': 1}])
        e = vb.estado_value(df, pd.Series(['nuestra valoración solo le ve +2%']))
        assert list(e.columns) == ['ticker', 'value_grupo', 'motivo_fuera', 'per_z']
        assert e.at[0, 'motivo_fuera'] == 'nuestra valoración solo le ve +2%'


def _docs(tmp_path, estado, tracker, cache=None):
    (tmp_path / 'portfolio_tracker').mkdir()
    pd.DataFrame(tracker, columns=['ticker', 'value_grupo']).to_csv(
        tmp_path / 'portfolio_tracker' / 'recommendations.csv', index=False)
    if estado is not None:
        pd.concat(estado, ignore_index=True).to_csv(tmp_path / 'value_estado.csv', index=False)
    if cache is not None:
        (tmp_path / 'why_cheap_cache.json').write_text(json.dumps(cache))
    return tmp_path


class TestSoloLoQueFuePrioridad:
    def test_lo_que_nunca_fue_prioridad_no_entra(self, tmp_path):
        docs = _docs(tmp_path, [_estado(ticker='AAA', per_z=-0.2), _estado(ticker='BBB', per_z=-0.2)],
                     [('AAA', 'PRIORIDAD'), ('BBB', 'OBSERVAR')])
        motivos = ps.motivos_de_venta(docs)
        assert set(motivos) == {'AAA'}
        assert 'PER' in motivos['AAA']

    def test_el_deterioro_sale_de_la_cache_de_noticias(self, tmp_path):
        docs = _docs(tmp_path, [_estado(ticker='AAA', value_grupo='PRIORIDAD', per_z=-1.5)],
                     [('AAA', 'PRIORIDAD')], {'AAA': {'veredicto': 'DETERIORO'}})
        assert 'deterioro' in ps.motivos_de_venta(docs)['AAA']

    def test_sin_el_estado_no_se_decide_nada(self, tmp_path):
        assert ps.motivos_de_venta(_docs(tmp_path, None, [('AAA', 'PRIORIDAD')])) == {}


class TestEnLaCartera:
    def test_el_peso_dice_vender(self):
        r = ps.peso_de_posicion(8.0, 'OBSERVAR', 30.0, venta='su PER ya no está barato')
        assert r['accion'] == 'VENDER' and r['objetivo'] == 0.0
        assert 'Fue Prioridad y ya no lo es' in r['motivo']

    def test_sin_motivo_sigue_como_siempre(self):
        assert ps.peso_de_posicion(8.0, 'OBSERVAR', 30.0, venta='')['accion'] == 'MANTENER'

    def test_mi_cartera_lo_vende_y_recomienda_cero(self, monkeypatch):
        import ticker_api as api
        idx = pd.bdate_range('2025-11-01', periods=260)
        rng = np.random.default_rng(1)
        precios = pd.DataFrame({'AAA': 100 * np.exp(np.cumsum(rng.normal(0, 0.30 / np.sqrt(252), 260)))}, index=idx)
        monkeypatch.setattr(ps, 'precios_diarios', lambda t: precios)
        enriched = [{'ticker': 'AAA', 'asset_type': 'stock', 'es_fondo': False, 'portfolio_pct': 8.0,
                     'current_price': 100.0}]
        api._pesos_de_cartera(enriched, {'AAA': {'value_grupo': 'OBSERVAR', 'motivo_venta': 'su PER ya no está barato'}})
        assert enriched[0]['peso_accion'] == 'VENDER'
        assert enriched[0]['peso_recomendado_pct'] == 0.0


class TestElAviso:
    UMBRALES = (30.0, 40.0)

    def test_lo_que_fue_prioridad_avisa_por_su_regla_y_no_por_el_objetivo(self):
        # Llegó al objetivo (upside -2 %), pero su venta la decide la regla de Prioridad.
        valoradas = pd.DataFrame([{'ticker': 'AAA', 'current_price': 100.0, 'upside_triangulated_pct': -2.0}])
        avisos = pa.avisos_de_cartera(['AAA', 'BBB'], valoradas, self.UMBRALES,
                                      {'AAA': '', 'BBB': 'su PER ya no está barato'})
        assert avisos == [{'ticker': 'BBB', 'tipo': 'PRIORIDAD', 'motivo': 'su PER ya no está barato'}]

    def test_lo_que_no_tienes_no_avisa(self):
        assert pa.avisos_de_cartera(['AAA'], pd.DataFrame(), self.UMBRALES, {'ZZZ': 'algo'}) == []

    def test_el_texto(self):
        t = pa.texto([{'ticker': 'BBB', 'tipo': 'PRIORIDAD', 'motivo': 'su PER ya no está barato'}])
        assert t == '<b>Toca vender</b>\n<b>BBB</b> ya no es Prioridad: su PER ya no está barato.'
