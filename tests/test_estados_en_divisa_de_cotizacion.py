"""Los estados financieros vienen en la divisa de las cuentas, no en la de cotización.

Keyence (ADR en dólares, cuentas en yenes) enseñaba un FCF yield de 321%
porque el FCF salía de los estados sin pasar por el tipo de cambio.
"""
import pandas as pd
from financial_cross_check import derive_from_statements


class _Stock:
    def __init__(self):
        idx = ['Free Cash Flow', 'Operating Cash Flow', 'Capital Expenditure']
        self.cashflow = pd.DataFrame({'2026': [400.0, 450.0, -50.0]}, index=idx)
        self.quarterly_cashflow = None
        self.quarterly_income_stmt = None
        self.financials = self.balance_sheet = None


def test_el_fcf_de_los_estados_se_convierte():
    out, _ = derive_from_statements(_Stock(), {}, fx_to_major=0.01)
    assert out['freeCashflow'] == 4.0
    assert out['operatingCashflow'] == 4.5


def test_sin_tipo_de_cambio_no_se_inventa_cifra():
    out, filled = derive_from_statements(_Stock(), {}, fx_to_major=None)
    assert filled == [] and 'freeCashflow' not in out
