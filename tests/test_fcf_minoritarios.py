"""
El FCF de THC incluía caja que no es del accionista.

El flujo operativo consolida el 100% de las filiales. Tenet es dueña de USPI y
de sus centros quirúrgicos junto a socios médicos, que cobran su parte como
«distribuciones a minoritarios» en FINANCIACIÓN, fuera del FCF declarado. Del
comunicado de FY2025 (medido el 28-sep-2026):

    FCF declarado                 2.530 M
    distribuciones a minoritarios   809 M
    queda para el accionista      1.721 M   (-32%)

Con el bruto, THC salía con FCF yield 14,4%, DCF +135% y PEG 0,06, y encabezaba
el ranking VALUE con 79 puntos. El validador de owner earnings la marcaba «no
fiable» —el flujo no cuadraba con la capitalización— y no restaba nada.
"""
from types import SimpleNamespace

import pandas as pd
import pytest

from financial_cross_check import (UMBRAL_MINORITARIOS,
                                   peso_de_minoritarios_en_fcf)


def _trimestral(fila: str, anual: float) -> pd.DataFrame:
    """Cuatro trimestres iguales que suman `anual`."""
    cols = pd.to_datetime(['2026-06-30', '2026-03-31', '2025-12-31', '2025-09-30'])
    return pd.DataFrame([[anual / 4] * 4], index=[fila], columns=cols)


def _stock(minoritarios=None, otros=None):
    qi = _trimestral('Minority Interests', minoritarios) if minoritarios is not None \
        else pd.DataFrame()
    qc = _trimestral('Net Other Financing Charges', otros) if otros is not None \
        else pd.DataFrame()
    return SimpleNamespace(quarterly_income_stmt=qi, quarterly_cashflow=qc)


def test_tenet_pierde_un_tercio_del_flujo():
    # beneficio del minoritario 933, salida «otra» 1.445: manda el menor (933)
    peso = peso_de_minoritarios_en_fcf(_stock(-933e6, -1445e6), 3023e6)
    assert peso == pytest.approx(933 / 3023, rel=1e-6)
    assert 0.30 < peso < 0.32


def test_si_la_salida_de_caja_es_menor_manda_la_salida():
    # DVA: 340 de beneficio del minoritario, pero solo 250 salieron de caja
    peso = peso_de_minoritarios_en_fcf(_stock(-340e6, -250e6), 1493e6)
    assert peso == pytest.approx(250 / 1493, rel=1e-6)


def test_sin_salida_otra_que_acote_manda_el_beneficio_del_minoritario():
    # CHTR/QSR: 'otros' positivo o ausente. Sobreestima, pero no descontar nada
    # dejaría el flujo entero para quien solo es dueño de una parte.
    peso = peso_de_minoritarios_en_fcf(_stock(-825e6, +434e6), 4358e6)
    assert peso == pytest.approx(825 / 4358, rel=1e-6)
    peso = peso_de_minoritarios_en_fcf(_stock(-825e6, None), 4358e6)
    assert peso == pytest.approx(825 / 4358, rel=1e-6)


def test_un_minoritario_pequeno_no_mueve_nada():
    # WMT: 423 sobre 13.509 = 3%
    assert peso_de_minoritarios_en_fcf(_stock(-423e6, -3577e6), 13509e6) is None
    # y el umbral es el declarado, no otro
    justo = 100e6 * UMBRAL_MINORITARIOS
    assert peso_de_minoritarios_en_fcf(_stock(-justo * 0.99, None), 100e6) is None
    assert peso_de_minoritarios_en_fcf(_stock(-justo * 1.01, None), 100e6) is not None


@pytest.mark.parametrize('minoritarios', [+50e6, 0.0])
def test_minoritarios_positivos_o_nulos_no_descuentan(minoritarios):
    # signo contrario: el minoritario pone pérdidas, no cobra beneficio
    assert peso_de_minoritarios_en_fcf(_stock(minoritarios, -900e6), 1000e6) is None


