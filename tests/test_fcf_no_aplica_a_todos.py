#!/usr/bin/env python3
"""El FCF yield no mide lo mismo en todos los negocios.

En un banco el flujo operativo son depósitos y préstamos; en un REIT, el
capex de construir va contra caja siempre. Usar ese número como si fuera
caja libre para el accionista tenía dos efectos, los dos reales el
22-sep-2026:

  COF   FCF yield 23,8% → el filtro lo echó de la lista por «divisa sin
        convertir». Es estadounidense y cotiza en dólares: no había nada
        que convertir. Y de haber entrado, habría cobrado +8 de score y
        +12 de convicción por ese número.
  EQIX  FCF yield −0,35% → se comía los −5 puntos de «quema caja» por
        construir centros de datos, que es a lo que se dedica. Salía con
        score 30,9, el más bajo de la lista, y aun así con badge ENTRADA.

Lo que NO debe romperse: la regla nació por ATLKY (3-ago-2026, coronas
suecas contra capitalización en dólares) y ahí tiene que seguir saltando.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_integrity import check_row, fcf_es_caja_libre


def _bloquea_por_fcf(pick):
    r = check_row(pick, require_value_fields=False)
    issues = r.get('issues', r) if isinstance(r, dict) else r
    return any(i.get('severity') == 'BLOCK' and i.get('field') == 'fcf_yield_pct'
               for i in issues)


class TestDondeElFcfNoEsCajaLibre:

    def test_prestamista_no_se_bloquea_por_su_fcf(self):
        cof = {'ticker': 'COF', 'industry': 'Credit Services',
               'dcf_no_aplicable': 'presta, no cobra comisiones',
               'fcf_yield_pct': 23.76}
        assert fcf_es_caja_libre(cof) is False
        assert not _bloquea_por_fcf(cof)

    def test_reit_tampoco(self):
        eqix = {'ticker': 'EQIX', 'industry': 'REIT - Specialty',
                'fcf_yield_pct': -0.35}
        assert fcf_es_caja_libre(eqix) is False

    def test_banco_y_aseguradora(self):
        for industria in ('Banks - Regional', 'Insurance - Life',
                          'Asset Management', 'Capital Markets'):
            assert fcf_es_caja_libre({'industry': industria}) is False, industria


class TestDondeSiEsCajaLibre:

    def test_red_de_pagos_conserva_su_fcf(self):
        """Visa comparte etiqueta «Credit Services» con Capital One pero cobra
        comisión, no presta. Lo resuelve `dcf_no_aplicable`, que el scorer
        calcula por el peso del margen de intereses — no la industria a ciegas."""
        visa = {'ticker': 'V', 'industry': 'Credit Services', 'fcf_yield_pct': 3.1}
        assert fcf_es_caja_libre(visa) is True

    def test_empresa_normal(self):
        assert fcf_es_caja_libre(
            {'industry': 'Consumer Electronics', 'fcf_yield_pct': 4.0}) is True

    def test_sin_industria_se_da_por_interpretable(self):
        """Ante la falta de dato no se desactiva una comprobación que existe
        para cazar basura: el que se salta la regla tiene que demostrarlo."""
        assert fcf_es_caja_libre({'fcf_yield_pct': 30.0}) is True
        assert _bloquea_por_fcf({'fcf_yield_pct': 30.0})


class TestLaReglaSigueCazandoLoQueNacioParaCazar:

    def test_los_adr_suecos_siguen_bloqueados(self):
        for ticker, industria, fcf in (
            ('ATLKY', 'Specialty Industrial Machinery', 26.24),
            ('ASAZY', 'Security & Protection Services', 46.58),
        ):
            pick = {'ticker': ticker, 'industry': industria, 'fcf_yield_pct': fcf}
            assert fcf_es_caja_libre(pick) is True
            assert _bloquea_por_fcf(pick), f'{ticker} tiene que seguir saltando'


class TestConFilasDeUnCsvDeVerdad:
    """Los tests de arriba usan diccionarios limpios. En el pipeline llegan
    filas de un DataFrame, y ahí una celda vacía es NaN — un float, y además
    *truthy*: `nan or ''` devuelve nan y `nan.strip()` revienta.

    Eso tumbó `Run Super Score Integration [CRITICAL]` el 23-sep-2026, y con
    él los veinte pasos siguientes del job: sin conviction filter, sin filtro
    técnico, sin portfolio tracker y sin veredictos de entrada.
    """

    def test_una_fila_con_nan_no_revienta(self):
        import numpy as np
        import pandas as pd
        df = pd.DataFrame([
            {'ticker': 'A', 'industry': np.nan, 'dcf_no_aplicable': np.nan},
            {'ticker': 'B', 'industry': 'Banks - Regional', 'dcf_no_aplicable': np.nan},
            {'ticker': 'C', 'industry': 'Credit Services', 'dcf_no_aplicable': 'presta'},
        ])
        out = [fcf_es_caja_libre(r.to_dict()) for _, r in df.iterrows()]
        assert out == [True, False, False]

    def test_el_csv_publicado_entero(self):
        """La prueba que habría evitado el fallo: recorrer el fichero real."""
        from pathlib import Path

        import pandas as pd
        ruta = Path(__file__).resolve().parents[1] / 'docs' / 'value_opportunities.csv'
        if not ruta.exists():
            pytest.skip('sin value_opportunities.csv')
        df = pd.read_csv(ruta)
        for _, r in df.iterrows():
            fcf_es_caja_libre(r.to_dict())    # no debe lanzar

    def test_check_row_tambien_aguanta_nan(self):
        import numpy as np
        r = {'ticker': 'X', 'current_price': 10.0, 'value_score': 50.0,
             'analyst_upside_pct': 12.0, 'fcf_yield_pct': 30.0,
             'industry': np.nan, 'dcf_no_aplicable': np.nan}
        res = check_row(r)
        assert isinstance(res, dict) and 'ok' in res

    def test_tipos_raros_no_rompen(self):
        """Un número donde se esperaba texto no puede tumbar el pipeline."""
        for v in (3.5, 0, True, [], {}):
            fcf_es_caja_libre({'dcf_no_aplicable': v, 'industry': v})
