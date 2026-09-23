#!/usr/bin/env python3
"""En Europa se reporta SEMESTRAL, y el scorer exigía trimestres.

yfinance no tiene `quarterly_income_stmt` para 36 de las 58 del universo
curado europeo —L'Oréal, Air Liquide, Hermès, Nestlé, Unilever, Diageo,
ASML…—, porque esas empresas no publican trimestres. El guardia del
19-sep-2026 («más de la mitad del score sería relleno») las dejaba a TODAS
sin score.

No se vio porque un bug tapaba al otro: el scanner europeo decidía reutilizar
el CSV del 18-sep mirando el `mtime`, que en CI siempre parece de hoy. Al
arreglar el mtime, Europa habría pasado de 58 empresas puntuadas a 22.

Con los estados ANUALES el interanual se mide igual de bien —mejor incluso:
no hay estacionalidad que corregir—; lo único que cambia es cuántas filas hay
que retroceder.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fundamental_scorer as fs


class _Estados:
    """Un yfinance de mentira: trimestral, anual o ninguno."""

    def __init__(self, trimestral=None, anual=None):
        self.quarterly_income_stmt = trimestral if trimestral is not None else pd.DataFrame()
        self.income_stmt = anual if anual is not None else pd.DataFrame()
        self.quarterly_financials = self.quarterly_income_stmt
        self.financials = self.income_stmt
        self.quarterly_balance_sheet = pd.DataFrame()
        self.balance_sheet = pd.DataFrame()


def _marco(periodos, beneficio):
    cols = pd.to_datetime([f'202{6 - i}-12-31' for i in range(periodos)])
    return pd.DataFrame({c: [v] for c, v in zip(cols, beneficio)},
                        index=['Net Income'])


class TestElPasoInteranual:

    def test_con_trimestres_se_retrocede_cuatro(self):
        assert fs._paso_interanual('trimestral') == 4

    def test_con_anos_se_retrocede_uno(self):
        assert fs._paso_interanual('anual') == 1

    def test_lo_desconocido_se_trata_como_trimestral(self):
        assert fs._paso_interanual('') == 4


class TestSinTrimestresSeUsaElAnual:

    def test_el_anual_entra_cuando_no_hay_trimestral(self):
        sc = fs.FundamentalScorer()
        st = _Estados(trimestral=None, anual=_marco(5, [100, 90, 85, 80, 70]))
        e = sc._get_quarterly_earnings(st)
        assert not e.empty
        assert e.attrs['periodo'] == 'anual'

    def test_un_trimestre_suelto_no_vale_como_serie(self):
        """Air Liquide devuelve UN trimestre: ni vacío ni utilizable.

        Con `.empty` como única comprobación se quedaba en el camino
        trimestral y salía sin score igual que si no hubiera nada.
        """
        sc = fs.FundamentalScorer()
        st = _Estados(trimestral=_marco(1, [100]), anual=_marco(5, [100, 90, 85, 80, 70]))
        e = sc._get_quarterly_earnings(st)
        assert e.attrs['periodo'] == 'anual'
        assert len(e) == 5

    def test_con_trimestres_de_verdad_no_se_toca_nada(self):
        sc = fs.FundamentalScorer()
        st = _Estados(trimestral=_marco(6, [100, 95, 90, 88, 80, 75]))
        e = sc._get_quarterly_earnings(st)
        assert e.attrs['periodo'] == 'trimestral'
        assert len(e) == 6

    def test_sin_nada_sigue_devolviendo_vacio(self):
        sc = fs.FundamentalScorer()
        assert sc._get_quarterly_earnings(_Estados()).empty


class TestElInteranualSeMideBienEnCadaBase:

    def test_con_anos_compara_contra_el_ano_pasado(self):
        """Cuatro filas atrás en una serie anual es hace CUATRO años."""
        sc = fs.FundamentalScorer()
        earnings = _marco(5, [110, 100, 90, 80, 70]).T
        earnings.columns = ['Earnings']
        earnings = earnings.sort_index(ascending=False)
        earnings.attrs['periodo'] = 'anual'
        res = sc._calculate_earnings_quality_score(earnings, {})
        # 110 contra 100 = +10%, no 110 contra 70 = +57%
        assert res['details'].get('eps_growth_yoy') == pytest.approx(10.0, abs=0.1)

    def test_con_trimestres_sigue_comparando_contra_el_mismo_trimestre(self):
        sc = fs.FundamentalScorer()
        earnings = _marco(5, [110, 100, 90, 80, 70]).T
        earnings.columns = ['Earnings']
        earnings = earnings.sort_index(ascending=False)
        earnings.attrs['periodo'] = 'trimestral'
        res = sc._calculate_earnings_quality_score(earnings, {})
        # 110 contra 70 = +57,1%
        assert res['details'].get('eps_growth_yoy') == pytest.approx(57.1, abs=0.2)


class TestElUniversoCuradoLlegaAPublicarse:
    """El punto ciego: un ticker que deja de resolverse no contradice a nadie.

    Pasó con MMC -> MRSH (quince corridas) y con ROG.SW -> ROP.SW (Roche, que
    Yahoo dejó de resolver con un 404 limpio).
    """

    def test_el_check_existe_y_detecta_una_cobertura_baja(self):
        import coherence_check as cc
        assert hasattr(cc, 'universo_curado_que_no_llega')
        # Con un mínimo imposible tiene que saltar; con 0, nunca.
        assert cc.universo_curado_que_no_llega(minimo_pct=1.01)
        assert cc.universo_curado_que_no_llega(minimo_pct=0.0) == []

    def test_roche_usa_el_simbolo_que_resuelve(self):
        from curated_tickers_eu import SCORED_EU_TICKERS
        assert 'ROG.SW' not in SCORED_EU_TICKERS, 'Yahoo devuelve 404 para ROG.SW'
        assert 'ROP.SW' in SCORED_EU_TICKERS
