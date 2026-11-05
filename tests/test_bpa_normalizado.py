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

from financial_cross_check import (CONCENTRACION_NO_OPERATIVO,
                                   DESVIO_FISCAL_ANOMALO, PESO_NO_OPERATIVO,
                                   TASA_FISCAL_NORMAL, bpa_normalizado)


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


class _StockConOperativo:
    """Trimestres de más reciente a más antiguo, en miles de millones."""
    def __init__(self, op, otros, intereses=None, acc=12.5e9):
        import pandas as pd
        cols = pd.to_datetime(['2026-09-30', '2026-06-30', '2026-03-31', '2025-12-31'])
        intereses = intereses or [0.0] * 4
        pre = [(o + x + i) * 1e9 for o, x, i in zip(op, otros, intereses)]
        self.quarterly_income_stmt = pd.DataFrame(
            [pre, [p * TASA_FISCAL_NORMAL for p in pre], [o * 1e9 for o in op],
             [i * 1e9 for i in intereses], [acc] * 4],
            columns=cols,
            index=['Pretax Income', 'Tax Provision', 'Operating Income',
                   'Net Non Operating Interest Income Expense', 'Diluted Average Shares'])


def test_el_caso_goog():
    """Revalorizaciones de 97.800 y 36.900 M$ en dos trimestres: el P/E veía
    un +58,7% que era contabilidad. El BPA sale del negocio y los intereses."""
    s = _StockConOperativo(op=[40.58, 40.77, 39.70, 35.93], otros=[-9.02, 97.83, 36.87, 2.27],
                           intereses=[0.7, 0.7, 0.7, 0.6])
    bpa, motivo = bpa_normalizado(s)
    assert bpa == pytest.approx((156.98 + 2.7) * (1 - TASA_FISCAL_NORMAL) / 12.5, abs=0.01)
    assert 'no operativo' in motivo


def test_lo_que_se_repite_cada_trimestre_no_se_quita():
    """Las participadas de CVX aportan todos los trimestres: es beneficio."""
    s = _StockConOperativo(op=[6.5, 6.4, 6.6, 6.3], otros=[2.76, 1.07, 0.94, 1.49])
    assert bpa_normalizado(s) == (None, None)


def test_los_intereses_no_cuentan_como_golpe():
    """Una empresa con mucha caja cobra intereses: eso no es una plusvalía."""
    s = _StockConOperativo(op=[1.0, 1.0, 1.0, 1.0], otros=[0, 0, 0, 0],
                           intereses=[0.9, 0.0, 0.0, 0.0])
    assert bpa_normalizado(s) == (None, None)


def test_una_perdida_puntual_no_sube_el_bpa():
    s = _StockConOperativo(op=[10, 10, 10, 10], otros=[0, -20, 0, 0])
    assert bpa_normalizado(s) == (None, None)


def test_un_golpe_pequeno_no_se_corrige():
    s = _StockConOperativo(op=[10, 10, 10, 10], otros=[0, 3, 0, 0])
    assert bpa_normalizado(s) == (None, None)


def test_los_umbrales_separan_lo_medido():
    """Medido el 5-nov-2026: lo recurrente se queda en el 44%, lo puntual
    empieza en el 56%."""
    assert 0.44 < CONCENTRACION_NO_OPERATIVO < 0.56
    assert 0.10 <= PESO_NO_OPERATIVO <= 0.20
