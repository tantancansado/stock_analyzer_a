#!/usr/bin/env python3
"""Tests para enrich_why_cheap.py — cubre US y EU.

Hasta el 5-ago-2026 solo procesaba value_opportunities.csv (US): la lista
europea nunca entraba en la selección de candidatos, mismo bug que tuvo
technical_filter.py con el timing técnico antes de arreglarse.
"""
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import enrich_why_cheap as ewc

COLS = ['ticker', 'company_name', 'value_score', 'proximity_to_52w_high',
       'relative_strength_6m']


def _row(ticker, score, drop=-20.0):
    return {'ticker': ticker, 'company_name': ticker, 'value_score': score,
            'proximity_to_52w_high': drop, 'relative_strength_6m': -5.0}


def _fake_veredicto(veredicto='CICLICO'):
    return {'veredicto': veredicto, 'resumen': 'test', 'fuentes': []}


@pytest.fixture
def universos(tmp_path, monkeypatch):
    us_csv = tmp_path / 'value_opportunities.csv'
    eu_csv = tmp_path / 'european_value_opportunities.csv'
    monkeypatch.setattr(ewc, 'TARGET_CSVS', [us_csv, eu_csv])
    # La caché va al tmp del test: con la ruta real, los tests se escribían
    # entre sí en docs/why_cheap_cache.json y el veredicto cacheado de un test
    # hacía fallar al siguiente (además de ensuciar el repo al correr la suite).
    monkeypatch.setattr(ewc, 'CACHE', tmp_path / 'why_cheap_cache.json')
    return us_csv, eu_csv


class TestCandidatosDeAmbosUniversos:
    def test_eu_entra_en_la_seleccion(self, universos, monkeypatch):
        us_csv, eu_csv = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        pd.DataFrame([_row('SAP.DE', 70.0)], columns=COLS).to_csv(eu_csv, index=False)
        monkeypatch.setattr(ewc, 'MAX_TICKERS', 5)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)

        vistos = []

        def _fake_analyze(ticker, *a, **kw):
            vistos.append(ticker)
            return _fake_veredicto()

        with patch.object(ewc, 'analyze_ticker', side_effect=_fake_analyze):
            ewc.main()

        assert 'SAP.DE' in vistos  # antes del fix, nunca

    def test_presupuesto_de_candidatos_es_compartido_no_por_csv(self, universos, monkeypatch):
        us_csv, eu_csv = universos
        us_rows = [_row(f'US{i}', 90.0 - i) for i in range(5)]
        eu_rows = [_row(f'EU{i}', 89.0 - i) for i in range(5)]
        pd.DataFrame(us_rows, columns=COLS).to_csv(us_csv, index=False)
        pd.DataFrame(eu_rows, columns=COLS).to_csv(eu_csv, index=False)
        monkeypatch.setattr(ewc, 'MAX_TICKERS', 3)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)

        vistos = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: (vistos.append(t), _fake_veredicto())[1]):
            ewc.main()

        # 3 en TOTAL, no 3 de cada uno (serían 6)
        assert len(vistos) == 3

    def test_resultados_se_escriben_en_el_csv_correcto(self, universos, monkeypatch):
        us_csv, eu_csv = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        pd.DataFrame([_row('SAP.DE', 70.0)], columns=COLS).to_csv(eu_csv, index=False)
        monkeypatch.setattr(ewc, 'MAX_TICKERS', 5)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)

        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: _fake_veredicto('EVENTO')):
            ewc.main()

        us_out = pd.read_csv(us_csv)
        eu_out = pd.read_csv(eu_csv)
        assert us_out.set_index('ticker').loc['AAPL', 'why_cheap'] == 'EVENTO'
        assert eu_out.set_index('ticker').loc['SAP.DE', 'why_cheap'] == 'EVENTO'
        # el 'origen_csv' de trabajo interno no se filtra a los CSV publicados
        assert 'origen_csv' not in us_out.columns
        assert 'origen_csv' not in eu_out.columns

    def test_universo_ausente_no_rompe_a_los_demas(self, universos, monkeypatch):
        us_csv, eu_csv = universos  # eu_csv no se crea
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        monkeypatch.setattr(ewc, 'MAX_TICKERS', 5)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)

        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: _fake_veredicto()):
            ewc.main()

        assert pd.read_csv(us_csv).set_index('ticker').loc['AAPL', 'why_cheap'] == 'CICLICO'

    def test_sin_ningun_universo_no_rompe(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ewc, 'TARGET_CSVS', [tmp_path / 'no_existe.csv'])
        ewc.main()  # no debe lanzar

    def test_ambos_vacios_no_rompe(self, universos):
        us_csv, eu_csv = universos
        pd.DataFrame(columns=COLS).to_csv(us_csv, index=False)
        pd.DataFrame(columns=COLS).to_csv(eu_csv, index=False)
        ewc.main()  # no debe lanzar


