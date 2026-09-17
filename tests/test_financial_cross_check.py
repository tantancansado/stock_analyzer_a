#!/usr/bin/env python3
"""Tests del cuadre contable — el caso ATLKY del 3-ago-2026."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from financial_cross_check import check_coherence, derive_from_statements


class TestSharesPriceCoherence:
    def test_us_stock_cuadra(self):
        # MCO real: 173.180.984 × 478.38 = 82.846.319.126 ≈ marketCap
        info = {'sharesOutstanding': 173180984, 'currentPrice': 478.38,
                'marketCap': 82846326784}
        res = check_coherence(info, 'MCO')
        assert res['per_share_reliable'] is True
        assert abs(res['shares_price_ratio'] - 1.0) < 0.001

    def test_adr_no_cuadra(self):
        # ATLKY real: acciones ordinarias suecas contra precio del ADS
        info = {'sharesOutstanding': 3317744716, 'currentPrice': 21.25,
                'marketCap': 103670685696}
        res = check_coherence(info, 'ATLKY')
        assert res['per_share_reliable'] is False
        assert res['shares_price_ratio'] == 0.6801
        assert 'ADR' in res['issues'][0]

    def test_datos_incompletos_no_bloquean(self):
        # Sin los tres datos no hay cuadre que hacer; no se asume lo peor
        assert check_coherence({'currentPrice': 10.0})['per_share_reliable'] is True

    def test_desviacion_pequena_tolerada(self):
        # Recompras entre el corte del dato y el precio de hoy
        info = {'sharesOutstanding': 100, 'currentPrice': 10.0, 'marketCap': 1020}
        assert check_coherence(info)['per_share_reliable'] is True


class TestFcfCrossCheck:
    def test_fcf_declarado_coherente_con_ocf_menos_capex(self):
        info = {'freeCashflow': 2579124992, 'operatingCashflow': 3319000064,
                'capitalExpenditure': -739875072}
        assert check_coherence(info)['issues'] == []

    def test_fcf_declarado_divergente_se_reporta(self):
        info = {'freeCashflow': 9000000000, 'operatingCashflow': 3319000064,
                'capitalExpenditure': -739875072}
        res = check_coherence(info, 'X')
        assert any('derivado' in i for i in res['issues'])
        # Divergencia se reporta pero no invalida los ratios por acción
        assert res['per_share_reliable'] is True


class _FakeStock:
    def __init__(self, cashflow=None):
        self.cashflow = cashflow if cashflow is not None else pd.DataFrame()
        self.financials = pd.DataFrame()
        self.balance_sheet = pd.DataFrame()


class TestDeriveFromStatements:
    def test_rellena_desde_el_estado_de_flujos(self):
        cf = pd.DataFrame(
            {pd.Timestamp('2025-12-31'): [25972000768.0, -3000000.0]},
            index=['Free Cash Flow', 'Capital Expenditure'],
        )
        info, filled = derive_from_statements(_FakeStock(cf), {'freeCashflow': None})
        assert info['freeCashflow'] == 25972000768.0
        assert 'freeCashflow' in filled

    def test_no_toca_lo_que_ya_existe(self):
        cf = pd.DataFrame({pd.Timestamp('2025-12-31'): [999.0]}, index=['Free Cash Flow'])
        info, filled = derive_from_statements(_FakeStock(cf), {'freeCashflow': 123.0})
        assert info['freeCashflow'] == 123.0 and filled == []

    def test_deriva_fcf_de_ocf_menos_capex(self):
        cf = pd.DataFrame(
            {pd.Timestamp('2025-12-31'): [3319000064.0, -739875072.0]},
            index=['Operating Cash Flow', 'Capital Expenditure'],
        )
        info, filled = derive_from_statements(_FakeStock(cf), {'freeCashflow': None})
        assert info['freeCashflow'] == 3319000064.0 - 739875072.0
        assert any('derivado' in f for f in filled)

    def test_estados_vacios_no_rompen(self):
        info, filled = derive_from_statements(_FakeStock(), {'freeCashflow': None})
        assert info['freeCashflow'] is None and filled == []


class TestElFcfDelEstadoDeFlujosManda:
    """`freeCashflow` de yfinance es un campo calculado por ellos, y se desvía.

    Medido el 17-sep-2026:
        YUM   declarado   833M  ·  operativo-capex  1.679M   (la MITAD)
        MCD   declarado 6.262M  ·  operativo-capex  7.761M   (-19%)
        CBOE  declarado   678M  ·  operativo-capex  1.874M

    Con 833M el FCF yield de YUM salía 2,22% cuando el real es 4,48%, y el DCF
    partía de la mitad del flujo — por eso decía «un 5,7% cara» mientras el
    modelo de P/E decía «+73,7% barata». Los dos modelos se contradecían porque
    los dos tenían el input roto, y el sistema respondía descartando los dos.

    `check_coherence` YA detectaba la discrepancia y la imprimía; luego se usaba
    el dato malo igualmente. Detectar sin actuar no sirve de nada.
    """

    def _stock(self, ocf_trim, capex_trim):
        import pandas as pd
        cols = pd.to_datetime(['2026-06-30', '2026-03-31', '2025-12-31', '2025-09-30'])
        qc = pd.DataFrame([ocf_trim, capex_trim], columns=cols,
                          index=['Operating Cash Flow', 'Capital Expenditure'])

        class _S:
            quarterly_cashflow = qc
            cashflow = pd.DataFrame()
            financials = pd.DataFrame()
            balance_sheet = pd.DataFrame()
        return _S()

    def test_el_caso_yum(self):
        st = self._stock([507e6, 416e6, 617e6, 543e6], [-100e6, -75e6, -135e6, -94e6])
        info, filled = derive_from_statements(st, {'freeCashflow': 833.25e6})
        assert info['freeCashflow'] == 1679e6
        assert any('833' in f for f in filled), 'el cambio tiene que quedar dicho'

    def test_tambien_cuando_el_desvio_es_pequeno(self):
        """MCD se colaba por poco: 19% de desvío contra un umbral del 25%, y
        seguía valorándose con un flujo un quinto más bajo del que genera."""
        st = self._stock([2807e6, 2412e6, 2697e6, 3428e6], [-831e6, -682e6, -1059e6, -1011e6])
        info, _ = derive_from_statements(st, {'freeCashflow': 6262e6})
        assert info['freeCashflow'] == 7761e6

    def test_suma_cuatro_trimestres_no_coge_el_ultimo(self):
        """El valor «más reciente» de un estado trimestral es un trimestre
        suelto, no un año."""
        st = self._stock([500e6]*4, [-100e6]*4)
        info, _ = derive_from_statements(st, {'freeCashflow': None})
        assert info['freeCashflow'] == 1600e6

    def test_con_menos_de_cuatro_trimestres_no_se_inventa_un_ttm(self):
        import pandas as pd
        cols = pd.to_datetime(['2026-06-30', '2026-03-31'])
        qc = pd.DataFrame([[500e6, 400e6], [-100e6, -80e6]], columns=cols,
                          index=['Operating Cash Flow', 'Capital Expenditure'])

        class _S:
            quarterly_cashflow = qc
            cashflow = pd.DataFrame()
            financials = pd.DataFrame()
            balance_sheet = pd.DataFrame()
        info, _ = derive_from_statements(_S(), {'freeCashflow': 900e6})
        assert info['freeCashflow'] == 900e6, 'sin TTM se respeta lo que había'


class TestElCapitalCirculanteNoEsFlujoDelNegocio:
    """Un movimiento de balance no es dinero que genere la empresa.

    Medido el 17-sep-2026 sobre el último año fiscal:

        CBOE   flujo 1.753M   circulante  +529M  (+30%)   -> lo INFLA
        V      flujo 23.059M  circulante -15.172M (-66%)  -> lo DEPRIME
        ADP    flujo  5.441M  circulante  -1.106M (-20%)

    Con el circulante de CBOE dentro, su FCF yield salía 6,04% cuando el real
    ronda el 4-5%, y parecía crecer al 27,6% cuando sus ingresos crecen al
    6,0%. Sobre eso la recomendé como el mejor candidato del día.

    Se toma el MENOR de los dos: al que se lo infla se le quita, y al que se lo
    deprime no se le regala un flujo que no ha entrado en caja.
    """

    def _stock(self, ocf, capex, wc):
        import pandas as pd
        cols = pd.to_datetime(['2026-06-30', '2026-03-31', '2025-12-31', '2025-09-30'])
        filas = {'Operating Cash Flow': ocf, 'Capital Expenditure': capex}
        if wc is not None:
            filas['Change In Working Capital'] = wc
        qc = pd.DataFrame(list(filas.values()), columns=cols, index=list(filas))

        class _S:
            quarterly_cashflow = qc
            cashflow = pd.DataFrame()
            financials = pd.DataFrame()
            balance_sheet = pd.DataFrame()
        return _S()

    def test_cuando_el_circulante_infla_se_quita(self):
        st = self._stock([500e6]*4, [-25e6]*4, [150e6]*4)   # +30% del flujo
        info, _ = derive_from_statements(st, {'freeCashflow': None})
        assert info['freeCashflow'] == (2000e6 - 600e6 - 100e6)

    def test_cuando_el_circulante_deprime_no_se_regala(self):
        """Visa: el circulante le resta 15.172M. Sumárselo daría un FCF que no
        ha entrado en caja."""
        st = self._stock([500e6]*4, [-25e6]*4, [-150e6]*4)
        info, _ = derive_from_statements(st, {'freeCashflow': None})
        assert info['freeCashflow'] == (2000e6 - 100e6)

    def test_sin_el_dato_de_circulante_se_usa_el_fcf_normal(self):
        st = self._stock([500e6]*4, [-25e6]*4, None)
        info, _ = derive_from_statements(st, {'freeCashflow': None})
        assert info['freeCashflow'] == (2000e6 - 100e6)
