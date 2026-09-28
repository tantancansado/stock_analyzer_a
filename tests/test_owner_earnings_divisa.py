"""Owner Earnings comparaba euros con dólares, y un tipo de cambio con un precio.

Dos fallos con la misma raíz: los datos de TIKR de un ADR llegan en la divisa
de la empresa y por acción ordinaria, y el precio es el del ADR en USD.

1. `price_close` de TIKR no es un precio, es el tipo de cambio del año. Se dejó
   de extraer el 16-sep-2026, pero 22 tickers seguían con él (no se volvieron a
   bajar, o su bloque de cuentas se conservó de la semana anterior) y
   `owner_earnings` lo multiplicaba por las acciones como si fuera un precio:

       CNI   EV/FCF 3,7  compra 4,69 (cotiza 120,93)   «OVERVALUED -96%»
       SAP   EV/FCF 1,0  compra 6,07 (cotiza 210,68)   «OVERVALUED -97%»

2. Aun sin eso, el objetivo salía en EUR/CAD/SEK por acción ordinaria y se
   comparaba con el precio del ADR: SAP -43% cuando eran -35%, y ESLOY «WATCH
   +5%» cuando el ADR es media acción y eran -40%. Es una señal falsa con
   aspecto de oportunidad, la peor.
"""
import copy
import json
import textwrap
from pathlib import Path

import pytest

import owner_earnings as oe

RAIZ = Path(__file__).resolve().parent.parent
DATOS = json.loads((RAIZ / 'docs' / 'tikr_earnings_data.json').read_text())['data']


def _ficha(ticker='CNI'):
    return copy.deepcopy(DATOS[ticker])


@pytest.fixture
def calcular(monkeypatch):
    """calculate() sobre una ficha concreta, con divisas y tipo de cambio a mano."""
    def _run(ficha, ticker='CNI', divisas=(None, None), fx=None):
        monkeypatch.setattr(oe, '_load_tikr', lambda: {ticker: ficha})
        monkeypatch.setattr(oe, '_divisas_del_ticker', lambda t: divisas)
        monkeypatch.setattr(oe, '_fx_de_cuentas_a_precio', lambda de, a, f: fx)
        return oe.calculate(ticker)
    return _run


# ── conversion_de_divisa: la aritmética ─────────────────────────────────────

def test_adr_de_loreal_es_un_quinto_de_accion():
    # mc en EUR, precio del ADR en USD: ratio = 1 / (0,2 × 1,14)
    c = oe.conversion_de_divisa(1 / (0.2 * 1.14), 1.14)
    assert c['adr_por_accion'] == 5
    assert c['factor'] == pytest.approx(1.14 / 5)


def test_adr_de_media_accion_no_se_confunde_con_uno_a_uno():
    """ESLOY: ratio 1,70 con EUR a 1,14 → 1,94 ≈ 2. Era el que colaba un WATCH."""
    c = oe.conversion_de_divisa(1.704, 1.14)
    assert c['adr_por_accion'] == 2
    assert c['factor'] == pytest.approx(0.57)


def test_uno_a_uno_solo_pide_el_tipo_de_cambio():
    c = oe.conversion_de_divisa(0.867, 1.14)      # SAP
    assert c['adr_por_accion'] == 1
    assert c['factor'] == pytest.approx(1.14)


def test_cotizacion_local_lleva_el_market_cap_en_la_divisa_del_precio():
    """CSU.TO: cuentas en USD, precio en CAD, market cap/(precio×acciones) = 1,000."""
    c = oe.conversion_de_divisa(1.0, 1.38, mc_en_divisa_de_cuentas=False)
    assert c['adr_por_accion'] == 1
    assert c['factor'] == pytest.approx(1.38)


def test_un_ratio_que_no_es_de_adr_no_se_convierte():
    """7 ADR por acción no existe: no se adivina, se marca."""
    assert oe.conversion_de_divisa(7 / 1.14, 1.14) is None


@pytest.mark.parametrize('ratio,fx', [(None, 1.1), (1.0, None), (0, 1.1), (1.0, 0), (-1.0, 1.1), (1.0, -1.1)])
def test_sin_datos_no_hay_conversion(ratio, fx):
    assert oe.conversion_de_divisa(ratio, fx) is None


# ── calculate: el tipo de cambio no es un precio ────────────────────────────

