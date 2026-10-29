#!/usr/bin/env python3
"""Rebote tras resultados: caída anormal, por resultados, buenos, barata y sobrevendida."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rebote_tras_resultados as rr


def _hist(caidas=(-0.10,), n=80, base=100.0, ruido=0.01, semilla=1):
    """Sesiones diarias con ruido normal y las caídas dadas al final."""
    rng = np.random.default_rng(semilla)
    rets = list(rng.normal(0, ruido, n)) + list(caidas)
    close = base * np.cumprod(1 + np.array(rets))
    idx = pd.bdate_range('2026-06-01', periods=len(close))
    return pd.DataFrame({'Open': close, 'High': close * 1.005, 'Low': close * 0.995,
                         'Close': close}, index=idx)


class TestCaidaAnormal:
    def test_una_caida_de_diez_desviaciones_lo_es(self):
        c = rr.caida_anormal(_hist((-0.10,)))
        assert c and c['caida_pct'] < -5 and c['z'] <= -3

    def test_un_mal_dia_normal_no_lo_es(self):
        assert rr.caida_anormal(_hist((-0.015,))) is None

    def test_en_un_valor_muy_volatil_un_menos_seis_no_es_anormal(self):
        assert rr.caida_anormal(_hist((-0.06,), ruido=0.04)) is None

    def test_poco_historial_no_da_veredicto(self):
        assert rr.caida_anormal(_hist((-0.10,), n=20)) is None


class TestReaccion:
    def test_tras_el_cierre_se_mide_desde_el_cierre_de_ese_dia(self):
        h = _hist((-0.10,))
        fecha = h.index[-2]
        r = rr.reaccion(h, fecha, tras_cierre=True)
        assert r['cierre_previo'] == round(float(h['Close'].iloc[-2]), 2)
        assert r['stop'] < r['precio'] < r['cierre_previo'] and r['rr'] > 0

    def test_antes_de_la_apertura_se_mide_desde_el_dia_anterior(self):
        h = _hist((-0.10,))
        r = rr.reaccion(h, h.index[-1], tras_cierre=False)
        assert r['cierre_previo'] == round(float(h['Close'].iloc[-2]), 2)

    def test_resultados_viejos_no_explican_la_caida_de_hoy(self):
        h = _hist((-0.10,))
        assert rr.reaccion(h, h.index[-20], tras_cierre=True) is None

    def test_si_ya_recupero_el_cierre_previo_no_hay_rebote_que_coger(self):
        h = _hist((-0.10, 0.15))
        assert rr.reaccion(h, h.index[-3], tras_cierre=True) is None


class TestFechaDeResultados:
    class _Tk:
        def __init__(self, df):
            self.df = df

        def get_earnings_dates(self, limit=8):
            return self.df

    def _ed(self, filas):
        idx = pd.DatetimeIndex([pd.Timestamp(f, tz='America/New_York') for f, *_ in filas])
        return pd.DataFrame({'EPS Estimate': [e for _, e, _, _ in filas],
                             'Reported EPS': [r for _, _, r, _ in filas],
                             'Surprise(%)': [s for _, _, _, s in filas]}, index=idx)

    def test_sin_bpa_cargado_cuenta_igual_por_fecha(self):
        # WMT y TJX el 29-oct-2026: el BPA de agosto seguía sin cargar
        ed = self._ed([('2026-11-19 07:00', 0.64, None, None),
                       ('2026-08-20 08:00', 0.74, None, None),
                       ('2026-05-21 06:00', 0.66, 0.66, 0.19)])
        fecha, tras_cierre, sorpresa = rr.ultimos_resultados(self._Tk(ed), pd.Timestamp('2026-10-29', tz='UTC'))
        assert fecha == pd.Timestamp('2026-08-20') and not tras_cierre and sorpresa is None

    def test_las_16h_es_tras_el_cierre(self):
        ed = self._ed([('2026-10-28 16:00', 3.02, 2.67, -11.5)])
        fecha, tras_cierre, sorpresa = rr.ultimos_resultados(self._Tk(ed), pd.Timestamp('2026-10-30', tz='UTC'))
        assert tras_cierre and sorpresa == -11.5


class TestValoracion:
    def test_recorrido_al_objetivo_pe_con_el_precio_de_hoy(self):
        assert rr.valoracion_pe(pd.Series({'target_price_pe': 120.0}), 100.0) == 20.0

    def test_sin_multiplo_propio_no_se_dice_que_este_barata(self):
        assert rr.valoracion_pe(pd.Series({'target_price_pe': None}), 100.0) is None
        assert rr.valoracion_pe(None, 100.0) is None


def _setup(**k):
    base = {'ticker': 'AAA', 'price': 90.0, 'target': 100.0, 'stop': 85.0, 'rr': 2.0,
            'caida_pct': -10.0, 'rsi2': 3.0, 'upside_pe': 25.0, 'fecha_resultados': '2026-10-28',
            'beneficio': 'batió', 'ventas': 'batió', 'prevision': 'MANTIENE', 'por_que_cae': 'capex'}
    base.update(k)
    return base


class TestMensaje:
    def test_dice_que_hacer_y_cuando_deja_de_valer(self, monkeypatch):
        monkeypatch.setattr(rr, 'historial', lambda: (0, None))
        m = rr.mensaje([_setup()], '2026-10-30')
        assert 'mantiene la previsión' in m and 'Entrada pequeña' in m
        assert '100,00 $' in m and '85,00 $' in m
        assert 'aún sin historial' in m

    def test_con_historial_lo_dice(self, monkeypatch):
        monkeypatch.setattr(rr, 'historial', lambda: (12, 58))
        assert '58% de aciertos a 30 días en 12 casos' in rr.mensaje([_setup()], '2026-10-30')


class TestEmbudo:
    """Lo barato decide antes de pagar una consulta a Claude."""

    def _correr(self, monkeypatch, tmp_path, fund, resultados='BUENOS'):
        h = _hist((-0.12,))
        monkeypatch.setattr(rr, '_universo', lambda: ['AAA'])
        monkeypatch.setattr(rr, '_historicos', lambda ts: {'AAA': h})
        monkeypatch.setattr(rr, 'ultimos_resultados', lambda tk, ahora=None: (h.index[-2], True, None))
        fund.to_csv(tmp_path / 'f.csv', index=False)
        monkeypatch.setattr(rr, 'FUND_CSV', tmp_path / 'f.csv')
        consultas = []
        monkeypatch.setattr(rr, 'comprobar_resultados', lambda *a: consultas.append(a) or {
            'resultados': resultados, 'beneficio': 'batió', 'ventas': 'batió',
            'prevision': 'MANTIENE', 'por_que_cae': 'capex', 'fuentes': 2})
        import yfinance
        monkeypatch.setattr(yfinance, 'Ticker', lambda t: None)
        return rr.detectar('2026-10-30'), consultas

    def test_buena_empresa_buenos_resultados_barata_y_sobrevendida(self, monkeypatch, tmp_path):
        fund = pd.DataFrame([{'ticker': 'AAA', 'company_name': 'Aaa', 'target_price_pe': 500.0}])
        setups, consultas = self._correr(monkeypatch, tmp_path, fund)
        assert [s['ticker'] for s in setups] == ['AAA'] and len(consultas) == 1

    def test_cara_a_su_pe_de_siempre_no_se_pregunta(self, monkeypatch, tmp_path):
        fund = pd.DataFrame([{'ticker': 'AAA', 'company_name': 'Aaa', 'target_price_pe': 1.0}])
        setups, consultas = self._correr(monkeypatch, tmp_path, fund)
        assert setups == [] and consultas == []

    def test_resultados_malos_no_avisan(self, monkeypatch, tmp_path):
        fund = pd.DataFrame([{'ticker': 'AAA', 'company_name': 'Aaa', 'target_price_pe': 500.0}])
        setups, _ = self._correr(monkeypatch, tmp_path, fund, resultados='MALOS')
        assert setups == []
