#!/usr/bin/env python3
"""Los periodos se emparejan por FECHA, no por posición (11-nov-2026).

yfinance deja a veces vacío un trimestre intermedio —el de junio de 2026 en BSX,
IT, ETN y DVA, unos días sí y otros no—. El `dropna` lo quitaba y todo lo que
contaba posiciones se desplazaba: `iloc[4]` era el trimestre de hace cinco y
«los cuatro últimos» cubrían quince meses. En el archivo diario se veía como un
dato que va y vuelve: Gartner con las ventas a -1,3 %, -10,8 % y -1,3 % en tres
días seguidos.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import financial_cross_check as fcc
import fundamental_scorer as fs

# Ventas de Gartner tal y como las daba yfinance el 11-nov-2026, en millones.
FECHAS = pd.to_datetime(['2026-09-30', '2026-06-30', '2026-03-31', '2025-12-31',
                         '2025-09-30', '2025-06-30', '2025-03-31'])
CON_HUECO = pd.Series([1505, np.nan, 1511, 1753, 1524, 1686, np.nan], index=FECHAS)
COMPLETA = pd.Series([1505, 1690, 1511, 1753, 1524, 1686, 1530], index=FECHAS)


class TestElMismoPeriodoDelAnoAnterior:
    def test_con_un_trimestre_vacio_compara_con_el_de_hace_un_ano(self):
        assert fcc.mismo_periodo_hace(CON_HUECO) == (1505.0, 1524.0)

    def test_sale_lo_mismo_tenga_o_no_el_hueco(self):
        assert fcc.mismo_periodo_hace(CON_HUECO) == fcc.mismo_periodo_hace(COMPLETA)

    def test_si_falta_justo_el_de_hace_un_ano_no_hay_dato(self):
        sin_sep = CON_HUECO.copy()
        sin_sep['2025-09-30'] = np.nan
        assert fcc.mismo_periodo_hace(sin_sep) is None

    def test_vale_con_anos_y_a_tres_anos(self):
        anual = pd.Series([130, 120, np.nan, 100],
                          index=pd.to_datetime(['2026-12-31', '2025-12-31', '2024-12-31', '2023-12-31']))
        assert fcc.mismo_periodo_hace(anual) == (130.0, 120.0)
        assert fcc.mismo_periodo_hace(anual, anios=3) == (130.0, 100.0)

    def test_aguanta_el_calendario_de_52_semanas(self):
        s = pd.Series([10, 9], index=pd.to_datetime(['2026-09-27', '2025-09-28']))
        assert fcc.mismo_periodo_hace(s) == (10.0, 9.0)

    def test_sin_fechas_no_inventa(self):
        assert fcc.mismo_periodo_hace(pd.Series([1, 2, 3], index=['a', 'b', 'c'])) is None


class TestDoceMesesSonCuatroTrimestresSeguidos:
    def test_con_un_hueco_no_se_suman(self):
        assert fcc.ultimos_seguidos(CON_HUECO, 4) is None

    def test_sin_hueco_si(self):
        assert fcc.ultimos_seguidos(COMPLETA, 4).sum() == 1505 + 1690 + 1511 + 1753

    def test_el_tramo_para_aceleraciones_se_corta_en_el_hueco(self):
        assert list(fcc.tramo_seguido(CON_HUECO)) == [1505.0]
        assert len(fcc.tramo_seguido(COMPLETA)) == 7


def _cuenta(serie):
    return pd.DataFrame([serie.values], index=['Total Revenue'], columns=serie.index)


class TestElScorer:
    def test_las_ventas_de_gartner_no_cambian_por_el_hueco(self):
        sc = fs.FundamentalScorer()
        con = sc._calculate_growth_acceleration_score(pd.DataFrame(), {'quarterly_financials': _cuenta(CON_HUECO)})
        sin = sc._calculate_growth_acceleration_score(pd.DataFrame(), {'quarterly_financials': _cuenta(COMPLETA)})
        assert con['rev_growth_yoy'] == sin['rev_growth_yoy'] == pytest.approx(-1.2, abs=0.1)

    def test_el_bpa_tampoco(self):
        sc = fs.FundamentalScorer()
        e = pd.DataFrame({'Earnings': CON_HUECO.values}, index=FECHAS)
        e.attrs['periodo'] = 'trimestral'
        assert sc._calculate_earnings_quality_score(e, {})['eps_growth_yoy'] == pytest.approx(-1.2, abs=0.1)

    def test_el_margen_de_doce_meses_no_suma_quince(self):
        q = pd.DataFrame([CON_HUECO.values, (CON_HUECO * 0.2).values],
                         index=['Total Revenue', 'Operating Income'], columns=FECHAS)

        class _St:
            quarterly_income_stmt = q
        assert fs.margen_operativo_12m(_St()) is None


def test_nadie_vuelve_a_contar_periodos_por_posicion():
    """El mismo fallo ya se había arreglado en conviction_filter (BSX) y seguía
    vivo en el scorer. Quien lea estados financieros usa mismo_periodo_hace,
    ultimos_seguidos o tramo_seguido."""
    import re
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    estados = re.compile(r'quarterly_income_stmt|quarterly_financials|quarterly_cashflow|income_stmt')
    posicion = re.compile(r'\.iloc\[[1-8]\]|\.iloc\[:[2-8]\]\.sum\(\)|\.head\([2-8]\)\.sum\(\)')
    culpables = []
    for f in raiz.glob('*.py'):
        texto = f.read_text()
        if not estados.search(texto):
            continue
        for n, linea in enumerate(texto.splitlines(), 1):
            codigo = linea.split('#', 1)[0]
            if posicion.search(codigo):
                culpables.append(f'{f.name}:{n}: {linea.strip()}')
    assert not culpables, '\n'.join(culpables)