class TestPresupuestoEsTopeReal:
    """El presupuesto tiene que ser un techo, no una sugerencia.

    Hasta el 7-ago-2026 sólo se comprobaba "¿me he pasado ya?" ANTES de cada
    ticker, así que siempre se podía desbordar por el coste entero del último:
    esa corrida gastó 527s con presupuesto de 420 (+25%). Importa porque el job
    core-scoring va a 78-84 min sobre un tope de 90 — ese exceso sale del
    margen que evita que el job muera entero.
    """

    def test_no_arranca_un_ticker_que_no_cabe(self, universos, monkeypatch):
        """Con el presupuesto casi agotado no se empieza otro análisis."""
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 200)
        monkeypatch.setattr(ewc, 'COSTE_TICKER_SEG', 175.0)
        llamados = []

        def _fake(ticker, *a, **k):
            llamados.append(ticker)
            return {'veredicto': 'CICLICO', 'fuentes': [], 'resumen': ''}

        monkeypatch.setattr(ewc, 'analyze_ticker', _fake)
        ewc.main()
        # Cabe uno (0 + 175 <= 200); tras él quedan ~175s gastados y
        # 175+175 > 200, así que no arranca un segundo.
        assert len(llamados) <= 1, \
            f'arrancó {len(llamados)} análisis sin margen: {llamados}'

    def test_la_reserva_crece_con_el_peor_caso_visto(self):
        """Un ticker atascado sube la reserva, no se repite el atasco."""
        reserva = ewc.COSTE_TICKER_SEG
        for coste in (150.0, 400.0, 120.0):
            reserva = max(reserva, coste)
        assert reserva == 400.0

    def test_min_caida_excluye_el_ruido(self):
        """Explicar una caída del 9% cuesta lo mismo que una del 39% y no
        aporta: el módulo separa castigo de deterioro, y al 8% no hay castigo.
        MSFT entró con -9,7%, se llevó 201s por un timeout y dejó fuera a MCO."""
        assert ewc.MIN_CAIDA_PCT >= 12.0, \
            'umbral demasiado bajo — vuelve a colar ruido y gastar API en él'

    def test_presupuesto_cubre_al_menos_dos_tickers(self):
        """Si no caben dos, MAX_TICKERS miente y la selección es teatro."""
        assert ewc.PRESUPUESTO_SEG >= 2 * ewc.COSTE_TICKER_SEG


class TestCacheDeVeredictos:
    """Por qué una empresa está barata no cambia de un día para otro.

    Sin caché se recompraba el mismo análisis a diario: super_score_integrator
    regenera value_opportunities.csv desde cero y borra la columna, así que BR
    y SAP se re-analizaban cada mañana con búsqueda web (~$0,20 cada uno). Esa
    es la partida que agotó el saldo de la API el 10-ago-2026.
    """

    def test_no_reanaliza_lo_que_esta_en_cache(self, universos, monkeypatch):
        import json
        us_csv, _ = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        ewc.CACHE.write_text(json.dumps({
            'AAPL': {'veredicto': 'CICLICO', 'resumen': 'del cache', 'fuentes': [],
                     'fecha': __import__('datetime').date.today().isoformat(),
                     'criterio': ewc.CRITERIO},
        }))
        llamadas = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: llamadas.append(t) or _fake_veredicto()):
            ewc.main()
        assert llamadas == [], 'volvió a pagar un análisis que ya tenía en caché'
        assert pd.read_csv(us_csv).set_index('ticker').loc['AAPL', 'why_cheap'] == 'CICLICO'

    def test_reanaliza_lo_caducado(self, universos, monkeypatch):
        import json, datetime as dt
        us_csv, _ = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        viejo = (dt.date.today() - dt.timedelta(days=ewc.CACHE_DIAS + 1)).isoformat()
        ewc.CACHE.write_text(json.dumps({
            'AAPL': {'veredicto': 'CICLICO', 'resumen': 'viejo', 'fuentes': [], 'fecha': viejo},
        }))
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        llamadas = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: llamadas.append(t) or _fake_veredicto('EVENTO')):
            ewc.main()
        assert llamadas == ['AAPL'], 'no refrescó un veredicto caducado'

    def test_lo_analizado_queda_cacheado(self, universos, monkeypatch):
        import json
        us_csv, _ = universos
        pd.DataFrame([_row('AAPL', 60.0)], columns=COLS).to_csv(us_csv, index=False)
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: _fake_veredicto('EVENTO')):
            ewc.main()
        guardado = json.loads(ewc.CACHE.read_text())
        assert guardado['AAPL']['veredicto'] == 'EVENTO'
        assert 'fecha' in guardado['AAPL'], 'sin fecha no se puede caducar'


