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


class TestResultadosBuenos:
    """La regla vive en el código; Claude solo trae los hechos con fuentes."""

    def _v(self, sorpresa, ventas='BATIO', prevision='MANTIENE'):
        return {'bpa_sorpresa_pct': sorpresa, 'ventas_vs_consenso': ventas, 'prevision': prevision}

    def test_now_29_oct_dos_centimos_por_debajo_subiendo_la_prevision_vale(self):
        assert rr.resultados_buenos(self._v(-2.0, prevision='SUBE'))

    def test_en_linea_sin_subir_la_prevision_no_basta(self):
        assert not rr.resultados_buenos(self._v(-2.0, prevision='MANTIENE'))

    def test_fallar_de_verdad_no_lo_arregla_la_prevision(self):
        assert not rr.resultados_buenos(self._v(-5.0, prevision='SUBE'))

    def test_batir_en_beneficio_y_ventas_manteniendo_la_prevision_vale(self):
        assert rr.resultados_buenos(self._v(4.0))

    def test_ventas_por_debajo_no_vale(self):
        assert not rr.resultados_buenos(self._v(4.0, ventas='FALLO', prevision='SUBE'))

    def test_recortar_la_prevision_no_vale(self):
        assert not rr.resultados_buenos(self._v(4.0, prevision='BAJA'))

    def test_sin_el_dato_del_bpa_no_hay_veredicto(self):
        assert not rr.resultados_buenos(self._v(None, prevision='SUBE'))

    def test_sin_fuentes_no_hay_resultados_buenos(self, monkeypatch):
        import json
        import claude_research
        hechos = json.dumps(self._v(4.0, prevision='SUBE'))
        monkeypatch.setattr(claude_research, 'ask_with_search', lambda *a, **k: (hechos, []))
        assert rr.comprobar_resultados('AAA', 'Aaa', '2026-10-28', -10.0)['resultados'] == 'NO'
        monkeypatch.setattr(claude_research, 'ask_with_search', lambda *a, **k: (hechos, ['https://x']))
        assert rr.comprobar_resultados('AAA', 'Aaa', '2026-10-28', -10.0)['resultados'] == 'BUENOS'