def test_price_close_no_se_lee_como_precio(calcular):
    limpia = _ficha()
    con_fx = _ficha()
    anios = con_fx['financials_history']['annual_years']
    con_fx['financials_history']['metrics']['price_close'] = {str(a): 1.3 for a in anios}

    a, b = calcular(limpia), calcular(con_fx)
    assert b['median_ev_fcf'] == a['median_ev_fcf']
    assert b['historical_multiples'] == {}
    assert b['buy_price'] == a['buy_price']
    assert b['median_ev_fcf'] > 5, 'un EV/FCF de una cifra es un tipo de cambio, no un múltiplo'


# ── calculate: divisa y ADR ─────────────────────────────────────────────────

def test_mismas_divisas_no_se_toca_nada(calcular):
    base = calcular(_ficha())
    mismo = calcular(_ficha(), divisas=('USD', 'USD'), fx=1.0)
    assert mismo['buy_price'] == base['buy_price']
    assert mismo['conversion_divisa'] is None


def test_los_objetivos_se_pasan_a_la_divisa_del_precio(calcular):
    """CNI: cuentas en CAD, precio del ADR en USD, 1:1."""
    ficha = _ficha()
    nativa = calcular(ficha)
    px, mc = oe._fv(ficha['price']['c']), oe._fv(ficha['price']['mc'])
    sh = oe._metric(ficha['financials_history']['metrics'], 'shares_diluted',
                    sorted(ficha['financials_history']['annual_years'], reverse=True)[0])
    fx = round(px * sh / mc, 4)                    # el CAD→USD que cuadra el market cap
    conv = calcular(_ficha(), divisas=('CAD', 'USD'), fx=fx)

    assert conv['conversion_divisa']['adr_por_accion'] == 1
    assert conv['conversion_divisa']['de'] == 'CAD'
    assert conv['buy_price'] == pytest.approx(nativa['buy_price'] * fx, rel=0.01)
    assert conv['exit_price'] == pytest.approx(nativa['exit_price'] * fx, rel=0.01)
    assert conv['upside_pct'] == pytest.approx((conv['buy_price'] / px - 1) * 100, abs=0.2)
    assert conv['signal'] != 'DATA_INCONSISTENT'
    assert conv['price_consistency_issue'] is None


def test_sin_tipo_de_cambio_no_hay_veredicto(calcular):
    """Divisas distintas y sin cómo convertir: mejor sin señal que con una falsa,
    aunque el market cap «cuadre» dentro de la banda de tolerancia."""
    r = calcular(_ficha(), divisas=('CAD', 'USD'), fx=None)
    assert r['signal'] == 'DATA_INCONSISTENT'
    assert r['buy_price'] is None and r['upside_pct'] is None
    assert r['price_consistency_issue'] is not None
    assert r['conversion_divisa'] is None


# ── el scraper y los datos guardados ────────────────────────────────────────

def _limpiador():
    """`_quitar_tipo_de_cambio`, extraída como texto: `tikr_scraper` depende de
    `pycognito`, que solo está en el runner."""
    src = (RAIZ / 'tikr_scraper.py').read_text()
    i = src.index('def _quitar_tipo_de_cambio')
    j = src.index('def _save_output')
    ns: dict = {}
    exec(textwrap.dedent(src[i:j]), ns)
    return ns['_quitar_tipo_de_cambio']


def test_el_limpiador_quita_price_close_y_solo_eso():
    limpiar = _limpiador()
    datos = {
        'A': {'financials_history': {'metrics': {'price_close': {'2025': 1.3}, 'revenue': {'2025': 10}}}},
        'B': {'financials_history': {'metrics': {'revenue': {'2025': 5}}}},
        'C': {'financials_history': {}},
        'D': {},
        'E': None,
    }
    assert limpiar(datos) == 1
    assert datos['A']['financials_history']['metrics'] == {'revenue': {'2025': 10}}
    assert datos['B']['financials_history']['metrics'] == {'revenue': {'2025': 5}}


def test_al_guardar_siempre_se_limpia():
    """El merge conserva lo que ya había, y ahí es donde el campo sobrevivía."""
    from conftest import bloque_de_codigo
    src = (RAIZ / 'tikr_scraper.py').read_text()
    cuerpo = bloque_de_codigo(src, 'def _save_output(')
    assert '_quitar_tipo_de_cambio(merged)' in cuerpo
    assert cuerpo.index('merged = {**existing, **results}') < cuerpo.index('_quitar_tipo_de_cambio(merged)')
    assert cuerpo.index('_quitar_tipo_de_cambio(merged)') < cuerpo.index('write_text')


def test_los_datos_guardados_no_traen_tipo_de_cambio_como_precio():
    con_campo = [t for t, v in DATOS.items()
                 if ((v.get('financials_history') or {}).get('metrics') or {}).get('price_close')]
    assert con_campo == [], f'price_close es un tipo de cambio, no un precio: {con_campo}'
