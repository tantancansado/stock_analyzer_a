"""La historia del PER se reconstruye sin mirar al futuro y sin inventar nada."""
import json
import math

import pandas as pd
import pytest

import bandas_per as bp

HOY = pd.Timestamp('2026-11-07')


def _td(bpa, forward=None, neto=None):
    return {'analyst_estimates': {
        'historico_norm': {str(y): {'eps_norm': v, 'net_income_norm': (neto or {}).get(y, v * 100)} for y, v in bpa.items()},
        'forward': forward or {}}}


def _precios(desde='2011-01-31', hasta='2026-10-31', valor=100.0):
    idx = pd.date_range(desde, hasta, freq='ME')
    return pd.Series(valor, index=idx, dtype=float)


CRECE = {y: 4.0 * 1.05 ** (y - 2010) for y in range(2010, 2026)}


class TestCuandoSeConoce:
    def test_cierre_de_diciembre(self):
        assert bp.cierre_conocido(2025, 12) == pd.Timestamp(2025, 12, 28) + pd.Timedelta(days=60)

    def test_enero_es_del_año_siguiente(self):
        """WMT: la etiqueta 2025 de TIKR es el año cerrado en enero de 2026."""
        assert bp.cierre_conocido(2025, 1) == pd.Timestamp(2026, 1, 28) + pd.Timedelta(days=60)

    def test_febrero_es_del_mismo_año(self):
        """STZ: la etiqueta 2025 es febrero de 2025. Tratarla como la de enero le daba
        unas ventas de +2,5 % cuando el último año cerrado cayó un 10,5 %."""
        assert bp.cierre_conocido(2025, 2).year == 2025

    def test_mayo_es_del_mismo_año(self):
        """ORCL: la etiqueta 2025 es mayo de 2025."""
        assert bp.cierre_conocido(2025, 5).year == 2025


class TestSerieBpa:
    def test_un_año_cerrado_en_forward_cuenta(self):
        """MSFT: junio de 2026 ya está cerrado aunque TIKR lo lleve en forward."""
        s = bp.serie_bpa(_td({2024: 11.0, 2025: 13.6}, {'2026': {'eps_norm': 16.8}}), 6, HOY)
        assert s[2026] == 16.8

    def test_un_año_sin_cerrar_no_cuenta(self):
        s = bp.serie_bpa(_td({2024: 7.0, 2025: 7.5}, {'2026': {'eps_norm': 9.0}}), 12, HOY)
        assert 2026 not in s

    def test_rotura_de_base_corta_lo_anterior(self):
        """CTAS: acciones implícitas que saltan indican que la serie cambió de base."""
        bpa = {2010: 1.0, 2011: 1.1, 2012: 0.3, 2013: 0.33}
        neto = {2010: 100, 2011: 110, 2012: 120, 2013: 130}
        s = bp.serie_bpa(_td(bpa, neto=neto), 12, HOY)
        assert sorted(s) == [2012, 2013]


class TestVentasAnuales:
    def _td(self, v):
        return {'financials_history': {'metrics': {'total_revenue': {str(y): x for y, x in v.items()}}}}

    def test_ultimo_año_cerrado(self):
        r = bp.ventas_anuales(self._td({2023: 100.0, 2024: 110.0, 2025: 121.0}), 12, HOY)
        assert r == {'ventas_anual_pct': 10.0, 'ventas_anual_anio': 2025}

    def test_un_año_sin_cerrar_no_cuenta(self):
        r = bp.ventas_anuales(self._td({2024: 100.0, 2025: 110.0, 2026: 500.0}), 12, HOY)
        assert r['ventas_anual_anio'] == 2025

    def test_el_año_cerrado_cuenta_aunque_acabe_de_cerrar(self):
        """MSFT: el año fiscal 2026 acabó en junio de 2026."""
        r = bp.ventas_anuales(self._td({2025: 100.0, 2026: 118.0}), 6, HOY)
        assert r['ventas_anual_anio'] == 2026 and r['ventas_anual_pct'] == 18.0

    def test_sin_dos_años_seguidos_no_hay_dato(self):
        assert bp.ventas_anuales(self._td({2020: 100.0, 2025: 110.0}), 12, HOY) == {}
        assert bp.ventas_anuales({}, 12, HOY) == {}


