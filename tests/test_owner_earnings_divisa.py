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
    assert mismo['ntm_pe'] == base['ntm_pe'] == oe._fv(_ficha()['multiples']['ntm_pe'])
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


# ── P/E y objetivo por PER: el BPA de TIKR no tiene una base fija ───────────
#
# `ntm_pe` de TIKR es precio / BPA. En CNI, CP, TECK, RACE, ASML y CSU.TO el BPA
# viene en la divisa de la empresa y el precio en otra (CNI 14,1x cuando el P/E
# a futuro real es 19x); en los ADR de verdad el BPA ya viene en USD por ADR; en
# Givaudan mezcla las dos (0,6x). Además, el objetivo por PER salía ya en la
# divisa del precio (el múltiplo lleva las unidades) y se le aplicaba encima el
# factor de conversión: convertido dos veces, un 30% de menos en CNI.

def test_pe_de_cni_sale_del_beneficio_y_no_del_bpa_en_cad(calcular):
    ficha = _ficha()
    tikr = oe._fv(ficha['multiples']['ntm_pe'])
    r = calcular(ficha, divisas=('CAD', 'USD'), fx=0.7065)
    assert tikr < 15                                  # el dato de TIKR, mal
    assert 18 < r['ntm_pe'] < 22                      # yfinance: 19,0
    assert r['per_target'] == pytest.approx(r['ntm_pe'] * 0.85, abs=0.1)


def test_el_objetivo_por_per_no_se_convierte_dos_veces(calcular):
    """Con un objetivo del 85% del P/E actual, el PER de un año cercano tiene que
    quedar cerca del 85% del precio. Convertido dos veces, en CNI era el 57%."""
    r = calcular(_ficha(), divisas=('CAD', 'USD'), fx=0.7065)
    per = r['price_targets']['2026']['per']
    assert 0.7 < per / r['current_price'] < 1.0


def test_adr_de_verdad_sale_igual_de_bien(calcular):
    """ESLOY: BPA de TIKR ya en USD por ADR (media acción). Antes salía a 40 sobre
    un precio de 85; ahora a ~66."""
    r = calcular(_ficha('ESLOY'), 'ESLOY', divisas=('EUR', 'USD'), fx=1.16)
    assert r['conversion_divisa']['adr_por_accion'] == 2
    assert 15 < r['ntm_pe'] < 22
    assert 0.7 < r['price_targets']['2026']['per'] / r['current_price'] < 1.0


def test_beneficio_que_el_bpa_no_confirma_no_da_objetivo(calcular):
    """CSU.TO 2028: beneficio de 1.176 con 1 analista frente a 2.887 el año
    anterior, y un BPA de 164 que implica 7 millones de acciones (son 21)."""
    r = calcular(_ficha('CSU.TO'), 'CSU.TO', divisas=('USD', 'CAD'), fx=1.384)
    objetivos = r['price_targets']
    assert 'per' in objetivos['2026'] and 'per' in objetivos['2027']
    assert 'per' not in objetivos['2028']
    assert 13 < r['ntm_pe'] < 18                      # yfinance: 15,3


def test_sin_beneficio_esperado_no_se_inventa_un_pe(calcular):
    ficha = _ficha()
    for anio in ficha['analyst_estimates']['forward'].values():
        anio['net_income_norm'] = None
    r = calcular(ficha, divisas=('CAD', 'USD'), fx=0.7065)
    assert r['ntm_pe'] is None
    assert all('per' not in t for t in r['price_targets'].values())
    assert r['signal'] != 'DATA_INCONSISTENT'         # los otros dos métodos siguen


def test_beneficio_confirmado_acepta_las_dos_bases_del_bpa():
    conv = {'factor': 0.5}
    acciones = 100.0
    ordinaria = {'net_income_norm': 1000.0, 'eps_norm': 10.0}    # 100 acciones
    por_adr = {'net_income_norm': 1000.0, 'eps_norm': 5.0}       # 200 = 100 / 0,5
    ajena = {'net_income_norm': 1000.0, 'eps_norm': 40.0}        # 25 acciones
    assert oe._beneficio_confirmado(ordinaria, acciones, conv) == 1000.0
    assert oe._beneficio_confirmado(por_adr, acciones, conv) == 1000.0
    assert oe._beneficio_confirmado(ajena, acciones, conv) is None
    assert oe._beneficio_confirmado({'net_income_norm': 1000.0}, acciones, conv) is None


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
