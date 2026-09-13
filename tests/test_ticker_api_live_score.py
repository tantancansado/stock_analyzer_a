#!/usr/bin/env python3
"""El score en vivo penalizaba por datos que faltaban, no por datos malos."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import ticker_api


OK_MA = {'passes': True, 'score': 90, 'reason': 'Above all MAs'}
OK_AD = {'signal': 'NEUTRAL', 'score': 55, 'reason': 'Balanced volume'}
RATE_LIMIT = 'Error: Too Many Requests. Rate limited. Try after a while.'


class TestNoEvaluado:

    @pytest.mark.parametrize('motivo', [
        RATE_LIMIT,
        'rate limit exceeded',
        'HTTP 429',
        'Insufficient data for 200 SMA',
        'Error: connection reset',
    ])
    def test_reconoce_los_motivos_de_no_evaluado(self, motivo):
        assert ticker_api._no_evaluado(motivo) is True

    @pytest.mark.parametrize('motivo', [
        'Price below 200 SMA',
        'Moderate distribution (0.8x ratio, 44% up volume)',
        '', None,
    ])
    def test_un_veredicto_real_no_es_no_evaluado(self, motivo):
        assert ticker_api._no_evaluado(motivo) is False


class TestPesosDelScore:

    def test_un_componente_ausente_reparte_su_peso(self):
        # Antes se sumaban los componentes presentes sin renormalizar, así que
        # un ticker sin VCP puntuaba sobre 60 y se presentaba sobre 100: AVGO,
        # con ML 50.6 y fundamental 64.1, daba una base de 34.4 en vez de 57.3.
        base, _, _ = ticker_api._calc_live_score(None, 50.6, 64.1, OK_MA, OK_AD)
        assert base == pytest.approx((50.6 * 0.3 + 64.1 * 0.3) / 0.6, abs=0.05)
        assert base > 57   # el viejo daba 34.4

    def test_con_los_tres_componentes_los_pesos_no_cambian(self):
        base, _, _ = ticker_api._calc_live_score(80.0, 60.0, 70.0, OK_MA, OK_AD)
        assert base == pytest.approx(80 * 0.4 + 60 * 0.3 + 70 * 0.3, abs=0.1)

    def test_un_solo_componente_vale_su_propio_valor(self):
        base, _, _ = ticker_api._calc_live_score(None, None, 64.1, OK_MA, OK_AD)
        assert base == pytest.approx(64.1, abs=0.1)

    def test_sin_ningun_componente_no_hay_score(self):
        assert ticker_api._calc_live_score(None, None, None, OK_MA, OK_AD) == (None, None, None)


class TestPenalizaciones:

    def test_un_filtro_de_media_movil_sin_evaluar_no_penaliza(self):
        # Regla del proyecto: un rate-limit no es una tendencia bajista.
        ma_caido = {'passes': False, 'score': 0, 'reason': RATE_LIMIT}
        _, pen, _ = ticker_api._calc_live_score(80.0, 60.0, 70.0, ma_caido, OK_AD)
        assert pen == 0

    def test_un_filtro_de_media_movil_que_falla_de_verdad_si_penaliza(self):
        ma_malo = {'passes': False, 'score': 20, 'reason': 'Price below 200 SMA'}
        _, pen, _ = ticker_api._calc_live_score(80.0, 60.0, 70.0, ma_malo, OK_AD)
        assert pen == 20

    def test_una_acumulacion_sin_evaluar_no_penaliza(self):
        ad_caido = {'signal': 'UNKNOWN', 'score': 50, 'reason': RATE_LIMIT}
        _, pen, _ = ticker_api._calc_live_score(80.0, 60.0, 70.0, OK_MA, ad_caido)
        assert pen == 0

    def test_distribucion_real_si_penaliza(self):
        ad_malo = {'signal': 'DISTRIBUTION', 'score': 35, 'reason': 'Moderate distribution'}
        _, pen, _ = ticker_api._calc_live_score(80.0, 60.0, 70.0, OK_MA, ad_malo)
        assert pen == 15   # 10 por la señal + 5 por el score bajo

    def test_el_final_nunca_baja_de_cero(self):
        ma_malo = {'passes': False, 'score': 10, 'reason': 'Price below 200 SMA'}
        ad_malo = {'signal': 'STRONG_DISTRIBUTION', 'score': 10, 'reason': 'Heavy selling'}
        _, _, final = ticker_api._calc_live_score(5.0, 5.0, 5.0, ma_malo, ad_malo)
        assert final == 0