class TestObjetivoPe:
    BANDA = {'bpa': 5.0, 'bpa_anio': 2025, 'mu': 3.0, 'sd': 0.2, 'mediana': 20.0, 'meses': 120}

    def _fund(self, precio=80.0, **extra):
        return pd.DataFrame([{'ticker': 'AAA', 'current_price': precio, 'target_price_pe': 999.0,
                              'target_price_pe_upside_pct': 999.0, 'pe_sin_ancla_motivo': 'vieja', **extra}])

    def test_mediana_por_bpa_normalizado(self):
        r, n = bp.reescribir_objetivo_pe(self._fund(), {'AAA': self.BANDA})
        assert n == 1 and r.at[0, 'target_price_pe'] == 100.0 and r.at[0, 'target_price_pe_upside_pct'] == 25.0
        assert 'TIKR' in r.at[0, 'pe_ancla'] and pd.isna(r.at[0, 'pe_sin_ancla_motivo'])

    def test_sin_tikr_se_queda_lo_de_yfinance(self):
        r, n = bp.reescribir_objetivo_pe(self._fund(), {})
        assert n == 0 and r.at[0, 'target_price_pe'] == 999.0

    def test_el_techo_de_burbuja_tambien_vale_aqui(self):
        """El usuario, 29-oct-2026: «no quiero precios de burbuja»."""
        r, n = bp.reescribir_objetivo_pe(self._fund(), {'AAA': {**self.BANDA, 'mediana': 51.0}})
        assert n == 0 and r.at[0, 'target_price_pe'] == 999.0

    def test_un_objetivo_absurdo_no_se_publica(self):
        r, n = bp.reescribir_objetivo_pe(self._fund(precio=30.0), {'AAA': self.BANDA})
        assert n == 0

    def test_no_muta_la_entrada(self):
        f = self._fund()
        bp.reescribir_objetivo_pe(f, {'AAA': self.BANDA})
        assert f.at[0, 'target_price_pe'] == 999.0


class TestBandas:
    def test_calcula_media_y_desviacion_del_log_del_per(self):
        b = bp.bandas_de_ticker(_td(CRECE), _precios(), 12, HOY)
        assert b['bpa_anio'] == 2025 and b['meses'] == 120
        assert 2.0 < b['mu'] < 4.5 and b['sd'] > 0

    def test_no_usa_un_bpa_antes_de_conocerlo(self):
        """Con cierre en diciembre, en enero de 2026 aún manda el BPA de 2024."""
        b = bp.bandas_de_ticker(_td(CRECE), _precios(hasta='2026-01-31'), 12, pd.Timestamp('2026-01-15'))
        assert b['bpa_anio'] == 2024

    def test_bpa_negativo_no_da_per(self):
        bpa = dict(CRECE); bpa[2025] = -1.0
        assert 'negativo' in bp.bandas_de_ticker(_td(bpa), _precios(), 12, HOY)['motivo']

    def test_con_poca_historia_no_hay_bandas(self):
        b = bp.bandas_de_ticker(_td({y: 5.0 for y in range(2022, 2026)}), _precios(desde='2023-01-31'), 12, HOY)
        assert 'meses' in b['motivo']

    def test_sin_tikr_no_hay_bandas(self):
        assert 'motivo' in bp.bandas_de_ticker({}, _precios(), 12, HOY)

    def test_per_absurdos_no_cuentan(self):
        """Un BPA deprimido da múltiplos de 500x que descolocarían la media."""
        sano = bp.bandas_de_ticker(_td(CRECE), _precios(), 12, HOY)
        bpa = dict(CRECE); bpa[2018] = 0.1
        con_valle = bp.bandas_de_ticker(_td(bpa), _precios(), 12, HOY)
        assert abs(con_valle['mu'] - sano['mu']) < 0.15

    def test_beneficio_sobre_su_tendencia(self):
        bpa = dict(CRECE); bpa[2025] = CRECE[2025] * 2
        b = bp.bandas_de_ticker(_td(bpa), _precios(), 12, HOY)
        assert b['tendencia_pct'] == pytest.approx(100, abs=5)


class TestAplicar:
    BANDAS = {'bandas': {'AAA': {'bpa': 5.0, 'bpa_anio': 2025, 'mu': math.log(20.0), 'sd': 0.2, 'mediana': 20.0, 'meses': 120, 'tendencia_pct': 8.0, 'ventas_anual_pct': 14.0, 'ventas_anual_anio': 2025},
                         'BBB': {'motivo': 'cotiza y presenta cuentas en divisas distintas'}}}

    def _aplicar(self, filas, consenso=None):
        return bp.aplicar(pd.DataFrame(filas), self.BANDAS, consenso or {}).set_index('ticker')

    def test_la_desviacion_sale_del_precio_del_dia(self):
        r = self._aplicar([{'ticker': 'AAA', 'current_price': 100.0}, ])
        assert r.loc['AAA', 'per_z'] == 0.0 and r.loc['AAA', 'per_norm'] == 20.0
        r = self._aplicar([{'ticker': 'AAA', 'current_price': 100.0 * math.exp(-0.3)}])
        assert r.loc['AAA', 'per_z'] == pytest.approx(-1.5, abs=0.01)

    def test_los_precios_de_cada_banda(self):
        r = self._aplicar([{'ticker': 'AAA', 'current_price': 100.0}])
        assert r.loc['AAA', 'precio_per_media'] == 100.0
        assert r.loc['AAA', 'precio_per_menos_1s'] == pytest.approx(100 * math.exp(-0.2), abs=0.01)
        assert r.loc['AAA', 'bpa_sobre_tendencia_pct'] == 8.0
        assert r.loc['AAA', 'ventas_anual_pct'] == 14.0

    def test_lo_que_no_se_sabe_dice_por_que(self):
        r = self._aplicar([{'ticker': 'BBB', 'current_price': 100.0}, {'ticker': 'CCC', 'current_price': 100.0}])
        assert pd.isna(r.loc['BBB', 'per_z']) and 'divisas' in r.loc['BBB', 'per_sin_dato_motivo']
        assert r.loc['CCC', 'per_sin_dato_motivo'] == 'sin bandas de PER'

    def test_sin_precio_no_hay_desviacion(self):
        r = self._aplicar([{'ticker': 'AAA', 'current_price': float('nan')}])
        assert pd.isna(r.loc['AAA', 'per_z'])

    def test_no_pierde_filas_ni_duplica_columnas(self):
        df = pd.DataFrame([{'ticker': 'AAA', 'current_price': 100.0, 'per_z': 9.9}])
        r = bp.aplicar(df, self.BANDAS, {})
        assert len(r) == 1 and list(r.columns).count('per_z') == 1 and r['per_z'].iloc[0] == 0.0


