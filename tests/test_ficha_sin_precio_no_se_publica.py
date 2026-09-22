#!/usr/bin/env python3
"""Una ficha sin precio no es una empresa mala: es una que no se ha podido leer.

`FundamentalScorer.score_ticker` devuelve ceros en vez de fallar cuando
yfinance no da nada, y esos ceros se publicaban como si fueran medidas. El
22-sep-2026 ROG.SW —Roche, que cotiza a unos 250 CHF— salía en
european_fundamental_scores.csv con:

    current_price 0.0 · market_cap 0 · sector «N/A» · fundamental_score 0.0

Un score de 0 dice «pésima». Lo que pasaba es que no había dato, y son cosas
distintas: es el bug nº1 de este repo.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _filtra(df):
    """Réplica del filtro que aplica el scanner al guardar."""
    precio = pd.to_numeric(df['current_price'], errors='coerce')
    return df[~(precio.isna() | (precio <= 0))]


class TestSinPrecioFuera:

    def test_el_caso_real_de_roche(self):
        df = pd.DataFrame([
            {'ticker': 'ROG.SW', 'current_price': 0.0, 'fundamental_score': 0.0},
            {'ticker': 'SAP.DE', 'current_price': 209.78, 'fundamental_score': 61.0},
        ])
        out = _filtra(df)
        assert list(out['ticker']) == ['SAP.DE']

    def test_precio_ausente_o_ilegible_tambien(self):
        df = pd.DataFrame([
            {'ticker': 'A', 'current_price': None},
            {'ticker': 'B', 'current_price': ''},
            {'ticker': 'C', 'current_price': 'n/a'},
            {'ticker': 'D', 'current_price': -1.0},
            {'ticker': 'E', 'current_price': 12.5},
        ])
        assert list(_filtra(df)['ticker']) == ['E']

    def test_no_se_lleva_por_delante_un_penny_stock(self):
        """Un precio bajo es un precio. Solo se va lo que no existe."""
        df = pd.DataFrame([{'ticker': 'X', 'current_price': 0.004}])
        assert list(_filtra(df)['ticker']) == ['X']

    def test_el_scanner_lo_aplica(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / 'european_value_scanner.py').read_text()
        assert 'sin_leer' in src and 'current_price' in src, (
            'el filtro tiene que estar en el punto donde se guarda el CSV')


class TestLoPublicadoNoTieneFichasVacias:

    @pytest.mark.parametrize('fichero', [
        'docs/european_fundamental_scores.csv',
        'docs/fundamental_scores.csv',
    ])
    def test_ninguna_ficha_con_precio_cero(self, fichero):
        from pathlib import Path
        ruta = Path(__file__).resolve().parents[1] / fichero
        if not ruta.exists():
            pytest.skip(f'sin {fichero}')
        df = pd.read_csv(ruta)
        if 'current_price' not in df.columns:
            pytest.skip('sin columna de precio')
        precio = pd.to_numeric(df['current_price'], errors='coerce')
        malas = df[precio.isna() | (precio <= 0)]
        assert malas.empty, (
            f'{fichero}: {len(malas)} fichas sin precio publicadas con score: '
            f'{list(malas["ticker"].head(5))}')