class TestSinDatosNoEsUnVeredicto:
    """«Sin datos» es que la búsqueda no trajo nada, no que no haya motivo.

    El 21-oct-2026 BSX salió DETERIORO con cuatro fuentes; el 9-nov el refresco
    de los 14 días volvió vacío, pisó ese veredicto y BSX entró en Prioridad.
    """

    def _cache(self, **entradas):
        import json
        ewc.CACHE.write_text(json.dumps(entradas))

    def _hace(self, dias):
        import datetime as dt
        return (dt.date.today() - dt.timedelta(days=dias)).isoformat()

    def test_un_refresco_vacio_no_borra_el_deterioro(self, universos, monkeypatch):
        import json
        us_csv, _ = universos
        pd.DataFrame([_row('BSX', 90.0, -30.0), _row('INTU', 85.0, -40.0)],
                     columns=COLS).to_csv(us_csv, index=False)
        self._cache(BSX={'veredicto': 'DETERIORO', 'resumen': 'recortes sucesivos de guidance',
                         'fuentes': ['https://a', 'https://b'], 'fecha': self._hace(20),
                         'criterio': ewc.CRITERIO})
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: _fake_veredicto('SIN_DATOS')):
            ewc.main()
        assert 'BSX' not in set(pd.read_csv(us_csv).ticker), 'volvió a publicarse con el deterioro borrado'
        guardado = json.loads(ewc.CACHE.read_text())
        assert guardado['BSX']['veredicto'] == 'DETERIORO'
        assert guardado['BSX']['fecha'] == self._hace(20), 'con la fecha de hoy no se reintentaría mañana'

    def test_sin_datos_se_reintenta_al_dia_siguiente(self, universos, monkeypatch):
        us_csv, _ = universos
        pd.DataFrame([_row('INTU', 85.0, -40.0)], columns=COLS).to_csv(us_csv, index=False)
        self._cache(INTU={'veredicto': 'SIN_DATOS', 'resumen': '', 'fuentes': [],
                          'fecha': self._hace(1), 'criterio': ewc.CRITERIO})
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        llamadas = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: llamadas.append(t) or _fake_veredicto()):
            ewc.main()
        assert llamadas == ['INTU'], 'un «sin datos» de ayer se tomó como respuesta'

    def test_lo_juzgado_con_otro_criterio_se_vuelve_a_preguntar(self, universos, monkeypatch):
        import json
        us_csv, _ = universos
        pd.DataFrame([_row('FICO', 88.0, -35.0)], columns=COLS).to_csv(us_csv, index=False)
        self._cache(FICO={'veredicto': 'EVENTO', 'resumen': 'regulador', 'fuentes': ['https://a'],
                          'fecha': self._hace(0), 'criterio': ewc.CRITERIO - 1})
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        llamadas = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: llamadas.append(t) or _fake_veredicto('DETERIORO')):
            ewc.main()
        assert llamadas == ['FICO']
        assert 'FICO' not in set(pd.read_csv(us_csv).ticker)
        assert json.loads(ewc.CACHE.read_text())['FICO']['criterio'] == ewc.CRITERIO

    def test_el_respaldo_dura_mas_que_el_refresco(self, universos):
        """A los 14 días se refresca, pero no se borra: es el respaldo si el refresco falla."""
        self._cache(MKC={'veredicto': 'EVENTO', 'resumen': 'x', 'fuentes': ['https://a'],
                         'fecha': self._hace(ewc.CACHE_DIAS + 5), 'criterio': ewc.CRITERIO},
                    VIEJO={'veredicto': 'EVENTO', 'resumen': 'x', 'fuentes': ['https://a'],
                           'fecha': self._hace(ewc.CACHE_PODA_DIAS + 1), 'criterio': ewc.CRITERIO})
        ewc._guardar_cache(ewc._leer_cache(), {'HOY': _fake_veredicto('CICLICO')})
        import json
        guardado = json.loads(ewc.CACHE.read_text())
        assert set(guardado) == {'MKC', 'HOY'}


def test_el_resumen_sale_sin_etiquetas_de_cita():
    from why_cheap_analyzer import limpiar_resumen
    crudo = '(cite index="4-6">El 26,5 % de caída vino del regulador</cite>. <cite index="9-7">Guía recortada</cite>'
    assert limpiar_resumen(crudo) == 'El 26,5 % de caída vino del regulador. Guía recortada'


