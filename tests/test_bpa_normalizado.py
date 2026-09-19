"""Un crédito fiscal de un trimestre inflaba el objetivo por P/E.

YUM, 18-sep-2026: un crédito de 320 M$ dejó la tasa fiscal efectiva de los
últimos doce meses en -0,9% y el BPA reportado en 7,82, cuando el normalizado
es 5,99. Sobre ese BPA inflado el modelo daba un objetivo de 199 $ (+46,8%);
con el real da 152 $ (+12,4%).

El error se agravó justo al mejorar el ancla del P/E: un múltiplo más alto
multiplicado por un BPA inflado es equivocarse dos veces en el mismo número.
El mismo apunte contable ya se detectaba para el CRECIMIENTO (neto contra
operativo); esto lo aplica al NIVEL.
"""
import pytest

from financial_cross_check import (DESVIO_FISCAL_ANOMALO, TASA_FISCAL_NORMAL,
                                   bpa_normalizado)


class _Stock:
    def __init__(self, pre, tax, acc):
        import pandas as pd
        cols = pd.to_datetime(['2026-06-30', '2026-03-31', '2025-12-31', '2025-09-30'])
        self.quarterly_income_stmt = pd.DataFrame(
            [pre, tax, [acc] * 4], columns=cols,
            index=['Pretax Income', 'Tax Provision', 'Diluted Average Shares'])


def test_el_caso_yum():
    """533+516+607+541 antes de impuestos, con un crédito de -320 en el Q2."""
    s = _Stock([533e6, 516e6, 607e6, 541e6], [-320e6, 84e6, 72e6, 144e6], 277e6)
    bpa, motivo = bpa_normalizado(s)
    assert bpa == pytest.approx(5.99, abs=0.05)
    assert 'tasa fiscal' in motivo


def test_una_tasa_normal_no_se_toca():
    """Si la efectiva es la de siempre, el BPA reportado vale y no se inventa
    una corrección."""
    pre = [1000e6] * 4
    tax = [1000e6 * TASA_FISCAL_NORMAL] * 4
    bpa, motivo = bpa_normalizado(_Stock(pre, tax, 100e6))
    assert bpa is None and motivo is None


def test_el_umbral_deja_pasar_la_variacion_normal():
    """Las tasas efectivas oscilan unos puntos entre trimestres sin que eso
    signifique nada."""
    assert 0.05 <= DESVIO_FISCAL_ANOMALO <= 0.20


def test_con_perdidas_no_se_normaliza():
    """Antes de impuestos negativo: un BPA normalizado ahí no significa nada."""
    bpa, _ = bpa_normalizado(_Stock([-100e6] * 4, [0] * 4, 100e6))
    assert bpa is None


def test_el_scorer_prefiere_el_normalizado():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / 'fundamental_scorer.py').read_text()
    from conftest import bloque_de_codigo
    bloque = bloque_de_codigo(src, '# ── 3. P/E justo')
    assert 'epsNormalizado' in bloque
    assert bloque.index('epsNormalizado') < bloque.index('eps_fwd) if eps_fwd')