def test_sin_datos_o_con_fcf_no_positivo_no_inventa_nada():
    assert peso_de_minoritarios_en_fcf(_stock(), 3000e6) is None
    assert peso_de_minoritarios_en_fcf(_stock(-900e6, -900e6), None) is None
    assert peso_de_minoritarios_en_fcf(_stock(-900e6, -900e6), -100e6) is None
    roto = SimpleNamespace()  # sin atributos: yfinance sin esos estados
    assert peso_de_minoritarios_en_fcf(roto, 3000e6) is None


def test_el_peso_nunca_pasa_del_cien_por_cien():
    assert peso_de_minoritarios_en_fcf(_stock(-5000e6, None), 1000e6) == 1.0


def test_fcf_fiable_reparte_solo_lo_que_es_del_accionista():
    from fundamental_scorer import fcf_fiable
    base = {'operatingCashflow': 4015e6, 'capitalExpenditure': -1010e6}
    assert fcf_fiable(base) == pytest.approx(3005e6)
    neto = fcf_fiable({**base, 'minoritariosSobreFcf': 0.31})
    assert neto == pytest.approx(3005e6 * 0.69)


def test_fcf_fiable_no_convierte_un_flujo_negativo_en_menos_negativo():
    from fundamental_scorer import fcf_fiable
    r = fcf_fiable({'operatingCashflow': 100e6, 'capitalExpenditure': -300e6,
                    'minoritariosSobreFcf': 0.5})
    assert r == pytest.approx(-200e6)


def test_derive_from_statements_deja_el_fcf_neto_y_avisa():
    """`freeCashflow` sale neto y la fracción viaja aparte; el aviso la nombra."""
    from financial_cross_check import derive_from_statements

    class Stock:
        quarterly_income_stmt = _trimestral('Minority Interests', -933e6)
        quarterly_cashflow = pd.concat([
            _trimestral('Operating Cash Flow', 4015e6),
            _trimestral('Capital Expenditure', -992e6),
            _trimestral('Net Other Financing Charges', -1445e6)])

        def __getattr__(self, nombre):  # el resto de estados: vacíos
            return pd.DataFrame()

    info, avisos = derive_from_statements(Stock(), {})
    bruto = 4015e6 - 992e6
    peso = 933e6 / bruto
    assert info['minoritariosSobreFcf'] == pytest.approx(peso)
    assert info['freeCashflow'] == pytest.approx(bruto * (1 - peso))
    assert any('minoritariosSobreFcf' in a for a in avisos)


def test_el_peg_no_se_dispara_con_un_trimestre_sobre_base_hundida():
    from fundamental_scorer import TECHO_CRECIMIENTO_PEG, FundamentalScorer
    stock = SimpleNamespace(financials=None, balance_sheet=None)
    # THC: BPA +186,8% en un trimestre, P/E ~12. Antes PEG 0,06.
    r = FundamentalScorer._calculate_magic_formula_metrics(
        None, stock, {'forwardPE': 12.3, 'earningsGrowth': 1.868})
    assert r['peg_ratio'] == pytest.approx(12.3 / (TECHO_CRECIMIENTO_PEG * 100), abs=0.01)
    assert r['peg_ratio'] > 0.3


def test_el_peg_prefiere_tres_anos_al_trimestre():
    from fundamental_scorer import FundamentalScorer
    stock = SimpleNamespace(financials=None, balance_sheet=None)
    # MCD: un trimestre a +5,6% contra 12,8% a tres años
    r = FundamentalScorer._calculate_magic_formula_metrics(
        None, stock, {'forwardPE': 16.9, 'earningsGrowth': 0.056, 'earningsGrowth3y': 0.128})
    assert r['peg_ratio'] == pytest.approx(16.9 / 12.8, abs=0.01)


def test_el_peg_sigue_sin_existir_con_crecimiento_negativo():
    from fundamental_scorer import FundamentalScorer
    stock = SimpleNamespace(financials=None, balance_sheet=None)
    r = FundamentalScorer._calculate_magic_formula_metrics(
        None, stock, {'forwardPE': 12.0, 'earningsGrowth': -0.2})
    assert r['peg_ratio'] is None
