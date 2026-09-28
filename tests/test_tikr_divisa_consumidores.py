"""El resto de consumidores de TIKR tampoco pueden mezclar divisas.

Las cifras de TIKR de un ADR vienen en la divisa de la empresa y por acción
ordinaria; el precio es el del ADR en USD. `owner_earnings` ya lo convertía. Los
otros dos sitios que las enseñaban seguían sin hacerlo:

- el buscador (`ticker_api._build_tikr_search_snapshot`) daba el BPA de consenso
  de CNI como 8,58 junto a un precio de 120,93 USD, cuando por ADR son 6,06 USD;
- el prompt de las tesis (`thesis_generator._tikr_context`) escribía «EPS
  NTM=$8.58» y «target $274.99» con un «$» que era EUR o CAD.
"""
import copy
import json
from pathlib import Path

import pytest

import owner_earnings as oe
import ticker_api as api
from thesis_generator import ThesisGenerator

RAIZ = Path(__file__).resolve().parent.parent
DATOS = json.loads((RAIZ / 'docs' / 'tikr_earnings_data.json').read_text())['data']
CNI_FX = 0.7065


def _ficha(ticker='CNI'):
    return copy.deepcopy(DATOS[ticker])


@pytest.fixture
def divisas(monkeypatch):
    def _fijar(par, fx=CNI_FX):
        monkeypatch.setattr(oe, '_divisas_del_ticker', lambda t: par)
        monkeypatch.setattr(oe, '_fx_de_cuentas_a_precio', lambda de, a, f: fx)
    return _fijar


# ── el ayudante compartido ──────────────────────────────────────────────────

def test_conversion_de_ticker_pasa_de_cad_a_usd(divisas):
    divisas(('CAD', 'USD'))
    c = oe.conversion_de_ticker('CNI', _ficha())
    assert c['de'] == 'CAD' and c['a'] == 'USD'
    assert c['factor'] == pytest.approx(CNI_FX, rel=0.01)


def test_conversion_de_ticker_misma_divisa_no_convierte(divisas):
    divisas(('USD', 'USD'))
    assert not oe.divisas_distintas('MCD')
    assert oe.conversion_de_ticker('MCD', _ficha('MCD')) is None


def test_conversion_de_ticker_sin_tipo_de_cambio_no_inventa(divisas):
    divisas(('CAD', 'USD'), fx=None)
    assert oe.divisas_distintas('CNI')
    assert oe.conversion_de_ticker('CNI', _ficha()) is None


def test_calculate_sigue_usando_el_mismo_ayudante(divisas, monkeypatch):
    divisas(('CAD', 'USD'))
    monkeypatch.setattr(oe, '_load_tikr', lambda: {'CNI': _ficha()})
    r = oe.calculate('CNI')
    assert r['conversion_divisa'] == oe.conversion_de_ticker('CNI', _ficha())


# ── buscador ────────────────────────────────────────────────────────────────

@pytest.fixture
def buscar(monkeypatch):
    def _run(ficha, ticker='CNI'):
        monkeypatch.setattr(api, '_load_tikr_earnings_index', lambda: {ticker: ficha})
        return api._build_tikr_search_snapshot(ticker)
    return _run


def test_buscador_da_el_bpa_por_adr_en_dolares(buscar, divisas):
    divisas(('CAD', 'USD'))
    f = _ficha()
    nativo = float(f['ntm']['ntm_eps_consensus'])
    s = buscar(f)
    assert s['consensus_eps'] == pytest.approx(nativo * CNI_FX, abs=0.02)
    assert s['consensus_eps'] < nativo


def test_buscador_convierte_los_ingresos_con_el_tipo_de_cambio(buscar, divisas):
    divisas(('CAD', 'USD'))
    f = _ficha()
    ae = f['analyst_estimates']
    nativo = float(ae['forward'][str(ae['current_year'])]['revenue'])
    assert buscar(f)['consensus_revenue_millions'] == pytest.approx(nativo * CNI_FX, abs=0.1)


def test_buscador_misma_divisa_no_toca_nada(buscar, divisas):
    divisas(('USD', 'USD'))
    f = _ficha('MCD')
    s = buscar(f, 'MCD')
    assert s['consensus_eps'] == pytest.approx(float(f['ntm']['ntm_eps_consensus']), abs=0.01)