class TestVigia:
    """After-hours y preapertura: el pipeline de la mañana solo ve cierres."""

    def test_el_precio_de_preapertura_si_es_posterior_al_cierre(self):
        info = {'regularMarketTime': 100, 'preMarketTime': 200, 'preMarketPrice': 288.4,
                'postMarketTime': 50, 'postMarketPrice': 320.0}
        assert rr.precio_extendido(info) == (288.4, 'preapertura')

    def test_el_del_after_hours_si_es_el_ultimo(self):
        info = {'regularMarketTime': 100, 'postMarketTime': 150, 'postMarketPrice': 90.0}
        assert rr.precio_extendido(info) == (90.0, 'after-hours')

    def test_un_precio_fuera_de_hora_anterior_al_cierre_no_vale(self):
        # en plena sesión, o un festivo: lo de fuera de hora es de ayer
        info = {'regularMarketTime': 300, 'preMarketTime': 200, 'preMarketPrice': 90.0}
        assert rr.precio_extendido(info) is None

    def test_la_preapertura_es_la_sesion_de_hoy(self):
        h = _hist(n=70)
        hoy = h.index[-1]   # llega una barra a medias de hoy: fuera
        x = rr.con_sesion_extendida(h, 50.0, 'preapertura', hoy)
        assert x.index[-1] == hoy and x['Close'].iloc[-1] == 50.0
        assert x.index[-2] == h.index[-2]

    def test_el_after_hours_es_la_sesion_siguiente(self):
        h = _hist(n=70)
        viernes = h.index[h.index.day_of_week == 4][-1]
        x = rr.con_sesion_extendida(h[h.index <= viernes], 50.0, 'after-hours', viernes)
        assert x.index[-1] == viernes + pd.Timedelta(days=3) and x.index[-2] == viernes

    def test_el_lunes_mira_lo_que_publicaron_el_viernes(self):
        cal = {'AAA': ['2026-10-30'], 'BBB': ['2026-11-02'], 'CCC': ['2026-10-29'], 'ZZZ': ['2026-10-30']}
        assert rr.en_ventana(cal, pd.Timestamp('2026-11-02'), {'AAA', 'BBB', 'CCC'}) == ['AAA', 'BBB']

    def test_sin_nadie_en_la_ventana_no_descarga_nada(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rr, 'CALENDARIO', tmp_path / 'cal.json')
        (tmp_path / 'cal.json').write_text('{"AAA": ["2026-01-05"]}')
        monkeypatch.setattr(rr, '_universo', lambda: ['AAA'])
        monkeypatch.setattr(rr, '_historicos', lambda ts: (_ for _ in ()).throw(AssertionError('descargó')))
        assert rr.vigia(pd.Timestamp('2026-10-29 13:00', tz='UTC')) == []

    def _vigia(self, monkeypatch, tmp_path):
        import json
        import bounce_alerts
        import yfinance
        h = _hist(())
        hoy = h.index[-1] + pd.offsets.BDay(1)
        ahora = pd.Timestamp(hoy.date()).tz_localize('America/New_York') + pd.Timedelta(hours=8)
        (tmp_path / 'cal.json').write_text(json.dumps({'AAA': [str(h.index[-1].date())]}))
        pd.DataFrame([{'ticker': 'AAA', 'company_name': 'Aaa', 'target_price_pe': 500.0}]).to_csv(
            tmp_path / 'f.csv', index=False)
        for nombre, ruta in (('CALENDARIO', 'cal.json'), ('FUND_CSV', 'f.csv'),
                             ('AVISADOS', 'avisados.json'), ('EXTENDIDO', 'ext.csv')):
            monkeypatch.setattr(rr, nombre, tmp_path / ruta)
        monkeypatch.setattr(rr, '_universo', lambda: ['AAA', 'BBB.L'])
        monkeypatch.setattr(rr, '_historicos', lambda ts: {t: h for t in ts})
        monkeypatch.setattr(rr, 'historial', lambda: (0, None))
        monkeypatch.setattr(rr, 'ultimos_resultados', lambda tk, ahora=None: (h.index[-1], True, None))
        monkeypatch.setattr(rr, 'comprobar_resultados', lambda *a: {
            'resultados': 'BUENOS', 'beneficio': 'batió', 'ventas': 'batió',
            'prevision': 'SUBE', 'por_que_cae': 'capex', 'fuentes': 2})
        info = type('T', (), {'info': {'regularMarketTime': 1, 'preMarketTime': 2,
                                       'preMarketPrice': float(h['Close'].iloc[-1]) * 0.88}})
        monkeypatch.setattr(yfinance, 'Ticker', lambda t: info)
        enviados = []
        monkeypatch.setattr(bounce_alerts, '_send_telegram', lambda m: enviados.append(m) or True)
        return h, ahora, enviados

    def test_avisa_en_preapertura_y_el_tracker_lo_mide_desde_el_aviso(self, monkeypatch, tmp_path):
        h, ahora, enviados = self._vigia(monkeypatch, tmp_path)
        setups = rr.vigia(ahora)
        assert [s['ticker'] for s in setups] == ['AAA'] and 'en preapertura' in enviados[0]
        ext = pd.read_csv(tmp_path / 'ext.csv')
        # la señal es de la última sesión real; la de hoy ya es su recorrido
        assert ext['fecha_aviso'].tolist() == [str(h.index[-1].date())]

    def test_lo_que_avisó_el_vigía_no_se_repite(self, monkeypatch, tmp_path):
        _, ahora, enviados = self._vigia(monkeypatch, tmp_path)
        rr.vigia(ahora)
        assert rr.vigia(ahora) == [] and len(enviados) == 1


class TestCalendario:
    def test_recuerda_la_fecha_aunque_yahoo_ya_de_la_siguiente(self, monkeypatch, tmp_path):
        import json
        monkeypatch.setattr(rr, 'CALENDARIO', tmp_path / 'cal.json')
        monkeypatch.setattr(rr, 'FUND_CSV', tmp_path / 'f.csv')
        pd.DataFrame([{'ticker': 'AAA', 'earnings_date': '2026-10-28'}]).to_csv(tmp_path / 'f.csv', index=False)
        rr.actualizar_calendario('2026-10-28')
        # tras publicar, el scorer ya no da fecha (o da la de enero)
        pd.DataFrame([{'ticker': 'AAA', 'earnings_date': None}]).to_csv(tmp_path / 'f.csv', index=False)
        rr.actualizar_calendario('2026-10-29')
        assert json.loads((tmp_path / 'cal.json').read_text()) == {'AAA': ['2026-10-28']}

    def test_olvida_lo_de_hace_semanas(self, monkeypatch, tmp_path):
        import json
        monkeypatch.setattr(rr, 'CALENDARIO', tmp_path / 'cal.json')
        monkeypatch.setattr(rr, 'FUND_CSV', tmp_path / 'f.csv')
        (tmp_path / 'cal.json').write_text('{"AAA": ["2026-07-28", "2026-10-28"], "BBB": ["2026-07-30"]}')
        pd.DataFrame(columns=['ticker', 'earnings_date']).to_csv(tmp_path / 'f.csv', index=False)
        rr.actualizar_calendario('2026-10-29')
        assert json.loads((tmp_path / 'cal.json').read_text()) == {'AAA': ['2026-10-28']}
