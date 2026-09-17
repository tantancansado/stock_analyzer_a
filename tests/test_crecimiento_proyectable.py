"""Proyectar cinco años con el crecimiento de un trimestre.

`revenueGrowth` de yfinance es el crecimiento de UN trimestre contra el mismo
del año anterior. El DCF lo usaba para proyectar un lustro, y en cualquier
negocio cíclico el resultado es absurdo (17-sep-2026):

    OXY   revenueGrowth +53,4%  ->  DCF 123 $ con la acción a 59 $   (+109%)
    CVX   revenueGrowth +51,4%  ->  DCF 386 $ con la acción a 211 $   (+84%)

Los dos números salen de las cuentas y son ciertos: son petroleras con un
trimestre de rebote del crudo. Lo que no es cierto es que crezcan al 15% anual
durante cinco años. Es el mismo error que cometí describiendo a McDonald's con
un trimestre suelto.

Y un segundo fallo debajo: el suelo de crecimiento estaba en +3%, así que a un
negocio cuyos ingresos CAEN se le proyectaba crecimiento positivo igualmente.
OXY pierde un 16,2% de ingresos al año y el modelo le regalaba un +3%.

Con el crecimiento a 3 años y sin ese suelo: OXY +16,5%, CVX +8,0%, y los
negocios estables no se mueven (MCD -4,6%, ROP +57,5%).
"""
import pandas as pd
import pytest

from fundamental_scorer import (SUELO_CRECIMIENTO, TECHO_CRECIMIENTO,
                                crecimiento_sostenible)


class TestQueCrecimientoSeProyecta:
    def test_manda_el_de_tres_anos_sobre_el_del_trimestre(self):
        g = crecimiento_sostenible({'revenueGrowth3y': 0.06,
                                    'revenueGrowth': 0.534,     # el trimestre de OXY
                                    'earningsGrowth': 9.649})
        assert g == pytest.approx(0.06, abs=0.001)

    def test_sin_el_de_tres_anos_se_usa_lo_que_haya(self):
        g = crecimiento_sostenible({'revenueGrowth': 0.08, 'earningsGrowth': 0.20})
        assert g == pytest.approx(0.08, abs=0.001)

    def test_un_negocio_que_decrece_puede_decrecer_en_el_modelo(self):
        """El suelo estaba en +3%: OXY perdía un 16,2% de ingresos al año y se
        valoraba con crecimiento positivo."""
        g = crecimiento_sostenible({'revenueGrowth3y': -0.162})
        assert g < 0, 'el modelo tiene que poder decir que el negocio se encoge'
        assert g == pytest.approx(SUELO_CRECIMIENTO, abs=0.001)

    def test_pero_no_sin_límite(self):
        """Por debajo del suelo la empresa se está apagando y un DCF no es la
        herramienta para valorar eso."""
        assert crecimiento_sostenible({'revenueGrowth3y': -0.80}) == SUELO_CRECIMIENTO
        assert crecimiento_sostenible({'revenueGrowth3y': 3.0}) == TECHO_CRECIMIENTO

    def test_sin_ningun_dato_no_se_inventa(self):
        assert crecimiento_sostenible({}) is None


class TestElCagrDeIngresos:
    def _stock(self, ingresos):
        cols = pd.to_datetime(['2025-12-31', '2024-12-31', '2023-12-31', '2022-12-31'])
        fin = pd.DataFrame([ingresos], columns=cols, index=['Total Revenue'])

        class _S:
            income_stmt = fin
        return _S()

    def test_calcula_el_compuesto_a_tres_anos(self):
        from financial_cross_check import crecimiento_ingresos_3y
        # 1000 -> 1331 en 3 años es exactamente el 10% anual
        g = crecimiento_ingresos_3y(self._stock([1331, 1210, 1100, 1000]))
        assert g == pytest.approx(0.10, abs=0.001)

    def test_con_menos_de_cuatro_anos_devuelve_nada(self):
        from financial_cross_check import crecimiento_ingresos_3y
        cols = pd.to_datetime(['2025-12-31', '2024-12-31'])
        fin = pd.DataFrame([[1200, 1000]], columns=cols, index=['Total Revenue'])

        class _S:
            income_stmt = fin
        assert crecimiento_ingresos_3y(_S()) is None

    def test_detecta_la_caida(self):
        from financial_cross_check import crecimiento_ingresos_3y
        g = crecimiento_ingresos_3y(self._stock([729, 810, 900, 1000]))
        assert g == pytest.approx(-0.10, abs=0.001)
