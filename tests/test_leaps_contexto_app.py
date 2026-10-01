"""LEAPS lee lo que la app YA sabe en vez de preguntárselo a Claude a ciegas.

El 1-oct-2026 MCD llegó por Telegram. La ficha VALUE ya decía «EVENTO — Investor
Day del 23-sep, guía rebajada» (investigado con web y cacheado) y «ESPERAR»; el
gate de LEAPS preguntó a Claude, sin web, por qué había caído, y contestó «caída
cíclica, consumo más débil». El dato bueno estaba en el mismo CSV que LEAPS ya
leía y no lo cogía.
"""
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import leaps_analyzer as la


def _opp(**extra):
    base = {
        'ticker': 'MCD', 'company_name': "McDonald's", 'sector': 'Consumer Cyclical',
        'spot': 231.85, 'quality_score': 63.7, 'analyst_upside_pct': 28.6,
        'pct_from_52w_high': -30.8, 'ytd_pct': -22.0, 'forward_pe': 16.8,
        'trailing_pe': 18.8, 'situation': 'CAIDA_CIRCUNSTANCIAL',
        'recommended_contract': {
            'strike': 175.0, 'expiry': '2028-01-21', 't_years': 1.31, 'mid': 65.6,
            'cost_per_contract': 6562.0, 'delta': 0.8, 'leverage': 2.8,
            'annual_carry_pct': 3.0, 'total_annual_cost_pct': 6.2,
            'forgone_dividend_pct': 3.2, 'iv_pct': 32.7, 'iv_richness': 'cara',
            'iv_vs_hv': 1.7, 'roundtrip_spread_usd': 195, 'volume': 3,
            'breakeven': 241.0, 'breakeven_move_pct': 3.8,
        },
        'profit_at_target': {},
    }
    base.update(extra)
    return base


def _prompt_enviado(opp):
    visto = {}

    def falso(**kw):
        visto['prompt'] = kw['messages'][0]['content']
        return None
    import groq_utils
    with patch.object(groq_utils, 'claude_chat', falso):
        la.add_ai_narrative(opp)
    return visto['prompt']


class TestSenalesDeLaLista:
    def test_load_app_signals_trae_el_por_que_cae(self, tmp_path):
        pd.DataFrame([{'ticker': 'MCD', 'why_cheap': 'EVENTO',
                       'why_cheap_resumen': 'Investor Day 23-sep',
                       'entry_readiness': 'ESPERAR'}]
                     ).to_csv(tmp_path / 'value_opportunities.csv', index=False)
        with patch.object(la, 'DOCS', tmp_path):
            s = la.load_app_signals()['MCD']
        assert s['why_cheap'] == 'EVENTO'
        assert s['why_cheap_resumen'] == 'Investor Day 23-sep'

    def test_sin_analisis_queda_a_none_no_a_nan(self, tmp_path):
        pd.DataFrame([{'ticker': 'MA', 'why_cheap': None, 'why_cheap_resumen': None,
                       'entry_readiness': 'VIGILAR'}]
                     ).to_csv(tmp_path / 'value_opportunities.csv', index=False)
        with patch.object(la, 'DOCS', tmp_path):
            s = la.load_app_signals()['MA']
        assert s['why_cheap'] is None and s['why_cheap_resumen'] is None


class TestElPromptLlevaLoQueLaAppSabe:
    def test_incluye_la_causa_investigada_y_el_estado_de_entrada(self):
        p = _prompt_enviado(_opp(
            why_cheap='EVENTO', why_cheap_resumen='Investor Day 23-sep, guía rebajada',
            entry_readiness='ESPERAR',
            entry_readiness_reason='En caída (bajo MA200 descendente)'))
        assert 'EVENTO' in p and 'Investor Day 23-sep' in p
        assert 'ESPERAR' in p and 'bajo MA200 descendente' in p
        assert 'MANDA sobre cualquier suposición' in p

    def test_sin_investigacion_se_lo_dice_en_vez_de_dejarle_suponer(self):
        p = _prompt_enviado(_opp(why_cheap=None))
        assert 'no lo ha investigado' in p

    def test_sin_datos_cuenta_como_no_investigado(self):
        p = _prompt_enviado(_opp(why_cheap='SIN_DATOS', why_cheap_resumen='nada'))
        assert 'no lo ha investigado' in p

    def test_sin_estado_de_entrada_no_se_inventa_linea(self):
        p = _prompt_enviado(_opp(entry_readiness=None))
        assert 'Estado de entrada de la ACCIÓN' not in p


class TestCompletarEntrada:
    def _con_motor(self, resultado=None, falla=False):
        import technical_filter as tf

        def calcula(ticker, spy):
            if falla:
                raise RuntimeError('sin red')
            return resultado
        return patch.multiple(tf, compute_technical_signals=calcula,
                              fetch_spy_6m_return=lambda: 5.0)

    def test_rellena_un_ticker_que_no_esta_en_la_lista_value(self):
        la._SPY_6M = None
        opp = _opp(entry_readiness=None)
        with self._con_motor({'entry_readiness': 'VIGILAR',
                              'entry_readiness_reason': 'Construyendo base'}):
            la.completar_entrada(opp)
        assert opp['entry_readiness'] == 'VIGILAR'
        assert opp['entry_readiness_reason'] == 'Construyendo base'

    def test_no_pisa_el_estado_que_ya_trae_la_ficha_value(self):
        opp = _opp(entry_readiness='ESPERAR', entry_readiness_reason='x')
        with self._con_motor({'entry_readiness': 'ENTRADA'}):
            la.completar_entrada(opp)
        assert opp['entry_readiness'] == 'ESPERAR'

    def test_sin_historico_no_inventa(self):
        la._SPY_6M = None
        opp = _opp(entry_readiness=None)
        with self._con_motor({'entry_readiness': None, 'entry_readiness_reason': 'sin histórico'}):
            la.completar_entrada(opp)
        assert opp.get('entry_readiness') is None

    def test_si_el_motor_revienta_el_leaps_sigue_vivo(self):
        la._SPY_6M = None
        opp = _opp(entry_readiness=None)
        with self._con_motor(falla=True):
            la.completar_entrada(opp)
        assert opp.get('entry_readiness') is None