def test_buscador_sin_conversion_fiable_no_ensena_importes(buscar, divisas):
    """Mejor nada que 8,58 CAD al lado de un precio en USD. Se quedan los cocientes
    que salen de importes de la misma divisa (rentabilidad por FCF); el P/E no,
    porque el de TIKR divide el precio por un BPA de base desconocida."""
    divisas(('CAD', 'USD'), fx=None)
    s = buscar(_ficha())
    assert s['consensus_eps'] is None
    assert s['consensus_revenue_millions'] is None
    assert s['forward_pe'] is None
    assert s['fcf_yield'] is not None


# ── prompt de las tesis ─────────────────────────────────────────────────────

def _contexto(ficha, ticker='CNI'):
    g = object.__new__(ThesisGenerator)
    g._tikr_data = {ticker: ficha}
    return g._tikr_context(ticker)


def test_el_prompt_no_escribe_dolar_delante_de_cifras_en_cad(divisas):
    divisas(('CAD', 'USD'))
    ctx = _contexto(_ficha())
    assert '$' not in ctx
    assert 'CAD' in ctx


def test_el_prompt_avisa_de_la_divisa_y_da_el_bpa_por_adr(divisas):
    divisas(('CAD', 'USD'))
    f = _ficha()
    ctx = _contexto(f)
    assert 'DIVISA' in ctx and 'ADR' in ctx and 'USD' in ctx
    assert f"EPS NTM {float(f['multiples']['ntm_eps']) * CNI_FX:.2f}" in ctx


def test_el_prompt_sin_conversion_prohibe_comparar_con_el_precio(divisas):
    divisas(('CAD', 'USD'), fx=None)
    assert 'NO compares' in _contexto(_ficha())


def test_el_prompt_de_una_empresa_en_dolares_no_lleva_aviso(divisas):
    divisas(('USD', 'USD'))
    ctx = _contexto(_ficha('MCD'), 'MCD')
    assert 'DIVISA' not in ctx
    assert 'USD' in ctx and '$' not in ctx


@pytest.mark.parametrize('n,texto', [(1, '1 ADR = 1 acción'), (5, '1 ADR = 1/5 acción'),
                                     (0.5, '1 ADR = 2 acciones')])
def test_el_aviso_dice_cuantas_acciones_es_un_adr(monkeypatch, n, texto):
    monkeypatch.setattr(oe, '_divisas_del_ticker', lambda t: ('EUR', 'USD'))
    monkeypatch.setattr(oe, 'conversion_de_ticker', lambda t, d: {
        'adr_por_accion': n, 'fx': 1.14, 'factor': 1.14 / n, 'de': 'EUR', 'a': 'USD'})
    assert texto in _contexto(_ficha('SAP'), 'SAP')


# ── P/E a doce meses ────────────────────────────────────────────────────────
# El de TIKR es precio / BPA y el BPA no tiene base fija (CNI 14,1x cuando el
# real es 19x): el buscador lo usaba para puntuar y el prompt de las tesis se lo
# enseñaba al modelo. Los dos leen ahora el que sale del beneficio.

def test_pe_ntm_de_ticker_usa_el_beneficio_si_las_divisas_difieren(divisas):
    divisas(('CAD', 'USD'))
    assert oe._fv(_ficha()['multiples']['ntm_pe']) < 15          # TIKR, mal
    assert 18 < oe.pe_ntm_de_ticker('CNI', _ficha()) < 22


def test_pe_ntm_de_ticker_misma_divisa_deja_el_de_tikr(divisas):
    divisas(('USD', 'USD'))
    f = _ficha('MCD')
    assert oe.pe_ntm_de_ticker('MCD', f) == oe._fv(f['multiples']['ntm_pe'])


def test_buscador_da_el_pe_bien(buscar, divisas):
    divisas(('CAD', 'USD'))
    assert 18 < buscar(_ficha())['forward_pe'] < 22


def test_buscador_sin_conversion_fiable_no_da_pe(buscar, divisas):
    divisas(('CAD', 'USD'), fx=None)
    assert buscar(_ficha())['forward_pe'] is None


def test_prompt_de_tesis_da_el_pe_bien(divisas):
    divisas(('CAD', 'USD'))
    g = ThesisGenerator.__new__(ThesisGenerator)
    g._tikr_data = {'CNI': _ficha()}
    texto = g._tikr_context('CNI')
    pe = float(texto.split('P/E NTM=')[1].split('x')[0])
    assert 18 < pe < 22