class TestLasDePrioridad:
    """Las candidatas a comprar: Sonnet las estudia, se estudian tras cada resultado
    y sin estudio no salen como Prioridad (11-nov-2026)."""

    def _hoy(self, dias=0):
        import datetime as dt
        return (dt.date.today() + dt.timedelta(days=dias)).isoformat()

    def _prio(self, ticker='INTU', **extra):
        return {**_row(ticker, 90.0, -30.0), 'value_grupo': 'PRIORIDAD', 'value_falta': '', **extra}

    def _escribir(self, csv, *filas):
        pd.DataFrame(list(filas)).to_csv(csv, index=False)

    def test_la_estudia_sonnet(self, universos, monkeypatch):
        us_csv, _ = universos
        self._escribir(us_csv, self._prio())
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        modelos = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda *a, modelo=None, **kw: modelos.append(modelo) or _fake_veredicto('EVENTO')):
            ewc.main()
        assert modelos == [ewc.MODELO_PRIORIDAD]

    def test_si_sonnet_vuelve_vacio_pregunta_a_haiku(self, universos, monkeypatch):
        import json
        us_csv, _ = universos
        self._escribir(us_csv, self._prio())
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        respuestas = {ewc.MODELO_PRIORIDAD: 'SIN_DATOS', ewc.MODEL_HAIKU: 'CICLICO'}
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda *a, modelo=None, **kw: _fake_veredicto(respuestas[modelo])):
            ewc.main()
        assert pd.read_csv(us_csv).set_index('ticker').loc['INTU', 'value_grupo'] == 'PRIORIDAD'
        assert json.loads(ewc.CACHE.read_text())['INTU']['modelo'] == ewc.MODEL_HAIKU

    def test_sin_estudio_sale_en_observar(self, universos, monkeypatch):
        from value_bands import FALTA_ESTUDIO
        us_csv, _ = universos
        self._escribir(us_csv, self._prio())
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        with patch.object(ewc, 'analyze_ticker', side_effect=lambda *a, **kw: _fake_veredicto('SIN_DATOS')):
            ewc.main()
        fila = pd.read_csv(us_csv).set_index('ticker').loc['INTU']
        assert fila['value_grupo'] == 'OBSERVAR' and fila['value_falta'] == FALTA_ESTUDIO

    def test_lo_que_estudio_haiku_se_repite_con_sonnet(self, universos, monkeypatch):
        import json
        us_csv, _ = universos
        self._escribir(us_csv, self._prio())
        ewc.CACHE.write_text(json.dumps({'INTU': {
            'veredicto': 'EVENTO', 'resumen': 'x', 'fuentes': ['https://a'], 'fecha': self._hoy(),
            'criterio': ewc.CRITERIO, 'modelo': ewc.MODEL_HAIKU}}))
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        llamadas = []
        with patch.object(ewc, 'analyze_ticker',
                          side_effect=lambda t, *a, **kw: llamadas.append(t) or _fake_veredicto('EVENTO')):
            ewc.main()
        assert llamadas == ['INTU']

    def test_tras_presentar_resultados_se_vuelve_a_estudiar(self):
        base = {'veredicto': 'EVENTO', 'fecha': self._hoy(-3), 'criterio': ewc.CRITERIO}
        assert ewc._cache_vigente({**base, 'resultados': self._hoy(5)})
        assert not ewc._cache_vigente({**base, 'resultados': self._hoy(-1)}), \
            'presentó resultados ayer y seguía valiendo lo de antes'

    def test_guarda_la_fecha_de_los_proximos_resultados(self, universos, monkeypatch):
        import json
        us_csv, _ = universos
        self._escribir(us_csv, self._prio(earnings_date=self._hoy(9)))
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        with patch.object(ewc, 'analyze_ticker', side_effect=lambda *a, **kw: _fake_veredicto('EVENTO')):
            ewc.main()
        assert json.loads(ewc.CACHE.read_text())['INTU']['resultados'] == self._hoy(9)

    def test_una_fecha_de_resultados_ya_pasada_no_se_guarda(self, universos, monkeypatch):
        """Si no, caducaría cada día y se pagaría el estudio a diario."""
        import json
        us_csv, _ = universos
        self._escribir(us_csv, self._prio(earnings_date=self._hoy(-2)))
        monkeypatch.setattr(ewc, 'PRESUPUESTO_SEG', 999)
        with patch.object(ewc, 'analyze_ticker', side_effect=lambda *a, **kw: _fake_veredicto('EVENTO')):
            ewc.main()
        assert json.loads(ewc.CACHE.read_text())['INTU']['resultados'] == ''
