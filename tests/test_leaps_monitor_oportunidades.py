#!/usr/bin/env python3
"""Alertas de LEAPS NUEVOS — sin red.

Hueco detectado el 10-sep-2026: de las tres cosas que el usuario quiere por
Telegram (value nuevo, LEAPS nuevos, rebotes reales), la segunda no tenía
alerta ninguna. `leaps_monitor` solo vigilaba posiciones ABIERTAS — y el
usuario no tiene ninguna, así que `main()` salía por el return temprano antes
de mirar nada más. Además el escaneo corre a las 18:02, seis horas después del
briefing diario, así que sus hallazgos tampoco entraban en el único mensaje
del día: encontraba oportunidades y no las contaba.
"""
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import leaps_monitor as lm


def _lista(*tickers):
    return {'opportunities': [
        {'ticker': t, 'situation': 'CALIDAD_RAZONABLE', 'pct_from_52w_high': -10.0,
         'opportunity_score': 90.0,
         'recommended_contract': {'strike': 100.0, 'expiry': '2028-01-21',
                                  'cost_per_contract': 5000.0, 'breakeven': 150.0,
                                  'breakeven_move_pct': 7.5, 'leverage': 2.5,
                                  'iv_richness': 'cara'}}
        for t in tickers]}


def _correr(tmp_path, lista, sent):
    p = tmp_path / 'leaps_opportunities.json'
    p.write_text(json.dumps(lista))
    enviados = []
    with patch.object(lm, 'OPORTUNIDADES', p), \
         patch.object(lm, '_send_telegram', lambda t: enviados.append(t)):
        n = lm.alertar_oportunidades_nuevas(sent)
    return n, enviados


class TestOportunidadesNuevas:
    def test_avisa_de_las_que_entran(self, tmp_path):
        n, env = _correr(tmp_path, _lista('MSFT', 'BAC'), {})
        assert n == 2
        assert 'MSFT' in env[0] and 'BAC' in env[0]
        assert 'Breakeven' in env[0]

    def test_no_repite_al_dia_siguiente(self, tmp_path):
        sent = {}
        _correr(tmp_path, _lista('MSFT'), sent)
        n, env = _correr(tmp_path, _lista('MSFT'), sent)
        assert n == 0
        assert not env, "una oportunidad que sigue en lista no es noticia cada día"

    def test_solo_avisa_de_la_que_es_nueva(self, tmp_path):
        sent = {}
        _correr(tmp_path, _lista('MSFT'), sent)
        n, env = _correr(tmp_path, _lista('MSFT', 'UNH'), sent)
        assert n == 1
        assert 'UNH' in env[0] and 'MSFT' not in env[0]

    def test_si_desaparece_y_vuelve_avisa_otra_vez(self, tmp_path):
        sent = {}
        _correr(tmp_path, _lista('MSFT'), sent)
        _correr(tmp_path, _lista('BAC'), sent)            # MSFT se cae de la lista
        n, env = _correr(tmp_path, _lista('MSFT'), sent)  # y vuelve semanas después
        assert n == 1, "al reaparecer vuelve a ser una oportunidad nueva"
        assert 'MSFT' in env[0]

    def test_lista_vacia_no_avisa(self, tmp_path):
        n, env = _correr(tmp_path, {'opportunities': []}, {})
        assert n == 0 and not env

    def test_sin_fichero_no_revienta(self, tmp_path):
        with patch.object(lm, 'OPORTUNIDADES', tmp_path / 'no_existe.json'):
            assert lm.alertar_oportunidades_nuevas({}) == 0


class TestCorreSinPosicionesAbiertas:
    """El bug de fondo: main() salía por el return temprano cuando no había
    posiciones, así que las oportunidades nuevas no llegaban a mirarse. El
    usuario tiene cero posiciones LEAPS, o sea que ese era SIEMPRE el camino."""

    def test_main_anuncia_oportunidades_aunque_no_haya_posiciones(self, tmp_path):
        p = tmp_path / 'leaps_opportunities.json'
        p.write_text(json.dumps(_lista('MSFT')))
        enviados, guardado = [], {}
        with patch.object(lm, 'OPORTUNIDADES', p), \
             patch.object(lm, 'STATUS_OUT', tmp_path / 'status.json'), \
             patch.object(lm, 'load_option_positions', lambda: []), \
             patch.object(lm, '_load_sent', lambda: {}), \
             patch.object(lm, '_save_sent', guardado.update), \
             patch.object(lm, '_send_telegram', lambda t: enviados.append(t)):
            lm.main()
        assert enviados, "sin posiciones abiertas también hay que anunciar lo nuevo"
        assert 'MSFT' in enviados[0]
        assert guardado.get(lm.CLAVE_OPORTUNIDADES) == ['MSFT'], \
            "el estado debe persistirse o mañana se repite la misma alerta"