class TestRevisiones:
    def test_cuatro_y_trece_semanas(self):
        h = {'2026-08-02': 10.0, '2026-10-04': 10.5, '2026-11-01': 11.0}
        r = bp.revisiones(h, HOY)
        assert r['revision_13s_pct'] == 10.0 and r['revision_4s_pct'] == pytest.approx(4.8)

    def test_sin_foto_cercana_no_se_inventa(self):
        r = bp.revisiones({'2026-10-25': 10.0, '2026-11-01': 11.0}, HOY)
        assert r['revision_13s_pct'] is None and r['revision_4s_pct'] is None

    def test_un_salto_enorme_es_un_cambio_de_base(self):
        r = bp.revisiones({'2026-10-04': 10.0, '2026-11-01': 40.0}, HOY)
        assert r['revision_4s_pct'] is None

    def test_base_negativa_no_da_porcentaje(self):
        assert bp.revisiones({'2026-10-04': -1.0, '2026-11-01': 1.0}, HOY)['revision_4s_pct'] is None

    def test_sin_historial(self):
        assert bp.revisiones({}, HOY) == {'revision_4s_pct': None, 'revision_13s_pct': None}


class TestConsenso:
    def test_anota_la_foto_por_fecha(self):
        c = bp.anotar_consenso({'generated_at': '2026-11-01T13:52:16', 'data': {'msft': {'ntm': {'ntm_eps': 18.2}}}}, {})
        assert c['bpa_ntm']['MSFT'] == {'2026-11-01': 18.2}

    def test_no_pisa_lo_anterior_y_es_idempotente(self):
        c = {'bpa_ntm': {'MSFT': {'2026-10-25': 18.0}}}
        foto = {'generated_at': '2026-11-01', 'data': {'MSFT': {'ntm': {'ntm_eps': 18.2}}}}
        bp.anotar_consenso(foto, c); bp.anotar_consenso(foto, c)
        assert c['bpa_ntm']['MSFT'] == {'2026-10-25': 18.0, '2026-11-01': 18.2}

    def test_sin_dato_no_anota(self):
        c = bp.anotar_consenso({'generated_at': '2026-11-01', 'data': {'X': {'ntm': {}}}}, {})
        assert 'X' not in c['bpa_ntm']


class TestMain:
    def test_si_falla_tikr_conserva_lo_de_ayer(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(bp, 'TIKR', tmp_path / 'no.json')
        salida = tmp_path / 'b.json'; salida.write_text(json.dumps({'bandas': {'A': {}}}))
        monkeypatch.setattr(bp, 'SALIDA', salida)
        fund = tmp_path / 'f.csv'; pd.DataFrame([{'ticker': 'A', 'current_price': 10.0}]).to_csv(fund, index=False)
        monkeypatch.setattr(bp, 'FUND', fund)
        bp.main()
        assert json.loads(salida.read_text()) == {'bandas': {'A': {}}}
        assert 'conservan' in capsys.readouterr().out

    def test_si_falla_la_descarga_reescribe_el_pe_con_las_bandas_de_ayer(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bp, 'TIKR', tmp_path / 'no.json')
        salida = tmp_path / 'b.json'
        salida.write_text(json.dumps({'bandas': {'A': {'bpa': 2.0, 'bpa_anio': 2025, 'mu': 3.0, 'sd': .2, 'mediana': 20.0, 'meses': 120}}}))
        monkeypatch.setattr(bp, 'SALIDA', salida)
        fund = tmp_path / 'f.csv'; pd.DataFrame([{'ticker': 'A', 'current_price': 32.0}]).to_csv(fund, index=False)
        monkeypatch.setattr(bp, 'FUND', fund)
        bp.main()
        assert pd.read_csv(fund).at[0, 'target_price_pe'] == 40.0
